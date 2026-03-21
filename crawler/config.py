from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _as_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


DEFAULT_CONFIG = {
    'SECRET_KEY': os.getenv('SECRET_KEY', 'change-me'),
    'APP_HOST': os.getenv('APP_HOST', '127.0.0.1'),
    'APP_PORT': int(os.getenv('APP_PORT', '5000')),
    'DEBUG': _as_bool(os.getenv('FLASK_ENV'), False) and os.getenv('FLASK_ENV') == 'development',
    'APP_USERNAME': os.getenv('APP_USERNAME', 'admin'),
    'APP_PASSWORD': os.getenv('APP_PASSWORD', 'admin123'),
    'MYSQL_HOST': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'MYSQL_PORT': int(os.getenv('MYSQL_PORT', '3306')),
    'MYSQL_DATABASE': os.getenv('MYSQL_DATABASE', 'web_crawler'),
    'MYSQL_USER': os.getenv('MYSQL_USER', 'root'),
    'MYSQL_PASSWORD': os.getenv('MYSQL_PASSWORD', 'root'),
    'MYSQL_POOL_NAME': os.getenv('MYSQL_POOL_NAME', 'web_crawler_pool'),
    'MYSQL_POOL_SIZE': int(os.getenv('MYSQL_POOL_SIZE', '5')),
    'MAX_WORKERS': int(os.getenv('CRAWLER_MAX_WORKERS', '4')),
    'MAX_QUEUE_SIZE': int(os.getenv('CRAWLER_MAX_QUEUE_SIZE', '200')),
    'REQUESTS_PER_SECOND': float(os.getenv('CRAWLER_REQUESTS_PER_SECOND', '2.0')),
    'HTTP_TIMEOUT_SECONDS': int(os.getenv('CRAWLER_HTTP_TIMEOUT_SECONDS', '10')),
    'MAX_PAGE_BYTES': int(os.getenv('CRAWLER_MAX_PAGE_BYTES', '1000000')),
    'SAME_DOMAIN_ONLY': _as_bool(os.getenv('CRAWLER_SAME_DOMAIN_ONLY', 'true'), True),
}