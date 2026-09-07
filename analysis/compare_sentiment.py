"""Runs the local Ollama LLM over news rows missing an llm_sentiment_score, then compares
rule-based vs LLM sentiment: agreement rate (same polarity bucket) + top disagreements.
"""
import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config
from db.db import get_conn, update_news_llm_sentiment
from nlp.llm_sentiment import score_text as llm_score_text

log = logging.getLogger(__name__)

# Rule-based scores are normalized by *total* morpheme count (see nlp/rule_sentiment.py),
# so even a genuine lexicon hit rarely exceeds ~0.05 — a 0.1 band would misclassify real
# signal as neutral. The LLM's scores cluster at {0, ±0.5, ±0.8} in practice, so a wider
# band is fine there. Each side gets a band calibrated to its own scale.
RULE_NEUTRAL_BAND = 0.005
LLM_NEUTRAL_BAND = 0.1


def _polarity_bucket(score: float, neutral_band: float) -> str:
    if score > neutral_band:
        return "positive"
    if score < -neutral_band:
        return "negative"
    return "neutral"


def run_llm_scoring(ticker: str = None):
    """Fills in llm_sentiment_score for any news row that doesn't have one yet."""
    ticker = ticker or config.TICKER
    scored, failed = 0, 0
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, content FROM news WHERE ticker = ? AND llm_sentiment_score IS NULL",
            (ticker,),
        ).fetchall()
        for row in rows:
            result = llm_score_text(row["title"], row["content"])
            if result["score"] is None:
                failed += 1
                continue
            update_news_llm_sentiment(conn, row["id"], result["score"], config.OLLAMA_MODEL)
            scored += 1
    log.info("LLM sentiment: %d scored, %d failed for ticker=%s", scored, failed, ticker)
    return {"scored": scored, "failed": failed}


def build_comparison(ticker: str = None) -> dict:
    ticker = ticker or config.TICKER
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT id, news_date, title, rule_sentiment_score, llm_sentiment_score FROM news "
            "WHERE ticker = ? AND llm_sentiment_score IS NOT NULL",
            conn,
            params=(ticker,),
        )

    if df.empty:
        return {"agreement_rate": None, "n_compared": 0, "disagreements": [], "table": df}

    df["rule_bucket"] = df["rule_sentiment_score"].apply(_polarity_bucket, neutral_band=RULE_NEUTRAL_BAND)
    df["llm_bucket"] = df["llm_sentiment_score"].apply(_polarity_bucket, neutral_band=LLM_NEUTRAL_BAND)
    df["agree"] = df["rule_bucket"] == df["llm_bucket"]
    df["abs_diff"] = (df["rule_sentiment_score"] - df["llm_sentiment_score"]).abs()

    agreement_rate = float(df["agree"].mean() * 100)
    disagreements = (
        df[~df["agree"]].sort_values("abs_diff", ascending=False).head(3)[
            ["news_date", "title", "rule_sentiment_score", "llm_sentiment_score"]
        ]
    ).to_dict("records")

    return {"agreement_rate": agreement_rate, "n_compared": len(df), "disagreements": disagreements, "table": df}


def plot_comparison(df: pd.DataFrame, out_path):
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(df["rule_sentiment_score"], df["llm_sentiment_score"], alpha=0.7)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.axvline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("Rule-based sentiment score")
    ax.set_ylabel("LLM (Qwen2.5-3B) sentiment score")
    ax.set_title("Rule-based vs. Local LLM news sentiment")
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_llm_scoring()
    result = build_comparison()
    print({k: v for k, v in result.items() if k != "table"})
    if result["n_compared"]:
        plot_comparison(result["table"], config.REPORT_DIR / "sentiment_comparison.png")
