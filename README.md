# Web Crawler Index Search

A localhost-runnable web crawler and search application built with **Flask**, **MySQL**, and Python standard-library crawling primitives. The app lets you:

- start a crawl from an origin URL with a max depth,
- search indexed pages while crawling is still running,
- monitor queue depth, progress, failures, and backpressure from a web dashboard.

---

## Quick Start

### 1) Clone the repository

```bash
git clone https://github.com/dilatrkmn/web-crawler-index-search.git
cd web-crawler-index-search
```

### 2) Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```
This installs the Flask stack plus `certifi`, which the crawler uses to validate HTTPS certificates consistently across local environments.

### 4) Start MySQL locally

You can use either Homebrew MySQL or Docker on macOS.

#### Option A: Homebrew MySQL

```bash
brew install mysql
brew services start mysql
mysql -uroot -e "DROP DATABASE IF EXISTS web_crawler; CREATE DATABASE web_crawler CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

#### Option B: Docker MySQL

```bash
docker run --name crawler-mysql \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=web_crawler \
  -p 3306:3306 \
  -d mysql:8
```

### 5) Create your environment file

```bash
cp .env.example .env
```

Edit `.env` if needed. The default values are already set for a local demo, including a default crawler user-agent:

```env
CRAWLER_USER_AGENT=LocalWebCrawler/1.0
```

The default app port is set to `8000` to avoid common local conflicts on macOS (for example AirPlay/AirTunes services on `5000`). If `8000` is already in use on your machine, change:

```env
APP_PORT=5050
```

### 6) Run the app

```bash
python app.py
```

Open your browser at:

```text
http://127.0.0.1:8000
```
If you changed `APP_PORT`, open that port instead, e.g. `http://127.0.0.1:5050`.

### 7) Log in

Default credentials from `.env.example`:

- **username:** `admin`
- **password:** `admin123`

---

## Project Overview

This project implements a single-machine crawler/search system designed for the assignment requirements:

- **`index(origin, k)`** starts a crawl from a URL up to depth `k`.
- **`search(query)`** returns relevant URLs from pages already indexed.
- **search works while indexing is active** because each page is committed independently.
- **backpressure is enforced** through a bounded queue, a fixed worker count, and request rate limiting.
- **duplicate crawling is prevented** through normalized URL deduplication.
- **resume is supported** by storing the crawl frontier in MySQL and reloading unfinished work on startup.

---

## Main Technologies

### Backend / Web

- **Flask 2.3.3**
- **flask-login 0.6.3**
- **Werkzeug 2.3.7**

### Database / Configuration

- **MySQL** via `mysql-connector-python 8.2.0`
- **python-dotenv 1.0.1** for environment variables

### Core crawler implementation

- `urllib.request` for HTTP fetching
- `html.parser.HTMLParser` for HTML parsing
- `threading` for worker concurrency
- `queue.Queue` for the bounded frontier queue
- `ssl` + `certifi` for HTTPS certificate verification

### Testing

- **pytest 7.4.2**

---

## How the Application Works

## 1. Authentication

The app uses a simple local login flow powered by `flask-login`.

- the login page is available at `/login`
- credentials come from `.env`
- after login, the user can access the dashboard and API routes

This is not meant as production-grade auth, but it makes the local demo safer and uses the requested package stack cleanly.

## 2. Indexing flow

When you start a crawl:

1. the app creates a crawl job record,
2. the origin URL is normalized,
3. the URL is inserted into the `frontier`,
4. worker threads pull tasks from a bounded queue,
5. each page is fetched and parsed,
6. discovered links are normalized and enqueued if allowed,
7. page content and tokens are stored in MySQL.

The crawler respects:

- maximum crawl depth,
- same-domain filtering by default,
- a bounded queue for backpressure,
- a fixed worker pool,
- request-per-second rate limiting.

## 3. Search flow

Search reads directly from committed rows in MySQL.

Each crawled page stores:

- page metadata,
- extracted text,
- discovered links,
- indexed term frequencies,
- title term hits.

Search scores results using token matches and title boosts, then returns pages ordered by relevance.

Because each page is written immediately after processing, search can return new results before the full crawl finishes.

## 4. System state / status

The dashboard and `/api/status` expose live system information such as:

- queue depth,
- queue capacity,
- active workers,
- pages crawled,
- failures,
- duplicate skips,
- backpressure waits,
- per-job progress.

