"""Naver News search collector (Selenium) -> og:description enrichment -> Kiwi rule-based
sentiment -> news table.

Extraction strategy (see naver_selectors.py for why): Naver's per-article CSS classes are
build-hashed and unusable as stable selectors. Instead we anchor on each result's
`data-sds-comp="Profile"` node (press name + relative date) and, for each one, climb
ancestors until we find the nearest non-Naver link with real title text — this pairs
correctly even when Naver groups related coverage into one cluster, because each
sub-item's own Profile node resolves to its own nearby headline first.

Scope note: Naver's search-result page doesn't expose a per-article snippet through any
stable selector, so instead of scraping one, we fetch each article's own page and read its
`og:description`/`meta[name=description]` tag — a near-universal publisher convention,
and more robust than reverse-engineering Naver's snippet markup. Falls back to empty
content (title-only sentiment) if a publisher omits it or the fetch fails.
"""
import logging
import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait

import config
from collectors import naver_selectors as sel
from collectors.chrome_driver import USER_AGENT, build_headless_chrome
from db.db import get_conn, insert_news
from nlp.rule_sentiment import score_text
from nlp.text_clean import clean_text

log = logging.getLogger(__name__)

_RELATIVE_RE = re.compile(r"(\d+)\s*(분|시간|일)\s*전")
_ABSOLUTE_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})\.?")
_HTTP_HEADERS = {"User-Agent": USER_AGENT}
_MIN_USEFUL_DESCRIPTION_LEN = 20
_A11Y_BOILERPLATE_RE = re.compile(r"새\s*창\s*열림")


def _strip_a11y_boilerplate(text: str) -> str:
    """Naver's headline <a> tags embed a visually-hidden '새 창 열림' (opens in new window)
    span for screen readers, which get_text() picks up — strip it before storing."""
    return _A11Y_BOILERPLATE_RE.sub("", text).strip()


def _parse_naver_date(text: str) -> str:
    """Best-effort normalize Naver's relative/absolute date strings to YYYY-MM-DD."""
    now = datetime.now()
    if not text:
        return now.strftime("%Y-%m-%d")

    if "어제" in text:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")

    m = _RELATIVE_RE.search(text)
    if m:
        amount, unit = int(m.group(1)), m.group(2)
        delta = {"분": timedelta(minutes=amount), "시간": timedelta(hours=amount), "일": timedelta(days=amount)}[unit]
        return (now - delta).strftime("%Y-%m-%d")

    m = _ABSOLUTE_RE.search(text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    return now.strftime("%Y-%m-%d")


def _find_headline_anchor(profile_el):
    """Climb from a Profile node until an ancestor contains a non-Naver link with real title text."""
    el = profile_el
    for _ in range(sel.MAX_ANCESTOR_CLIMB):
        el = el.parent
        if el is None:
            return None
        candidates = [
            a
            for a in el.select(sel.EXTERNAL_LINK_SELECTOR)
            if a.get("href") and not any(d in a["href"] for d in sel.EXCLUDED_LINK_DOMAINS)
        ]
        titled = [a for a in candidates if len(a.get_text(strip=True)) >= sel.MIN_TITLE_LENGTH]
        if titled:
            return titled[0]
    return None


def _extract_search_results(html: str):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen_urls = set()
    for profile in soup.select(sel.PROFILE_COMPONENT_SELECTOR):
        anchor = _find_headline_anchor(profile)
        if anchor is None:
            continue
        url = anchor["href"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        results.append(
            {
                "title": clean_text(_strip_a11y_boilerplate(anchor.get_text(strip=True))),
                "url": url,
                "news_date": _parse_naver_date(profile.get_text(" ", strip=True)),
            }
        )
    return results


def _fetch_description(url: str) -> str:
    try:
        resp = requests.get(url, headers=_HTTP_HEADERS, timeout=8)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        meta = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        desc = (meta.get("content") or "").strip() if meta else ""
        return desc if len(desc) >= _MIN_USEFUL_DESCRIPTION_LEN else ""
    except requests.RequestException as e:
        log.debug("description fetch failed for %s: %s", url, e)
        return ""


def collect_news(max_articles: int = None):
    max_articles = max_articles or config.NEWS_MAX_ARTICLES_PER_RUN
    query = config.NEWS_SEARCH_QUERY
    url = config.NAVER_NEWS_SEARCH_URL.format(query=query)

    driver = build_headless_chrome()
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements("css selector", sel.PROFILE_COMPONENT_SELECTOR)) > 0
            )
        except Exception:
            log.warning("Timed out waiting for news results to render for query=%r", query)
        time.sleep(1)  # let async description/thumbnail fetches inside the SPA settle
        html = driver.page_source
    finally:
        driver.quit()

    results = _extract_search_results(html)[:max_articles]
    if not results:
        log.warning(
            "0 articles parsed for query=%r — Naver markup may have changed; "
            "check collectors/naver_selectors.py",
            query,
        )

    inserted = 0
    with get_conn() as conn:
        for item in results:
            content = clean_text(_fetch_description(item["url"]))
            rule_score = score_text(f"{item['title']} {content}")
            n = insert_news(
                conn,
                ticker=config.TICKER,
                news_date=item["news_date"],
                title=item["title"],
                content=content,
                url=item["url"],
                rule_sentiment_score=rule_score,
            )
            inserted += n

    log.info("news: %d new rows inserted for query=%r (parsed %d)", inserted, query, len(results))
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from db.db import init_db

    init_db()
    collect_news()
