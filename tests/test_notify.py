import reports.notify as notify


def test_slack_noop_when_unconfigured(monkeypatch):
    monkeypatch.setattr(notify, "SLACK_WEBHOOK_URL", "")
    assert notify.notify_slack("hello") is False


def test_email_noop_when_unconfigured(monkeypatch):
    monkeypatch.setattr(notify, "SMTP_HOST", "")
    assert notify.notify_email("subject", "body") is False
