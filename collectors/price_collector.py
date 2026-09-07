"""Yahoo Finance OHLCV collector -> stock_price table."""
import logging

import yfinance as yf

import config
from db.db import get_conn, insert_stock_price

log = logging.getLogger(__name__)


def collect_price(period="3mo"):
    df = yf.Ticker(config.TICKER).history(period=period)
    if df.empty:
        log.warning("yfinance returned no rows for %s", config.TICKER)
        return 0

    inserted = 0
    with get_conn() as conn:
        for trade_date, row in df.iterrows():
            n = insert_stock_price(
                conn,
                ticker=config.TICKER,
                trade_date=trade_date.strftime("%Y-%m-%d"),
                open_=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            )
            inserted += n
    log.info("stock_price: %d new rows inserted for %s", inserted, config.TICKER)
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from db.db import init_db

    init_db()
    collect_price()
