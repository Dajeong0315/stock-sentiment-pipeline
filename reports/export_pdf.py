"""Markdown report -> PDF, via headless Chrome's print-to-PDF (reuses the same Chrome the
news collector already drives — no new PDF-rendering dependency, and Korean text renders
correctly for free since Chrome uses whatever CJK fonts the OS already has installed).
"""
import base64
import logging

import markdown

import config
from collectors.chrome_driver import build_headless_chrome

log = logging.getLogger(__name__)

_HTML_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><style>
body {{ font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; line-height: 1.6;
       max-width: 800px; margin: 2em auto; color: #1a1a1a; }}
h1, h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }}
code {{ background: #f0f0f0; padding: 0.1em 0.3em; }}
</style></head><body>{body}</body></html>"""


def markdown_to_pdf(md_path, pdf_path) -> None:
    html_body = markdown.markdown(md_path.read_text(encoding="utf-8"))
    html = _HTML_TEMPLATE.format(body=html_body)

    tmp_html_path = md_path.with_suffix(".tmp.html")
    tmp_html_path.write_text(html, encoding="utf-8")

    driver = build_headless_chrome()
    try:
        driver.get(tmp_html_path.resolve().as_uri())
        result = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True})
        pdf_path.write_bytes(base64.b64decode(result["data"]))
    finally:
        driver.quit()
        tmp_html_path.unlink(missing_ok=True)

    log.info("PDF written to %s", pdf_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    markdown_to_pdf(config.REPORT_DIR / "latest_report.md", config.REPORT_DIR / "latest_report.pdf")
