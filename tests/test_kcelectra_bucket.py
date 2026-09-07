import pytest

pytest.importorskip("torch")  # this module is only in requirements-kcelectra.txt, not core CI
from analysis.kcelectra_finetune import LABEL_TO_IDX, _bucket  # noqa: E402


def test_bucket_positive():
    assert _bucket(0.5, neutral_band=0.1) == LABEL_TO_IDX[1]


def test_bucket_negative():
    assert _bucket(-0.5, neutral_band=0.1) == LABEL_TO_IDX[-1]


def test_bucket_neutral_within_band():
    assert _bucket(0.02, neutral_band=0.1) == LABEL_TO_IDX[0]


def test_bucket_none_defaults_neutral():
    assert _bucket(None, neutral_band=0.1) == LABEL_TO_IDX[0]
