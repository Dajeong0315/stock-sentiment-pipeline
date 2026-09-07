"""SQLite connection + append-only insert helpers with duplicate protection via UNIQUE constraints."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import config

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def init_db():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_stock_price(conn, ticker, trade_date, open_, high, low, close, volume):
    cur = conn.execute(
        """INSERT OR IGNORE INTO stock_price (ticker, trade_date, open, high, low, close, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ticker, trade_date, open_, high, low, close, volume),
    )
    return cur.rowcount


def insert_disclosure(conn, corp_code, report_name, report_date, report_type, raw_summary):
    cur = conn.execute(
        """INSERT OR IGNORE INTO disclosure (corp_code, report_name, report_date, report_type, raw_summary)
           VALUES (?, ?, ?, ?, ?)""",
        (corp_code, report_name, report_date, report_type, raw_summary),
    )
    return cur.rowcount


def insert_news(conn, ticker, news_date, title, content, url, rule_sentiment_score=None):
    cur = conn.execute(
        """INSERT OR IGNORE INTO news (ticker, news_date, title, content, url, rule_sentiment_score)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (ticker, news_date, title, content, url, rule_sentiment_score),
    )
    return cur.rowcount


def update_news_llm_sentiment(conn, news_id, llm_sentiment_score, llm_model_used):
    conn.execute(
        "UPDATE news SET llm_sentiment_score = ?, llm_model_used = ? WHERE id = ?",
        (llm_sentiment_score, llm_model_used, news_id),
    )


def insert_prediction_log(conn, ticker, predict_date, model_name, predicted_value, actual_value, metric_rmse):
    conn.execute(
        """INSERT INTO prediction_log (ticker, predict_date, model_name, predicted_value, actual_value, metric_rmse)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (ticker, predict_date, model_name, predicted_value, actual_value, metric_rmse),
    )


def count_rows(conn, table):
    return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
