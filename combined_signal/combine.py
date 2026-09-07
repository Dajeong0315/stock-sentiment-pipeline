"""Mini prototype: combine the price-prediction signal and the news-sentiment signal into
one composite score. A weighted sum, not a second model — this is meant to demonstrate
signal fusion, not to be a production trading strategy."""
import logging
from datetime import datetime, timedelta

import config
from analysis.model import predict_latest_return
from db.db import get_conn

log = logging.getLogger(__name__)

PRICE_WEIGHT = 0.6
SENTIMENT_WEIGHT = 0.4
SENTIMENT_LOOKBACK_DAYS = 3
BUY_THRESHOLD = 0.15
SELL_THRESHOLD = -0.15

# Predicted returns are tiny (e.g. 0.01 = 1%); this scales them onto roughly the same
# [-1, 1] range as sentiment scores before combining.
RETURN_SCALE = 20.0


def _recent_sentiment_mean(ticker: str, days: int = SENTIMENT_LOOKBACK_DAYS) -> float:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT AVG(COALESCE(llm_sentiment_score, rule_sentiment_score)) AS avg_score "
            "FROM news WHERE ticker = ? AND news_date >= ?",
            (ticker, cutoff),
        ).fetchone()
    return float(row["avg_score"]) if row and row["avg_score"] is not None else 0.0


def _label(composite: float) -> str:
    if composite > BUY_THRESHOLD:
        return "BUY"
    if composite < SELL_THRESHOLD:
        return "SELL"
    return "HOLD"


def compute_composite_signal(ticker: str = None) -> dict:
    ticker = ticker or config.TICKER
    predicted_return = predict_latest_return(ticker)
    sentiment_mean = _recent_sentiment_mean(ticker)

    price_signal = max(-1.0, min(1.0, predicted_return * RETURN_SCALE))
    composite = PRICE_WEIGHT * price_signal + SENTIMENT_WEIGHT * sentiment_mean

    result = {
        "ticker": ticker,
        "predicted_next_return": predicted_return,
        "price_signal": price_signal,
        "sentiment_signal": sentiment_mean,
        "composite_signal": composite,
        "label": _label(composite),
    }
    log.info("Composite signal: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(compute_composite_signal())
