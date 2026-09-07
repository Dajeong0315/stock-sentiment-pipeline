from nlp.text_clean import clean_text


def test_strips_html_tags():
    assert "<b>" not in clean_text("<b>삼성전자</b> 실적 발표")


def test_strips_urls():
    assert "http" not in clean_text("기사 링크 https://example.com/a?b=1 참고")


def test_strips_wire_service_byline():
    cleaned = clean_text("(서울=연합뉴스) 홍길동 기자 = 삼성전자 실적 발표")
    assert "기자" not in cleaned
    assert "삼성전자" in cleaned


def test_empty_input_returns_empty():
    assert clean_text("") == ""
    assert clean_text(None) == ""
