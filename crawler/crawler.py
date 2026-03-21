from __future__ import annotations

import queue
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .storage import FrontierTask, Storage
from .utils import normalize_url, parse_html, same_domain, tokenize


class RateLimiter:
    def __init__(self, rate_per_second: float):
        self.rate_per_second = max(rate_per_second, 0.1)
        self.interval = 1.0 / self.rate_per_second
        self.lock = threading.Lock()
        self.next_allowed = time.monotonic()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            if now < self.next_allowed:
                time.sleep(self.next_allowed - now)
                now = time.monotonic()
            self.next_allowed = max(now, self.next_allowed) + self.interval


class CrawlManager:
    def __init__(self, storage: Storage, config: dict):
        self.storage = storage
        self.config = config
        self.queue: queue.Queue[FrontierTask] = queue.Queue(maxsize=config['MAX_QUEUE_SIZE'])
        self.rate_limiter = RateLimiter(config['REQUESTS_PER_SECOND'])
        self.stop_event = threading.Event()
        self.workers: list[threading.Thread] = []
        self.inflight_lock = threading.Lock()
        self.inflight = 0
        self._start_workers()
        self._restore_pending_tasks()

    def _start_workers(self) -> None:
        for index in range(self.config['MAX_WORKERS']):
            worker = threading.Thread(target=self._worker_loop, name=f'crawler-worker-{index}', daemon=True)
            worker.start()
            self.workers.append(worker)

    def _restore_pending_tasks(self) -> None:
        for task in self.storage.load_pending_tasks():
            self._put_task(task)

    def shutdown(self) -> None:
        self.stop_event.set()
        for _ in self.workers:
            while True:
                try:
                    self.queue.put(None, timeout=0.25)
                    break
                except queue.Full:
                    continue
        for worker in self.workers:
            worker.join(timeout=2)

    def start_job(self, origin_url: str, max_depth: int) -> dict:
        normalized_origin = normalize_url(origin_url)
        if not normalized_origin:
            raise ValueError('Origin URL must be a valid http/https URL.')
        job_id = self.storage.create_job(origin_url, normalized_origin, max_depth)
        task = self.storage.reserve_url(job_id, origin_url, normalized_origin, 0, None)
        if task:
            self._put_task(task)
        return {'job_id': job_id, 'origin_url': origin_url, 'max_depth': max_depth}

    def _put_task(self, task: FrontierTask | None) -> None:
        if task is None:
            return
        while not self.stop_event.is_set():
            try:
                self.queue.put(task, timeout=0.25)
                return
            except queue.Full:
                self.storage.increment_counter('backpressure_waits')

    def _worker_loop(self) -> None:
        while not self.stop_event.is_set():
            task = self.queue.get()
            if task is None:
                self.queue.task_done()
                return
            with self.inflight_lock:
                self.inflight += 1
            try:
                self.storage.mark_frontier_processing(task.frontier_id)
                succeeded = self._process_task(task)
                if succeeded:
                    self.storage.mark_frontier_done(task.frontier_id)
            except Exception as exc:
                self.storage.record_failure(task, None, None, str(exc))
                self.storage.mark_frontier_failed(task.frontier_id)
            finally:
                self.storage.complete_job_if_finished(task.job_id)
                with self.inflight_lock:
                    self.inflight -= 1
                self.queue.task_done()

    def _process_task(self, task: FrontierTask) -> bool:
        status_code = None
        content_type = None
        html = ''
        try:
            self.rate_limiter.wait()
            request = Request(task.url, headers={'User-Agent': self.config['USER_AGENT']})
            with urlopen(request, timeout=self.config['HTTP_TIMEOUT_SECONDS']) as response:
                status_code = getattr(response, 'status', None)
                content_type = response.headers.get('Content-Type', '')
                raw_bytes = response.read(self.config['MAX_PAGE_BYTES'])
                html = raw_bytes.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
        except HTTPError as exc:
            self.storage.record_failure(task, exc.code, exc.headers.get('Content-Type'), str(exc))
            self.storage.mark_frontier_failed(task.frontier_id)
            return False
        except URLError as exc:
            self.storage.record_failure(task, status_code, content_type, str(exc))
            self.storage.mark_frontier_failed(task.frontier_id)
            return False

        if 'html' not in (content_type or '').lower():
            self.storage.record_failure(task, status_code, content_type, 'Skipped non-HTML content')
            self.storage.mark_frontier_failed(task.frontier_id)
            return False

        title, text, raw_links = parse_html(html)
        body_terms = tokenize(text)
        title_terms = tokenize(title)
        normalized_links = []
        if task.depth < task.max_depth:
            for raw_link in raw_links:
                normalized = normalize_url(raw_link, task.url)
                if not normalized:
                    continue
                if self.config['SAME_DOMAIN_ONLY'] and not same_domain(task.url, normalized):
                    continue
                normalized_links.append({'to_url': raw_link, 'normalized_to_url': normalized})
                reserved = self.storage.reserve_url(
                    task.job_id,
                    normalized,
                    normalized,
                    task.depth + 1,
                    task.normalized_url,
                )
                if reserved:
                    self._put_task(reserved)
                else:
                    self.storage.increment_counter('pages_skipped')

        self.storage.save_page(
            task=task,
            status_code=status_code,
            title=title,
            content_text=text,
            content_type=content_type,
            error=None,
            links=normalized_links,
            body_terms=body_terms,
            title_terms=title_terms,
        )
        return True

    def status(self) -> dict:
        payload = self.storage.get_status()
        payload['queue_depth'] = self.queue.qsize()
        payload['queue_capacity'] = self.config['MAX_QUEUE_SIZE']
        with self.inflight_lock:
            payload['inflight'] = self.inflight
        payload['backpressure_active'] = payload['queue_depth'] >= self.config['MAX_QUEUE_SIZE']
        payload['requests_per_second'] = self.config['REQUESTS_PER_SECOND']
        payload['max_workers'] = self.config['MAX_WORKERS']
        return payload

    def search(self, query: str, limit: int = 50) -> dict:
        terms = list(tokenize(query).keys())
        return {
            'query': query,
            'terms': terms,
            'results': self.storage.search(terms, limit=limit),
        }