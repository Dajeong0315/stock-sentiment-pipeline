"""Main entry point.

--mode scheduled : collect price/disclosure/news + rule-based sentiment, log counts, exit.
                   (this is what the daily scheduler calls — no model training, no LLM calls,
                   no dashboard/report regeneration, so it stays fast and cheap to run hourly/daily)
--mode manual    : full pipeline — collect, then EDA/model, LLM sentiment scoring + comparison,
                   combined signal, markdown report + METRICS.md, then git commit.
"""
import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python scripts/run_pipeline.py`

import config
from collectors.dart_collector import collect_disclosures
from collectors.news_collector import collect_news
from collectors.price_collector import collect_price
from db.db import init_db

log = logging.getLogger(__name__)


def _run_collection():
    init_db()
    counts = {
        "stock_price": collect_price(),
        "disclosure": collect_disclosures(),
        "news": collect_news(),
    }
    log.info("Collection complete: %s", counts)
    return counts


def _git_commit(message: str):
    try:
        subprocess.run(["git", "add", "-A"], cwd=config.BASE_DIR, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", message], cwd=config.BASE_DIR, capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info("git commit created: %s", message)
        elif "nothing to commit" in result.stdout:
            log.info("git commit skipped: nothing changed")
        else:
            log.warning("git commit failed (%d): %s", result.returncode, (result.stdout + result.stderr).strip())
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log.warning("git commit failed: %s", e)


def run(mode: str):
    counts = _run_collection()

    if mode == "scheduled":
        log.info("Scheduled run finished. counts=%s", counts)
        return {"mode": mode, "counts": counts}

    from reports.generate_report import generate_report

    report_result = generate_report()
    log.info("Manual run finished. report=%s", report_result["report_path"])

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    _git_commit(f"Pipeline run ({mode}) {timestamp}: +{counts['stock_price']}price/"
                f"+{counts['disclosure']}disclosure/+{counts['news']}news")

    return {"mode": mode, "counts": counts, "report": report_result}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["scheduled", "manual"], default="manual")
    args = parser.parse_args()
    run(args.mode)
