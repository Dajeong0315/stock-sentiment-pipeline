from combined_signal.combine import BUY_THRESHOLD, SELL_THRESHOLD, _label


def test_label_buy_above_threshold():
    assert _label(BUY_THRESHOLD + 0.01) == "BUY"


def test_label_sell_below_threshold():
    assert _label(SELL_THRESHOLD - 0.01) == "SELL"


def test_label_hold_in_between():
    assert _label(0.0) == "HOLD"
