"""Optional result notification via Slack webhook and/or email (SMTP).
Both are no-ops if their .env vars aren't set — nothing breaks for users who skip this.

ponytail: not verified against a real Slack workspace or mail server (no credentials
available in this environment) — reasoned through against each service's plain documented
interface (Slack incoming webhooks, stdlib smtplib), not tested end to end.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

import requests

log = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def notify_slack(text: str) -> bool:
    if not SLACK_WEBHOOK_URL:
        return False
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("Slack notification failed: %s", e)
        return False


def notify_email(subject: str, body: str) -> bool:
    if not (NOTIFY_EMAIL_TO and SMTP_HOST and SMTP_USER and SMTP_PASSWORD):
        return False
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL_TO
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as e:
        log.warning("Email notification failed: %s", e)
        return False


def notify_run_result(ticker: str, signal: dict, counts: dict) -> None:
    text = (
        f"[{ticker}] 파이프라인 실행 완료\n"
        f"수집: 주가+{counts['stock_price']} 공시+{counts['disclosure']} 뉴스+{counts['news']}\n"
        f"종합 시그널: {signal['label']} (score={signal['composite_signal']:+.3f})"
    )
    sent_slack = notify_slack(text)
    sent_email = notify_email(f"[{ticker}] 파이프라인 실행 결과: {signal['label']}", text)
    if not sent_slack and not sent_email:
        log.info("No notification channel configured (SLACK_WEBHOOK_URL / SMTP_* unset) — skipped")
