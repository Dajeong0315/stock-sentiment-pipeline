from datetime import datetime, timedelta

from collectors.news_collector import _parse_naver_date


def test_relative_hours_ago():
    expected = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d")
    assert _parse_naver_date("2시간 전") == expected


def test_relative_days_ago():
    expected = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert _parse_naver_date("어제") == expected


def test_absolute_date():
    assert _parse_naver_date("2026.01.15.") == "2026-01-15"


def test_empty_defaults_to_today():
    assert _parse_naver_date("") == datetime.now().strftime("%Y-%m-%d")
