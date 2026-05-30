from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algos.a_regime_hrp_hmv_cvt import allocation_diagnostics  # noqa: E402


def test_a_cash_diagnostics_flags_cash_collapse():
    weights = pd.Series({"SPY": 0.02, "QQQ": 0.03, "__CASH__": 0.95})

    diagnostics = allocation_diagnostics(weights)

    assert diagnostics["cash_weight"] == 0.95
    assert diagnostics["gross_risky_exposure"] == 0.05
    assert diagnostics["cash_collapse_warning"] is True
    assert diagnostics["policy_verdict"] == "HOLD_DIAGNOSTIC_ONLY"


def test_a_cash_diagnostics_allows_meaningful_risky_exposure():
    weights = pd.Series({"SPY": 0.30, "QQQ": 0.20, "__CASH__": 0.50})

    diagnostics = allocation_diagnostics(weights)

    assert diagnostics["cash_weight"] == 0.50
    assert diagnostics["gross_risky_exposure"] == 0.50
    assert diagnostics["cash_collapse_warning"] is False
