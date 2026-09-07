"""Regex-based cleaning for scraped Korean news text before morphological analysis."""
import re

_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_BRACKET_TAG_RE = re.compile(r"\[[^\]]{1,20}\]|\([^)]{1,20}기자\)")
_MULTI_SPACE_RE = re.compile(r"\s+")
_ALLOWED_CHARS_RE = re.compile(r"[^가-힣a-zA-Z0-9.,!?%\s]")


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _BRACKET_TAG_RE.sub(" ", text)
    text = _ALLOWED_CHARS_RE.sub(" ", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text
