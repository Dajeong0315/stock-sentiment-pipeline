"""Zero-shot news sentiment scoring via a local Ollama LLM (Qwen2.5-3B-Instruct, 4bit).

No fine-tuning / labeled dataset — a single prompt template asks the model to
return a JSON sentiment score in [-1, 1] for a stock-news headline+body.
"""
import json
import logging
import re

import requests

import config

log = logging.getLogger(__name__)

PROMPT_TEMPLATE = """당신은 한국 주식시장 뉴스의 감정을 분석하는 애널리스트입니다.
아래 뉴스가 종목 주가에 미칠 영향을 -1.0(매우 부정적)부터 1.0(매우 긍정적) 사이 점수로 평가하세요.
0.0은 중립입니다. 반드시 아래 JSON 형식으로만 답하세요. 다른 설명은 쓰지 마세요.

뉴스 제목: {title}
뉴스 본문: {content}

응답 형식: {{"score": <float>, "reason": "<한 문장 이유>"}}
"""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _call_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def score_text(title: str, content: str) -> dict:
    """Returns {"score": float, "reason": str}. On any parse/connection failure, score=None."""
    prompt = PROMPT_TEMPLATE.format(title=title or "", content=(content or "")[:1500])
    try:
        raw_response = _call_ollama(prompt)
    except requests.RequestException as e:
        log.error("Ollama request failed: %s", e)
        return {"score": None, "reason": f"ollama_error: {e}"}

    match = _JSON_RE.search(raw_response)
    if not match:
        log.warning("No JSON found in Ollama response: %r", raw_response[:200])
        return {"score": None, "reason": "unparseable_response"}

    try:
        parsed = json.loads(match.group())
        score = float(parsed["score"])
        return {"score": max(-1.0, min(1.0, score)), "reason": parsed.get("reason", "")}
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        log.warning("Failed to parse Ollama JSON: %s | raw=%r", e, raw_response[:200])
        return {"score": None, "reason": "parse_error"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = score_text(
        title="삼성전자 4분기 영업이익 급등, 반도체 업황 회복 훈풍",
        content="삼성전자가 4분기 시장 예상치를 상회하는 영업이익을 기록하며 반도체 업황 회복 기대감을 높였다.",
    )
    print(result)
