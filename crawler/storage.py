from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from mysql.connector import Error as MySQLError

from .db import Database


@dataclass(slots=True)
class FrontierTask:
    frontier_id: int
    job_id: int
    url: str
    normalized_url: str
    depth: int
    origin_url: str
    max_depth: int


class Storage:
    def __init__(self, database: Database):
        self.database = database

    def initialize(self) -> None:
        self.database.initialize()

    def increment_counter(self, key: str, amount: int = 1) -> None:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "UPDATE crawler_state SET `value` = `value` + %s WHERE `key` = %s",
                (amount, key),
            )
            conn.commit()
            cursor.close()

    def create_job(self, origin_url: str, normalized_origin_url: str, max_depth: int) -> int:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                '''
                INSERT INTO crawl_jobs(origin_url, normalized_origin_url, max_depth, status, started_at)
                VALUES (%s, %s, %s, 'running', CURRENT_TIMESTAMP)
                ''',
                (origin_url, normalized_origin_url, max_depth),
            )
            conn.commit()
            job_id = int(cursor.lastrowid)
            cursor.close()
            return job_id

    def list_jobs(self) -> list[dict]:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                '''
                SELECT j.*,
                       COALESCE(SUM(CASE WHEN f.status='queued' THEN 1 ELSE 0 END), 0) AS queued_urls,
                       COALESCE(SUM(CASE WHEN f.status='processing' THEN 1 ELSE 0 END), 0) AS active_urls,
                       COALESCE(SUM(CASE WHEN f.status='done' THEN 1 ELSE 0 END), 0) AS completed_urls,
                       COALESCE(SUM(CASE WHEN f.status='failed' THEN 1 ELSE 0 END), 0) AS failed_urls,
                       COALESCE((SELECT COUNT(*) FROM pages p WHERE p.job_id=j.id), 0) AS indexed_pages
                FROM crawl_jobs j
                LEFT JOIN frontier f ON f.job_id=j.id
                GROUP BY j.id
                ORDER BY j.id DESC
                '''
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows

    def reserve_url(
        self,
        job_id: int,
        url: str,
        normalized_url: str,
        depth: int,
        discovered_from: str | None,
    ) -> FrontierTask | None:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    '''
                    INSERT INTO frontier(job_id, url, normalized_url, depth, status, discovered_from)
                    VALUES (%s, %s, %s, %s, 'queued', %s)
                    ''',
                    (job_id, url, normalized_url, depth, discovered_from),
                )
                frontier_id = int(cursor.lastrowid)
                cursor.execute(
                    "UPDATE crawler_state SET `value` = `value` + 1 WHERE `key` = %s",
                    ('discovered_urls',),
                )
                cursor.execute(
                    '''
                    SELECT f.id AS frontier_id, f.job_id, f.url, f.normalized_url, f.depth,
                           j.origin_url, j.max_depth
                    FROM frontier f
                    JOIN crawl_jobs j ON j.id = f.job_id
                    WHERE f.id = %s
                    ''',
                    (frontier_id,),
                )
                row = cursor.fetchone()
                conn.commit()
                return FrontierTask(**row)
            except MySQLError:
                conn.rollback()
                return None
            finally:
                cursor.close()

    def load_pending_tasks(self) -> list[FrontierTask]:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "UPDATE frontier SET status='queued', updated_at=CURRENT_TIMESTAMP WHERE status='processing'"
            )
            cursor.execute(
                '''
                SELECT f.id AS frontier_id, f.job_id, f.url, f.normalized_url, f.depth,
                       j.origin_url, j.max_depth
                FROM frontier f
                JOIN crawl_jobs j ON j.id = f.job_id
                WHERE f.status='queued' AND j.status='running'
                ORDER BY f.id ASC
                '''
            )
            rows = cursor.fetchall()
            conn.commit()
            cursor.close()
            return [FrontierTask(**row) for row in rows]

    def mark_frontier_processing(self, frontier_id: int) -> None:
        self._update_frontier_status(
            frontier_id,
            "UPDATE frontier SET status='processing', attempts=attempts+1, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
        )

    def mark_frontier_done(self, frontier_id: int) -> None:
        self._update_frontier_status(
            frontier_id,
            "UPDATE frontier SET status='done', updated_at=CURRENT_TIMESTAMP WHERE id=%s",
        )

    def mark_frontier_failed(self, frontier_id: int) -> None:
        self._update_frontier_status(
            frontier_id,
            "UPDATE frontier SET status='failed', updated_at=CURRENT_TIMESTAMP WHERE id=%s",
        )

    def _update_frontier_status(self, frontier_id: int, statement: str) -> None:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(statement, (frontier_id,))
            conn.commit()
            cursor.close()

    def save_page(
        self,
        task: FrontierTask,
        status_code: int | None,
        title: str,
        content_text: str,
        content_type: str | None,
        error: str | None,
        links: Iterable[dict],
        body_terms: Counter,
        title_terms: Counter,
    ) -> None:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                '''
                INSERT INTO pages(job_id, url, normalized_url, origin_url, depth, status_code, title, content_text, content_type, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    url=VALUES(url),
                    origin_url=VALUES(origin_url),
                    depth=VALUES(depth),
                    status_code=VALUES(status_code),
                    title=VALUES(title),
                    content_text=VALUES(content_text),
                    fetched_at=CURRENT_TIMESTAMP,
                    content_type=VALUES(content_type),
                    error=VALUES(error),
                    id=LAST_INSERT_ID(id)
                ''',
                (
                    task.job_id,
                    task.url,
                    task.normalized_url,
                    task.origin_url,
                    task.depth,
                    status_code,
                    title,
                    content_text,
                    content_type,
                    error,
                ),
            )
            page_id = int(cursor.lastrowid)
            cursor.execute('DELETE FROM links WHERE page_id=%s', (page_id,))
            if links:
                cursor.executemany(
                    'INSERT INTO links(page_id, to_url, normalized_to_url) VALUES (%s, %s, %s)',
                    [(page_id, link['to_url'], link['normalized_to_url']) for link in links],
                )
            cursor.execute('DELETE FROM page_terms WHERE page_id=%s', (page_id,))
            merged_terms = set(body_terms) | set(title_terms)
            if merged_terms:
                cursor.executemany(
                    'INSERT INTO page_terms(page_id, term, frequency, title_hits) VALUES (%s, %s, %s, %s)',
                    [
                        (page_id, term, int(body_terms.get(term, 0)), int(title_terms.get(term, 0)))
                        for term in merged_terms
                    ],
                )
            cursor.execute(
                "UPDATE crawler_state SET `value` = `value` + 1 WHERE `key` = %s",
                ('pages_crawled',),
            )
            conn.commit()
            cursor.close()

    def record_failure(self, task: FrontierTask, status_code: int | None, content_type: str | None, error: str) -> None:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                '''
                INSERT INTO pages(job_id, url, normalized_url, origin_url, depth, status_code, title, content_text, content_type, error)
                VALUES (%s, %s, %s, %s, %s, %s, '', '', %s, %s)
                ON DUPLICATE KEY UPDATE
                    url=VALUES(url),
                    origin_url=VALUES(origin_url),
                    depth=VALUES(depth),
                    status_code=VALUES(status_code),
                    fetched_at=CURRENT_TIMESTAMP,
                    content_type=VALUES(content_type),
                    error=VALUES(error)
                ''',
                (
                    task.job_id,
                    task.url,
                    task.normalized_url,
                    task.origin_url,
                    task.depth,
                    status_code,
                    content_type,
                    error,
                ),
            )
            cursor.execute(
                "UPDATE crawler_state SET `value` = `value` + 1 WHERE `key` = %s",
                ('pages_failed',),
            )
            conn.commit()
            cursor.close()

    def complete_job_if_finished(self, job_id: int) -> None:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT COUNT(*) AS count FROM frontier WHERE job_id=%s AND status IN ('queued','processing')",
                (job_id,),
            )
            pending = cursor.fetchone()['count']
            if pending == 0:
                cursor.execute(
                    "UPDATE crawl_jobs SET status='completed', finished_at=CURRENT_TIMESTAMP WHERE id=%s AND status='running'",
                    (job_id,),
                )
                conn.commit()
            cursor.close()

    def get_status(self) -> dict:
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT `key`, `value` FROM crawler_state')
            counters = {row['key']: row['value'] for row in cursor.fetchall()}
            cursor.close()
        jobs = self.list_jobs()
        active_jobs = sum(1 for job in jobs if job['status'] == 'running')
        return {
            'counters': counters,
            'jobs': jobs,
            'active_jobs': active_jobs,
        }

    def search(self, query_terms: list[str], limit: int = 50) -> list[dict]:
        if not query_terms:
            return []
        placeholders = ','.join(['%s'] * len(query_terms))
        with self.database.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                f'''
                SELECT p.url AS relevant_url,
                       p.origin_url,
                       p.depth,
                       p.title,
                       j.id AS job_id,
                       SUM(pt.frequency + (pt.title_hits * 5)) AS score,
                       COUNT(DISTINCT pt.term) AS matched_terms
                FROM page_terms pt
                JOIN pages p ON p.id = pt.page_id
                JOIN crawl_jobs j ON j.id = p.job_id
                WHERE pt.term IN ({placeholders})
                GROUP BY p.id, p.url, p.origin_url, p.depth, p.title, j.id
                ORDER BY matched_terms DESC, score DESC, p.depth ASC, p.url ASC
                LIMIT %s
                ''',
                [*query_terms, limit],
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows