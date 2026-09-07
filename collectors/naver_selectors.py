"""Naver News search result markup constants.

Naver's search result cards use build-hashed CSS classes (e.g. "hCxR_uNoqfEahHu_")
that are regenerated on every deploy and cannot be relied on. The one stable anchor
is the `data-sds-comp="Profile"` attribute Naver's "Search Design System" puts on
each result's press+date row — this file documents that fact so the next person
debugging a "0 articles found" run doesn't waste time re-guessing class selectors.

If PROFILE_COMPONENT_SELECTOR stops matching anything, re-derive it by opening
search.naver.com/search.naver?where=news&query=... in a real browser, inspecting
one result card, and looking for a `data-sds-comp` (or successor) attribute.
"""

PROFILE_COMPONENT_SELECTOR = '[data-sds-comp="Profile"]'

EXTERNAL_LINK_SELECTOR = 'a[href^="http"]'
EXCLUDED_LINK_DOMAINS = ("naver.com", "pstatic.net")

MIN_TITLE_LENGTH = 10   # filters out thumbnail/press-logo links with empty/short link text
MAX_ANCESTOR_CLIMB = 8  # safety bound while walking up from a Profile node to find its headline
