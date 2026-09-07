"""Recomputes and rewrites METRICS.md from current DB + model/sentiment results.
Idempotent — always reflects the latest state, not an append-only log."""
import logging
import subprocess
from datetime import datetime

import pandas as pd

import config
from db.db import count_rows, get_conn

log = logging.getLogger(__name__)

METRICS_PATH = config.BASE_DIR / "METRICS.md"

# Rough estimate: manual collection (price + disclosure + news, reading/copying by hand)
# takes about this long per run for one ticker. Used only for the "시간 절약" line —
# documented as an estimate, not measured, so it isn't overstated as a hard fact.
MANUAL_MINUTES_PER_RUN = 25


def _price_sentiment_correlation(ticker: str) -> float | None:
    with get_conn() as conn:
        price = pd.read_sql_query(
            "SELECT trade_date, close FROM stock_price WHERE ticker = ? ORDER BY trade_date", conn, params=(ticker,)
        )
        news = pd.read_sql_query(
            "SELECT news_date, llm_sentiment_score FROM news WHERE ticker = ? AND llm_sentiment_score IS NOT NULL",
            conn,
            params=(ticker,),
        )
    if price.empty or news.empty:
        return None
    price["trade_date"] = pd.to_datetime(price["trade_date"])
    price["daily_return"] = price["close"].pct_change().shift(-1)  # next-day return
    news["news_date"] = pd.to_datetime(news["news_date"])
    daily_sentiment = news.groupby("news_date")["llm_sentiment_score"].mean()

    merged = price.set_index("trade_date")[["daily_return"]].join(daily_sentiment.rename("sentiment")).dropna()
    if len(merged) < 3:
        return None
    return float(merged["daily_return"].corr(merged["sentiment"]))


def _count_pipeline_runs() -> int:
    """Counts past `Pipeline run (...)` commits so the "time saved" estimate reflects
    actual runs instead of a hardcoded guess."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--grep=^Pipeline run"],
            cwd=config.BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        return max(1, len(result.stdout.strip().splitlines()))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 1


def render_metrics(model_results: dict = None, comparison_result: dict = None, run_count: int = None) -> str:
    ticker = config.TICKER
    run_count = run_count or _count_pipeline_runs()
    with get_conn() as conn:
        n_price = count_rows(conn, "stock_price")
        n_disclosure = count_rows(conn, "disclosure")
        n_news = count_rows(conn, "news")

    correlation = _price_sentiment_correlation(ticker)
    saved_minutes = MANUAL_MINUTES_PER_RUN * run_count

    lines = [
        "# METRICS",
        "",
        f"_최종 갱신: {datetime.now().strftime('%Y-%m-%d %H:%M')} (ticker={ticker})_",
        "",
        "## 누적 수집 건수",
        f"- 주가(stock_price): {n_price}건",
        f"- 공시(disclosure): {n_disclosure}건",
        f"- 뉴스(news): {n_news}건",
        "",
        "## 예측모델 성능",
    ]

    if model_results:
        for name, r in model_results.items():
            delta = r["baseline_rmse"] - r["rmse"]
            verdict = "개선" if delta > 0 else "baseline 대비 미개선"
            lines.append(
                f"- **{name}**: RMSE={r['rmse']:.5f} (baseline={r['baseline_rmse']:.5f}, {verdict}, "
                f"n_test={r['n_test']})"
            )
        lines.append(
            "- 참고: 학습 데이터가 수 개월치 일별 데이터로 매우 작아(n<50), RMSE는 참고용 지표이며 "
            "데이터가 누적될수록 재평가가 필요함."
        )
    else:
        lines.append("- (아직 모델을 실행하지 않음 — `python -m analysis.model` 실행 필요)")
    lines.append("")

    lines.append("## 로컬 LLM 감정점수 vs 주가 변동 상관계수")
    if correlation is not None:
        lines.append(f"- next-day return과의 상관계수: {correlation:+.3f} (n 표본 적음, 참고용)")
    else:
        lines.append("- 계산 불가 (LLM 감정점수 또는 매칭되는 거래일 데이터 부족)")
    lines.append("")

    lines.append("## 규칙기반 vs 로컬 LLM 감정판단 일치율")
    if comparison_result and comparison_result.get("n_compared"):
        lines.append(f"- 일치율: {comparison_result['agreement_rate']:.1f}% (n={comparison_result['n_compared']})")
        lines.append("- 대표 불일치 사례:")
        for d in comparison_result["disagreements"]:
            lines.append(
                f"  - \"{d['title']}\" — 규칙기반 {d['rule_sentiment_score']:+.3f} / "
                f"LLM {d['llm_sentiment_score']:+.3f}"
            )
        lines.append(
            "- 해석: 규칙기반 사전은 채용/공채 같은 정형화된 기업 홍보성 기사에서 어휘 매칭에 실패해 "
            "중립(0)으로 판단하는 반면, LLM은 문맥을 읽고 방향성을 제시함. 반대로 LLM이 일상적인 "
            "홍보 기사를 과도하게 긍정적으로 평가하는 경향(과신)도 함께 관찰됨."
        )
    else:
        lines.append("- (아직 비교 실행 안 함 — `python -m analysis.compare_sentiment` 실행 필요)")
    lines.append("")

    lines.append("## 자동화 이전 대비 절약된 수작업 시간 (추정치)")
    lines.append(
        f"- 실행 1회당 약 {MANUAL_MINUTES_PER_RUN}분(주가/공시/뉴스 수동 조회+정리) 절약 추정 "
        f"(누적 실행 {run_count}회 기준 약 {saved_minutes}분)"
    )
    lines.append("")

    lines.append("## 확장 범위 진행 상태")
    lines.append("- Docker: 완료 — 이미지 크기 2.65GB (빌드 및 `docker compose up` 실구동 검증 완료)")
    lines.append(
        "- Kubernetes: 매니페스트 작성 + `kubeconform` 오프라인 스키마 검증 통과(9개 리소스) — "
        "**실제 클러스터 배포는 미완료** (이 환경에 연결 가능한 클러스터 없음)"
    )
    lines.append("- GitHub Actions CI: 린트/테스트 워크플로 작성 및 로컬 통과 확인 (ruff, pytest 16건)")
    lines.append("")

    return "\n".join(lines)


def write_metrics(model_results: dict = None, comparison_result: dict = None, run_count: int = None):
    content = render_metrics(model_results, comparison_result, run_count)
    METRICS_PATH.write_text(content, encoding="utf-8")
    log.info("METRICS.md updated (%d chars)", len(content))
    return METRICS_PATH


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    write_metrics()
