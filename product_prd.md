 Product Requirements Document

## 1. Product Summary

Web Crawler Index Search is a localhost-runnable application that crawls websites from a user-provided origin URL, indexes HTML page content into MySQL, and exposes search results while crawling is still in progress. The product is designed as a practical demonstration of concurrent crawling, bounded backpressure, thread-safe indexing, and near-real-time search on partially completed crawl jobs.

The current implementation targets a single-machine environment with a Flask web interface, a MySQL persistence layer, and Python standard-library crawling primitives. The primary value proposition is to give a reviewer or developer a working system that proves the core requirements of depth-limited crawling, duplicate prevention, live search during indexing, and observable crawler status.

## 2. Problem Statement

Developers, reviewers, and interview evaluators need a compact system that demonstrates how a search index can be built incrementally from a live crawl without requiring a distributed infrastructure footprint. Many toy crawlers fetch pages sequentially, ignore backpressure, or defer indexing until the entire crawl completes, which makes it hard to evaluate concurrency design and operational sensibility.

This product solves that gap by providing a runnable reference implementation that:

- crawls pages up to a configurable depth,
- prevents duplicate crawling using normalized URLs,
- stores searchable terms immediately after each page is processed,
- supports concurrent workers with bounded queueing,
- surfaces system state such as queue depth, inflight work, failures, and backpressure waits.

## 3. Target Users

### Primary users

- Hiring managers or interviewers evaluating the codebase.
- Developers who want a local crawler/search demo they can understand end-to-end.
- Students learning crawling, indexing, and concurrent worker design.

### Secondary users

- Engineers validating architecture ideas before scaling to production.
- Product stakeholders reviewing requirement coverage and trade-offs.

## 4. Goals

1. Provide a working crawl-and-search application that can run locally with minimal setup.
2. Allow users to start a crawl from an origin URL and a maximum depth.
3. Make indexed pages searchable before the crawl job finishes.
4. Prevent the same normalized page from being crawled twice within a job.
5. Demonstrate architectural sensibility through bounded queues, fixed worker concurrency, rate limiting, and persistent frontier state.
6. Expose enough operational visibility for a reviewer to inspect progress and failure conditions.

## 5. Non-Goals

- Full internet-scale crawling.
- JavaScript rendering or browser automation.
- Rich ranking, semantic retrieval, or vector search.
- Production-grade multi-tenant authentication or authorization.
- Robots.txt parsing, sitemap ingestion, or advanced crawl politeness beyond basic rate limiting.
- Horizontal scaling across multiple nodes in the current version.

## 6. User Stories

1. As a user, I want to enter an origin URL and crawl depth so that I can start indexing a site.
2. As a user, I want to search during an active crawl so that I can confirm the index is updating incrementally.
3. As a user, I want to see queue depth, inflight work, and failures so that I can understand crawler health.
4. As a reviewer, I want duplicate prevention and depth limits to be enforced so that the crawler behaves predictably.
5. As a developer, I want unfinished work persisted so that the system can restore pending tasks after restart.

## 7. Functional Requirements

### FR-1: Authentication
- The system must require login before granting access to the dashboard and API routes.
- Credentials may be sourced from environment configuration for local demo usage.

### FR-2: Start crawl job
- The system must accept an origin URL and maximum depth.
- The system must reject invalid or unsupported URLs.
- The system must create a crawl job record for each crawl request.

### FR-3: Frontier management
- The system must normalize URLs before deduplication and storage.
- The system must maintain a persistent frontier of queued, processing, done, and failed URLs.
- The system must restore pending tasks on startup when available.

### FR-4: Concurrent crawling
- The system must process tasks using a fixed number of worker threads.
- The system must limit crawl throughput with a configurable request-per-second gate.
- The system must support bounded queueing so that work production cannot grow without limit.

### FR-5: Content extraction
- The system must fetch HTML pages over HTTP or HTTPS.
- The system must extract page title, body text, and outgoing links.
- The system must skip or fail non-HTML responses rather than attempting to index them as documents.

### FR-6: Search indexing
- The system must persist page metadata and extracted text.
- The system must tokenize page body and title content for search.
- The system must store indexed data immediately after page processing so that search can see partial crawl progress.

### FR-7: Search
- The system must accept a query and return matched pages from indexed content.
- The system must return results ordered by relevance according to the current scoring rules.
- The system must support searching while a crawl is in progress.

### FR-8: Status and observability
- The system must expose crawl status including queue depth, queue capacity, inflight tasks, worker count, failures, duplicate skips, and backpressure waits.
- The system must report job completion when no frontier work remains.

### FR-9: Graceful shutdown
- The system must provide a way to stop background workers cleanly.

## 8. Non-Functional Requirements

### Reliability
- Frontier state and indexed content must be persisted in MySQL.
- The crawler must handle HTTP and URL errors without crashing the entire process.

### Performance
- The system should support concurrent worker execution on a single host.
- Search responses should operate over already committed rows without waiting for crawl completion.

### Safety and resource control
- The system must use bounded queueing to apply backpressure.
- The system must use thread-safe coordination around shared mutable state such as inflight counters and rate limiting.
- The system should cap page download size to avoid runaway memory usage on very large responses.

### Maintainability
- The codebase should remain understandable to a reviewer without introducing unnecessary infrastructure.
- The system should keep crawler logic, storage logic, and web routing separated by module responsibility.

## 9. Success Metrics

The product will be considered successful if it demonstrates the following:

- A crawl job can be started successfully from the UI or API.
- Pages are indexed and become searchable before the crawl job has fully completed.
- Duplicate pages are skipped consistently within the same job.
- Queueing remains bounded under link discovery pressure.
- Failures are observable and do not terminate unrelated work.
- The reviewer can understand the architecture and justify concurrency decisions.

## 10. Key Constraints and Assumptions

- The current version assumes a local or small-scale deployment footprint.
- MySQL must be available and configured before the app starts.
- The crawler targets static HTML content and does not execute JavaScript.
- Same-domain crawling is the default behavior for safety and predictability.
- Search quality is intentionally simple because the assignment prioritizes correctness and architecture over advanced ranking.

## 11. Risks and Mitigations

### Risk: Large or cyclic sites overwhelm the crawler
**Mitigation:** depth limits, URL normalization, duplicate prevention, fixed worker count, bounded queue size, and rate limiting.

### Risk: Network failures cause noisy crawl behavior
**Mitigation:** catch HTTP and URL exceptions, record failures, and continue processing other tasks.

### Risk: Search quality is too shallow for production expectations
**Mitigation:** scope the current system as an assignment-grade implementation and document a production roadmap separately.

### Risk: Restarting the app loses crawl progress
**Mitigation:** persist frontier state and restore pending tasks on startup.

## 12. MVP Scope

The MVP includes:

- login-protected web dashboard,
- crawl start endpoint,
- depth-limited crawling,
- duplicate prevention,
- immediate persistence of indexed pages,
- search during indexing,
- crawler status visibility,
- graceful worker shutdown.

## 13. Future Enhancements

- robots.txt support and domain-level crawl policies,
- richer ranking and snippet generation,
- distributed queueing and worker scaling,
- incremental recrawling and freshness policies,
- per-domain rate limiting,
- analytics dashboards and alerting,
- stronger auth and multi-user access control.