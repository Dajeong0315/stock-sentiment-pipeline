"""Generates a markdown analysis report for the latest pipeline run.
Writes reports/output/latest_report.md (overwritten each run) and a dated copy."""
import logging
from datetime import datetime

import config
from analysis.compare_sentiment import build_comparison, plot_comparison, run_llm_scoring
from analysis.model import train_and_evaluate
from combined_signal.combine import compute_composite_signal
from db.db import count_rows, get_conn
from reports.metrics_writer import write_metrics

log = logging.getLogger(__name__)


def _disclosure_summary(limit=10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT report_date, report_name FROM disclosure ORDER BY report_date DESC LIMIT ?", (limit,)
        ).fetchall()
    return rows


def generate_report(ticker: str = None) -> dict:
    ticker = ticker or config.TICKER

    model_results = train_and_evaluate(ticker)
    run_llm_scoring(ticker)
    comparison = build_comparison(ticker)
    chart_path = None
    if comparison["n_compared"]:
        chart_path = plot_comparison(comparison["table"], config.REPORT_DIR / "sentiment_comparison.png")
    signal = compute_composite_signal(ticker)

    with get_conn() as conn:
        n_price = count_rows(conn, "stock_price")
        n_disclosure = count_rows(conn, "disclosure")
        n_news = count_rows(conn, "news")

    disclosures = _disclosure_summary()

    lines = [
        f"# {ticker} 통합 분석 리포트",
        "",
        f"_생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        "## 데이터 현황",
        f"- 주가 {n_price}건 / 공시 {n_disclosure}건 / 뉴스 {n_news}건 누적",
        "",
        "## 최근 공시",
    ]
    if disclosures:
        for r in disclosures:
            lines.append(f"- {r['report_date']}  {r['report_name']}")
    else:
        lines.append("- 최근 공시 없음")
    lines.append("")

    lines.append("## 가격예측 모델")
    for name, r in model_results.items():
        lines.append(f"- {name}: RMSE={r['rmse']:.5f} (baseline RMSE={r['baseline_rmse']:.5f})")
    lines.append("")

    lines.append("## 규칙기반 vs 로컬 LLM 감정 비교")
    if comparison["n_compared"]:
        lines.append(f"- 일치율: {comparison['agreement_rate']:.1f}% (n={comparison['n_compared']})")
        if chart_path:
            lines.append(f"- 비교 차트: `{chart_path.relative_to(config.BASE_DIR)}`")
        lines.append("- 대표 불일치 사례:")
        for d in comparison["disagreements"]:
            lines.append(f"  - \"{d['title']}\" (규칙기반 {d['rule_sentiment_score']:+.2f} / LLM {d['llm_sentiment_score']:+.2f})")
    else:
        lines.append("- 비교할 LLM 감정점수 없음")
    lines.append("")

    lines.append("## 종합 시그널 (가격예측 + 감정신호)")
    lines.append(
        f"- 종합 시그널: **{signal['label']}** (score={signal['composite_signal']:+.3f}, "
        f"price_signal={signal['price_signal']:+.3f}, sentiment_signal={signal['sentiment_signal']:+.3f})"
    )
    lines.append("")

    report_text = "\n".join(lines)

    dated_path = config.REPORT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    latest_path = config.REPORT_DIR / "latest_report.md"
    dated_path.write_text(report_text, encoding="utf-8")
    latest_path.write_text(report_text, encoding="utf-8")

    write_metrics(model_results=model_results, comparison_result=comparison)

    log.info("Report written to %s", latest_path)
    return {"report_path": latest_path, "model_results": model_results, "comparison": comparison, "signal": signal}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_report()
