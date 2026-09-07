"""Regex-based cleaning for scraped Korean news text before morphological analysis."""
import re

_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_BRACKET_TAG_RE = re.compile(r"\[[^\]]{1,20}\]|\([^)]{1,20}\)")
# Wire-service byline, e.g. "(서울=연합뉴스) 홍길동 기자 = 본문..." — the name+기자 sits
# *outside* the parens, so it needs its own pattern rather than being caught by
# _BRACKET_TAG_RE above. Anchored to the start and requires the trailing "=" so this
# doesn't also eat unrelated phrases like "노조 기자간담회" that just happen to contain 기자.
_BYLINE_RE = re.compile(r"^\s*[가-힣]{2,4}\s*기자\s*=\s*")
_MULTI_SPACE_RE = re.compile(r"\s+")
_ALLOWED_CHARS_RE = re.compile(r"[^가-힣a-zA-Z0-9.,!?%\s]")


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _BRACKET_TAG_RE.sub(" ", text)
    text = _BYLINE_RE.sub(" ", text)
    text = _ALLOWED_CHARS_RE.sub(" ", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text
