"""scikit-learn regression: predict next-day return from price technicals + rule-based
sentiment. Time-ordered train/test split (no shuffling — this is a time series)."""
import logging

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error

import config
from analysis.features import build_feature_frame
from db.db import get_conn, insert_prediction_log

log = logging.getLogger(__name__)

TEST_FRACTION = 0.2


def _time_split(df, test_fraction=TEST_FRACTION):
    split_idx = int(len(df) * (1 - test_fraction))
    return df.iloc[:split_idx], df.iloc[split_idx:]


def train_and_evaluate(ticker: str = None):
    ticker = ticker or config.TICKER
    df = build_feature_frame(ticker)
    feature_cols = df.attrs["feature_cols"]

    if len(df) < 15:
        log.warning("Only %d usable rows — need more price history for a meaningful model", len(df))

    train_df, test_df = _time_split(df)
    X_train, y_train = train_df[feature_cols], train_df["target_next_return"]
    X_test, y_test = test_df[feature_cols], test_df["target_next_return"]

    models = {
        "ridge": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(n_estimators=200, max_depth=4, random_state=42),
    }

    results = {}
    with get_conn() as conn:
        for name, model in models.items():
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
            # naive baseline: "no change" (predict 0 return) for comparison
            baseline_rmse = float(np.sqrt(mean_squared_error(y_test, np.zeros_like(y_test))))
            results[name] = {"rmse": rmse, "baseline_rmse": baseline_rmse, "n_test": len(y_test)}

            for date, pred, actual in zip(test_df.index, preds, y_test):
                insert_prediction_log(
                    conn,
                    ticker=ticker,
                    predict_date=date.strftime("%Y-%m-%d"),
                    model_name=name,
                    predicted_value=float(pred),
                    actual_value=float(actual),
                    metric_rmse=rmse,
                )

    log.info("Model results: %s", results)
    return results


def predict_latest_return(ticker: str = None, model_name: str = "ridge") -> float:
    """Fits on all available history and predicts the *next* day's return from the most
    recent feature row (which has no target yet, since tomorrow hasn't happened)."""
    ticker = ticker or config.TICKER
    from analysis.features import MA_WINDOWS, VOL_WINDOWS, load_daily_sentiment, load_price_df

    price = load_price_df(ticker)
    sentiment = load_daily_sentiment(ticker)
    df = price.join(sentiment, how="left")
    df["news_count"] = df["news_count"].fillna(0)
    df["rule_sentiment_mean"] = df["rule_sentiment_mean"].fillna(0.0)
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
    train_rows = df.dropna(subset=feature_cols + ["target_next_return"])
    latest_row = df.dropna(subset=feature_cols).iloc[[-1]]

    model = Ridge(alpha=1.0) if model_name == "ridge" else RandomForestRegressor(
        n_estimators=200, max_depth=4, random_state=42
    )
    model.fit(train_rows[feature_cols], train_rows["target_next_return"])
    return float(model.predict(latest_row[feature_cols])[0])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from db.db import init_db

    init_db()
    print(train_and_evaluate())
