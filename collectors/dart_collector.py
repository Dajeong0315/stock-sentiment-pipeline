"""OpenDART disclosure collector -> disclosure table.

API docs: https://opendart.fss.or.kr/guide/main.do
Uses the `list.json` endpoint (recent disclosures for one corp_code).
"""
import io
import logging
import zipfile
from datetime import datetime, timedelta
from xml.etree import ElementTree

import requests

import config
from db.db import get_conn, insert_disclosure

log = logging.getLogger(__name__)

LIST_URL = "https://opendart.fss.or.kr/api/list.json"
CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"


def resolve_corp_code(corp_name_hint: str) -> str | None:
    """Fallback lookup: downloads OpenDART's full corp_code master list and matches by name.
    Only needed if DART_CORP_CODE in .env is wrong/blank."""
    if not config.OPENDART_API_KEY:
        log.error("OPENDART_API_KEY missing; cannot resolve corp_code")
        return None
    resp = requests.get(CORP_CODE_URL, params={"crtfc_key": config.OPENDART_API_KEY}, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_bytes = zf.read("CORPCODE.xml")
    root = ElementTree.fromstring(xml_bytes)
    for item in root.iter("list"):
        name = item.findtext("corp_name", "")
        if name == corp_name_hint:
            return item.findtext("corp_code")
    log.warning("No exact corp_code match for %s", corp_name_hint)
    return None


def collect_disclosures(days_back: int = 30):
    if not config.OPENDART_API_KEY:
        log.error("OPENDART_API_KEY missing in .env — skipping disclosure collection")
        return 0

    corp_code = config.DART_CORP_CODE or resolve_corp_code(config.DART_CORP_NAME_HINT)
    if not corp_code:
        log.error("No corp_code available — skipping disclosure collection")
        return 0

    end_de = datetime.now().strftime("%Y%m%d")
    bgn_de = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")

    inserted = 0
    page_no = 1
    with get_conn() as conn:
        while True:
            resp = requests.get(
                LIST_URL,
                params={
                    "crtfc_key": config.OPENDART_API_KEY,
                    "corp_code": corp_code,
                    "bgn_de": bgn_de,
                    "end_de": end_de,
                    "page_no": page_no,
                    "page_count": 100,
                },
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()

            status = payload.get("status")
            if status == "013":  # OpenDART's "no data found" code
                break
            if status != "000":
                log.error("OpenDART API error %s: %s", status, payload.get("message"))
                break

            for item in payload.get("list", []):
                report_date = item["rcept_dt"]
                report_date_iso = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:]}"
                n = insert_disclosure(
                    conn,
                    corp_code=corp_code,
                    report_name=item.get("report_nm"),
                    report_date=report_date_iso,
                    report_type=item.get("pblntf_ty"),
                    raw_summary=f"{item.get('flr_nm', '')} / {item.get('rm', '')}".strip(" /"),
                )
                inserted += n

            total_page = payload.get("total_page", 1)
            if page_no >= total_page:
                break
            page_no += 1

    log.info("disclosure: %d new rows inserted for corp_code=%s", inserted, corp_code)
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from db.db import init_db

    init_db()
    collect_disclosures()
