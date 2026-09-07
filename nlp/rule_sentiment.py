"""Rule-based sentiment scoring: regex cleaning -> Kiwi morphological analysis -> lexicon lookup.

Score is in [-1, 1]: (positive_hits - negative_hits) / total_tokens, with a naive
negation flip when a negation morpheme appears within 2 tokens either side of a sentiment
word — Korean negates both ways ("안 좋다" precedes the stem, "좋지 않다" follows it).
"""
from kiwipiepy import Kiwi

from nlp.lexicon import NEGATION_WORDS, NEGATIVE_WORDS, POSITIVE_WORDS
from nlp.text_clean import clean_text

_kiwi = Kiwi()

NEGATION_WINDOW = 4  # wide enough to bridge "-되지 않다"-style suffix chains (stem+되+지+않)


def score_text(raw_text: str) -> float:
    text = clean_text(raw_text)
    if not text:
        return 0.0

    tokens = _kiwi.tokenize(text)
    if not tokens:
        return 0.0

    forms = [t.form for t in tokens]
    hits = 0
    for i, form in enumerate(forms):
        polarity = 0
        if form in POSITIVE_WORDS:
            polarity = 1
        elif form in NEGATIVE_WORDS:
            polarity = -1
        else:
            continue

        window_start = max(0, i - NEGATION_WINDOW)
        window_end = min(len(forms), i + 1 + NEGATION_WINDOW)
        nearby = forms[window_start:i] + forms[i + 1 : window_end]
        if any(f in NEGATION_WORDS for f in nearby):
            polarity *= -1

        hits += polarity

    return max(-1.0, min(1.0, hits / len(tokens)))


if __name__ == "__main__":
    samples = [
        "삼성전자 4분기 영업이익 급등, 반도체 업황 회복 훈풍",
        "삼성전자 실적 부진, 반도체 업황 침체 우려 확대",
        "삼성전자 신제품 출시, 시장 반응은 아직 미지수",
    ]
    for s in samples:
        print(f"{score_text(s):+.3f}  {s}")
