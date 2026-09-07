"""Feature engineering: price technicals (moving averages, volatility) + daily aggregated
rule-based news sentiment, joined into one modeling frame keyed by trade_date."""
import pandas as pd

import config
from db.db import get_conn

MA_WINDOWS = (5, 10, 20)
VOL_WINDOWS = (5, 10, 20)


def load_price_df(ticker: str = None) -> pd.DataFrame:
    ticker = ticker or config.TICKER
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT trade_date, open, high, low, close, volume FROM stock_price "
            "WHERE ticker = ? ORDER BY trade_date",
            conn,
            params=(ticker,),
        )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date")


def load_daily_sentiment(ticker: str = None) -> pd.DataFrame:
    ticker = ticker or config.TICKER
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT news_date, rule_sentiment_score, llm_sentiment_score FROM news WHERE ticker = ?",
            conn,
            params=(ticker,),
        )
    if df.empty:
        return pd.DataFrame(columns=["rule_sentiment_mean", "llm_sentiment_mean", "news_count"])
    df["news_date"] = pd.to_datetime(df["news_date"])
    daily = df.groupby("news_date").agg(
        rule_sentiment_mean=("rule_sentiment_score", "mean"),
        llm_sentiment_mean=("llm_sentiment_score", "mean"),
        news_count=("rule_sentiment_score", "size"),
    )
    return daily


def build_feature_frame(ticker: str = None) -> pd.DataFrame:
    """One row per trading day: price technicals + same-day sentiment + next-day return target."""
    price = load_price_df(ticker)
    sentiment = load_daily_sentiment(ticker)

    df = price.join(sentiment, how="left")
    df["news_count"] = df["news_count"].fillna(0)
    df["rule_sentiment_mean"] = df["rule_sentiment_mean"].fillna(0.0)
    df["llm_sentiment_mean"] = df["llm_sentiment_mean"]  # left as NaN where no LLM score yet

    df["daily_return"] = df["close"].pct_change()
    for w in MA_WINDOWS:
        df[f"ma_{w}"] = df["close"].rolling(w).mean()
    for w in VOL_WINDOWS:
        df[f"vol_{w}"] = df["daily_return"].rolling(w).std()

    df["target_next_return"] = df["close"].pct_change().shift(-1)

    feature_cols = (
        [f"ma_{w}" for w in MA_WINDOWS]
        + [f"vol_{w}" for w in VOL_WINDOWS]
        + ["daily_return", "rule_sentiment_mean", "news_count", "volume"]
    )
    model_df = df.dropna(subset=feature_cols + ["target_next_return"]).copy()
    model_df.attrs["feature_cols"] = feature_cols
    return model_df


if __name__ == "__main__":
    frame = build_feature_frame()
    print(frame.tail())
    print("rows:", len(frame), "features:", frame.attrs["feature_cols"])
