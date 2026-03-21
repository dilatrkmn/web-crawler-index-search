from crawler.utils import normalize_url, parse_html, tokenize


def test_normalize_url_sorts_query_and_drops_fragment():
    normalized = normalize_url('https://Example.com/docs/../page?a=2&b=1#section')
    assert normalized == 'https://example.com/page?a=2&b=1'


def test_parse_html_extracts_title_text_and_links():
    title, text, links = parse_html(
        '<html><head><title>Hello</title></head>'
        '<body><a href="/about">About</a><p>World</p><script>ignore</script></body></html>'
    )
    assert title == 'Hello'
    assert 'World' in text
    assert links == ['/about']


def test_tokenize_filters_stop_words():
    tokens = tokenize('This crawler indexes pages and crawler pages again')
    assert tokens['crawler'] == 2
    assert 'this' not in tokens