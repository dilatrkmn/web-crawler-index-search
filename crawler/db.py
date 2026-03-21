from __future__ import annotations

from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS crawl_jobs (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        origin_url TEXT NOT NULL,
        normalized_origin_url TEXT NOT NULL,
        max_depth INT NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'queued',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        started_at DATETIME NULL,
        finished_at DATETIME NULL,
        last_error TEXT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS frontier (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        job_id BIGINT NOT NULL,
        url TEXT NOT NULL,
        normalized_url VARCHAR(700) NOT NULL,
        depth INT NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'queued',
        attempts INT NOT NULL DEFAULT 0,
        discovered_from VARCHAR(1024) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_frontier_job_url (job_id, normalized_url),
        INDEX idx_frontier_job_status (job_id, status),
        CONSTRAINT fk_frontier_job FOREIGN KEY (job_id) REFERENCES crawl_jobs(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pages (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        job_id BIGINT NOT NULL,
        url TEXT NOT NULL,
        normalized_url VARCHAR(700) NOT NULL,
        origin_url TEXT NOT NULL,
        depth INT NOT NULL,
        status_code INT NULL,
        title TEXT NULL,
        content_text LONGTEXT NULL,
        fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        content_type VARCHAR(255) NULL,
        error TEXT NULL,
        UNIQUE KEY uq_pages_job_url (job_id, normalized_url),
        INDEX idx_pages_job_depth (job_id, depth),
        INDEX idx_pages_normalized_url (normalized_url),
        CONSTRAINT fk_pages_job FOREIGN KEY (job_id) REFERENCES crawl_jobs(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS links (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        page_id BIGINT NOT NULL,
        to_url TEXT NOT NULL,
        normalized_to_url VARCHAR(1024) NOT NULL,
        INDEX idx_links_page_id (page_id),
        CONSTRAINT fk_links_page FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS page_terms (
        page_id BIGINT NOT NULL,
        term VARCHAR(255) NOT NULL,
        frequency INT NOT NULL,
        title_hits INT NOT NULL DEFAULT 0,
        PRIMARY KEY (page_id, term),
        INDEX idx_page_terms_term (term),
        CONSTRAINT fk_page_terms_page FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS crawler_state (
        `key` VARCHAR(64) PRIMARY KEY,
        `value` BIGINT NOT NULL
    )
    """,
]

COUNTERS = (
    'pages_crawled',
    'pages_failed',
    'pages_skipped',
    'discovered_urls',
    'backpressure_waits',
)


class Database:
    def __init__(self, config: dict):
        self.config = config
        self.pool = pooling.MySQLConnectionPool(
            pool_name=config['MYSQL_POOL_NAME'],
            pool_size=config['MYSQL_POOL_SIZE'],
            host=config['MYSQL_HOST'],
            port=config['MYSQL_PORT'],
            database=config['MYSQL_DATABASE'],
            user=config['MYSQL_USER'],
            password=config['MYSQL_PASSWORD'],
        )

    @contextmanager
    def connection(self):
        conn = self.pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            cursor = conn.cursor()
            for statement in SCHEMA:
                cursor.execute(statement)
            for counter in COUNTERS:
                cursor.execute(
                    "INSERT IGNORE INTO crawler_state(`key`, `value`) VALUES (%s, 0)",
                    (counter,),
                )
            conn.commit()
            cursor.close()