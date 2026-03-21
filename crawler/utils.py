import posixpath
import re
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

TOKEN_RE = re.compile(r"[a-zA-Z0-9]{2,}")
STOP_WORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'from', 'are', 'was', 'were',
    'you', 'your', 'have', 'has', 'had', 'but', 'not', 'all', 'can', 'our',
    'out', 'use', 'using', 'into', 'about', 'how', 'why', 'what', 'when',
    'where', 'who', 'will', 'shall', 'https', 'http', 'www', 'com', 'org',
}


class HTMLContentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text_parts = []
        self.in_title = False
        self.title_parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_map = dict(attrs)
        if tag in {'script', 'style'}:
            self._skip_depth += 1
        if tag == 'a' and 'href' in attrs_map:
            self.links.append(attrs_map['href'])
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in {'script', 'style'} and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        cleaned = data.strip()
        if not cleaned:
            return
        self.text_parts.append(cleaned)
        if self.in_title:
            self.title_parts.append(cleaned)

    @property
    def title(self) -> str:
        return ' '.join(self.title_parts).strip()

    @property
    def text(self) -> str:
        return ' '.join(self.text_parts).strip()


def normalize_url(candidate: str, base_url: str | None = None) -> str | None:
    if not candidate:
        return None
    absolute = urljoin(base_url, candidate) if base_url else candidate
    parsed = urlparse(absolute)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        return None
    host = parsed.hostname.lower() if parsed.hostname else ''
    port = parsed.port
    if port and not ((parsed.scheme == 'http' and port == 80) or (parsed.scheme == 'https' and port == 443)):
        netloc = f'{host}:{port}'
    else:
        netloc = host
    path = parsed.path or '/'
    normalized_path = posixpath.normpath(path)
    if not normalized_path.startswith('/'):
        normalized_path = '/' + normalized_path
    if path.endswith('/') and normalized_path != '/':
        normalized_path += '/'
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    return urlunparse((parsed.scheme.lower(), netloc, normalized_path, '', query, ''))


def same_domain(url_a: str, url_b: str) -> bool:
    return urlparse(url_a).hostname == urlparse(url_b).hostname


def parse_html(html: str) -> tuple[str, str, list[str]]:
    parser = HTMLContentParser()
    parser.feed(html)
    parser.close()
    return parser.title, parser.text, parser.links


def tokenize(text: str) -> Counter:
    tokens = [token.lower() for token in TOKEN_RE.findall(text or '')]
    return Counter(token for token in tokens if token not in STOP_WORDS)