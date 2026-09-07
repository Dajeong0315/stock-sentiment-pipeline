"""Local scheduler: runs the collection-only pipeline once a day. Keep this process
running (e.g. in a terminal, or as a Windows service/Task) — it blocks forever.

    python -m scheduler.daily_job

Alternative for Windows without a long-running process: register a Task Scheduler
job that runs `python scripts/run_pipeline.py --mode scheduled` daily instead —
see README.md for the exact `schtasks` command.
"""
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

import config
from scripts.run_pipeline import run

log = logging.getLogger(__name__)

RUN_HOUR = int(os.getenv("SCHEDULER_HOUR", "8"))
RUN_MINUTE = int(os.getenv("SCHEDULER_MINUTE", "0"))


def _job():
    log.info("Daily scheduled collection starting for %s", config.TICKER)
    try:
        run(mode="scheduled")
    except Exception:
        log.exception("Scheduled run failed")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(config.LOG_DIR / "scheduler.log", encoding="utf-8")],
    )
    scheduler = BlockingScheduler()
    scheduler.add_job(_job, "cron", hour=RUN_HOUR, minute=RUN_MINUTE, id="daily_collection")
    log.info("Scheduler started — daily run at %02d:%02d", RUN_HOUR, RUN_MINUTE)
    scheduler.start()
