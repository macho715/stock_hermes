from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algos.b_meta_temporal_conformal_gate import build_weights_from_signals  # noqa: E402


def test_b_default_long_only_caps_single_signal_and_sends_residual_to_cash():
    signals = pd.DataFrame({
        "Asset": ["QQQ"],
        "trade": [True],
        "raw_weight_score": [10.0],
    })

    weights = build_weights_from_signals(
        signals,
        max_weight=0.25,
        long_short=False,
        gross_cap=1.0,
        cash=True,
    )

    assert weights["QQQ"] == 0.25
    assert weights["__CASH__"] == 0.75
    assert abs(float(weights.sum()) - 1.0) < 1e-12


def test_b_fully_invested_preserves_legacy_single_signal_behavior():
    signals = pd.DataFrame({
        "Asset": ["QQQ"],
        "trade": [True],
        "raw_weight_score": [10.0],
    })

    weights = build_weights_from_signals(
        signals,
        max_weight=0.25,
        long_short=False,
        gross_cap=1.0,
        cash=True,
        fully_invested=True,
    )

    assert weights["QQQ"] == 1.0
    assert "__CASH__" not in weights
