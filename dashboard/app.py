"""Streamlit dashboard: price + moving averages, disclosure timeline, rule vs LLM sentiment
comparison, and the latest combined price+sentiment signal. Run with:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `streamlit run` from any cwd

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from analysis.compare_sentiment import build_comparison
from analysis.features import MA_WINDOWS, build_feature_frame, load_price_df
from combined_signal.combine import compute_composite_signal
from db.db import get_conn

st.set_page_config(page_title=f"{config.TICKER} 감정 x 가격 분석", layout="wide")

# Color palette — see the dataviz skill's palette convention: one neutral base,
# one accent for emphasis, semantic green/red reserved for positive/negative only.
COLOR_PRICE = "#2E5AAC"
COLOR_POSITIVE = "#1E8E5A"
COLOR_NEGATIVE = "#C0392B"
COLOR_NEUTRAL = "#8A8F98"
COLOR_MA = ("#F2A93B", "#9B6FD1", "#4FB6C4")


@st.cache_data(ttl=300)
def _load_price():
    return load_price_df()


@st.cache_data(ttl=300)
def _load_disclosures():
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT report_date, report_name, report_type FROM disclosure ORDER BY report_date DESC LIMIT 30",
            conn,
        )


@st.cache_data(ttl=300)
def _load_news():
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT news_date, title, rule_sentiment_score, llm_sentiment_score FROM news "
            "WHERE ticker = ? ORDER BY news_date DESC, id DESC LIMIT 50",
            conn,
            params=(config.TICKER,),
        )


st.title(f"{config.TICKER} 주가 · 공시 · 뉴스 감정 통합 대시보드")

price_df = _load_price()
if price_df.empty:
    st.warning("주가 데이터가 없습니다. `python -m collectors.price_collector`를 먼저 실행하세요.")
    st.stop()

col1, col2, col3 = st.columns(3)
latest_close = price_df["close"].iloc[-1]
prev_close = price_df["close"].iloc[-2] if len(price_df) > 1 else latest_close
col1.metric("최근 종가", f"{latest_close:,.0f}", f"{latest_close - prev_close:,.0f}")
col2.metric("누적 거래일 수", f"{len(price_df)}")

try:
    signal = compute_composite_signal()
    col3.metric("종합 시그널", signal["label"], f"{signal['composite_signal']:+.3f}")
except Exception as e:
    col3.metric("종합 시그널", "N/A")
    st.caption(f"시그널 계산 불가: {e}")

st.subheader("주가 추이 + 이동평균")
feat_df = build_feature_frame()
fig = go.Figure()
fig.add_trace(go.Scatter(x=price_df.index, y=price_df["close"], name="종가", line=dict(color=COLOR_PRICE, width=2)))
for w, c in zip(MA_WINDOWS, COLOR_MA):
    if f"ma_{w}" in feat_df.columns:
        fig.add_trace(go.Scatter(x=feat_df.index, y=feat_df[f"ma_{w}"], name=f"MA{w}", line=dict(color=c, width=1.3)))
fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.08))
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns([2, 1])

with left:
    st.subheader("규칙기반 vs 로컬 LLM 감정점수 비교")
    comparison = build_comparison()
    if comparison["n_compared"] == 0:
        st.info("아직 LLM 감정점수가 없습니다. `python -m analysis.compare_sentiment`를 실행하세요.")
    else:
        st.metric("일치율", f"{comparison['agreement_rate']:.1f}%", f"n={comparison['n_compared']}")
        table = comparison["table"][["news_date", "title", "rule_sentiment_score", "llm_sentiment_score", "agree"]]
        st.dataframe(table, use_container_width=True, hide_index=True)
        if comparison["disagreements"]:
            st.caption("대표 불일치 사례")
            for d in comparison["disagreements"]:
                st.write(
                    f"- **{d['title']}** — 규칙기반: {d['rule_sentiment_score']:+.2f} / "
                    f"LLM: {d['llm_sentiment_score']:+.2f}"
                )

with right:
    st.subheader("최근 공시")
    disclosures = _load_disclosures()
    if disclosures.empty:
        st.info("공시 데이터가 없습니다.")
    else:
        st.dataframe(disclosures, use_container_width=True, hide_index=True)

st.subheader("최신 뉴스")
news_df = _load_news()
if news_df.empty:
    st.info("뉴스 데이터가 없습니다.")
else:
    st.dataframe(news_df, use_container_width=True, hide_index=True)