---

## API Endpoints

### `POST /api/index`

Starts a crawl job.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/index \
  -H 'Content-Type: application/json' \
  -b cookies.txt -c cookies.txt \
  -d '{"origin":"https://example.com","depth":1}'
```

### `GET /api/search?q=...`

Searches the indexed content.

Example:

```bash
curl 'http://127.0.0.1:8000/api/search?q=example' -b cookies.txt
```

### `GET /api/status`

Returns current crawler state.

Example:

```bash
curl 'http://127.0.0.1:8000/api/status' -b cookies.txt
```

### `POST /api/shutdown`

Stops background workers cleanly.

---

## Recommended Demo URLs

For the fastest sanity check, start with:

- `http://example.com` at depth `0` or `1`

Then search for:

- `example`

Once that works, a richer HTTPS demo is:

- `https://docs.python.org/3/` at depth `1`

Then try queries such as:

- `python`
- `list`
- `dictionary`
- `string`

---

## Troubleshooting

### 1) `KeyError: 'USER_AGENT'` or `'USER_AGENT'` in the `pages.error` column

Make sure your `.env` contains:

```env
CRAWLER_USER_AGENT=LocalWebCrawler/1.0
```

The app now reads that value into `USER_AGENT` automatically.

### 2) `SSL: CERTIFICATE_VERIFY_FAILED`

The crawler uses `certifi` to provide a CA bundle for HTTPS requests. Reinstall dependencies if needed:

```bash
pip install -r requirements.txt
```

### 3) `127.0.0.1:5000` opens the wrong service or returns `403`

Some macOS setups already use port `5000`. Set a different app port in `.env`, for example:

```env
APP_PORT=5050
```

Then restart the app and open `http://127.0.0.1:5050`.

---

## Project Structure

```text
web-crawler-index-search/
├── app.py
├── .env.example
├── requirements.txt
├── README.md
├── product_prd.md
├── recommendation.md
├── crawler/
│   ├── app.py
│   ├── config.py
│   ├── crawler.py
│   ├── db.py
│   ├── storage.py
│   ├── utils.py
│   ├── static/
│   │   └── style.css
│   └── templates/
│       ├── index.html
│       └── login.html
└── tests/
    ├── test_app.py
    ├── test_crawler_integration.py
    └── test_utils.py
```

---

## Database Schema

The app creates these MySQL tables automatically on startup:

- `crawl_jobs`
- `frontier`
- `pages`
- `links`
- `page_terms`
- `crawler_state`

### What they store

- **`crawl_jobs`**: crawl metadata, origin URL, depth, status
- **`frontier`**: queued/processing/done/failed URLs
- **`pages`**: crawled page metadata and extracted content
- **`links`**: outgoing links discovered on each page
- **`page_terms`**: token frequencies for search
- **`crawler_state`**: counters used by the dashboard

---

## Assignment Requirements Mapping

### Depth-limited crawl

Implemented via the `depth` field carried in each frontier task and enforced before new links are queued.

### Never crawl the same page twice

Implemented with URL normalization plus a unique `(job_id, normalized_url)` constraint in the frontier table.

### Search while indexing is active

Implemented by committing each page independently so search sees newly indexed content immediately.

### Backpressure

Implemented with:

- a bounded in-memory queue,
- fixed worker count,
- global request rate limit,
- queue wait accounting.

### Resume after interruption

Implemented by persisting frontier state in MySQL and resetting unfinished `processing` rows back to `queued` at startup.

---

## Configuration

Configuration is loaded from `.env`.

Important variables:

```env
APP_USERNAME=admin
APP_PASSWORD=admin123
APP_HOST=127.0.0.1
APP_PORT=5000
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=web_crawler
MYSQL_USER=root
MYSQL_PASSWORD=root
CRAWLER_MAX_WORKERS=4
CRAWLER_MAX_QUEUE_SIZE=200
CRAWLER_REQUESTS_PER_SECOND=2.0
CRAWLER_HTTP_TIMEOUT_SECONDS=10
CRAWLER_MAX_PAGE_BYTES=1000000
CRAWLER_SAME_DOMAIN_ONLY=true
```

---

## Running Tests

Run:

```bash
pytest
```

Notes:

- `tests/test_utils.py` covers URL normalization, parsing, and tokenization.
- app/integration tests depend on the Flask/MySQL stack being installed and available.
