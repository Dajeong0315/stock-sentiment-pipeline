from nlp.rule_sentiment import score_text


def test_positive_headline_scores_above_zero():
    assert score_text("삼성전자 영업이익 급등, 반도체 업황 회복 훈풍") > 0


def test_negative_headline_scores_below_zero():
    assert score_text("삼성전자 실적 부진, 반도체 업황 침체 우려 확대") < 0


def test_neutral_headline_scores_zero():
    assert score_text("삼성전자 신제품 출시 행사 일정 공개") == 0.0


def test_negation_flips_polarity():
    positive = score_text("실적이 개선됐다")
    negated = score_text("실적이 개선되지 않았다")
    assert negated < positive


def test_empty_text_scores_zero():
    assert score_text("") == 0.0
