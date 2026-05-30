from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.run_cfast_validation import validate_latest_weights_schema  # noqa: E402


def test_latest_weights_schema_accepts_cash_and_unit_sum():
    weights = pd.DataFrame({
        "Asset": ["SPY", "__CASH__"],
        "Weight": [0.2, 0.8],
    })

    validate_latest_weights_schema(weights)


def test_latest_weights_schema_rejects_missing_cash():
    weights = pd.DataFrame({
        "Asset": ["SPY"],
        "Weight": [1.0],
    })

    with pytest.raises(ValueError, match="__CASH__"):
        validate_latest_weights_schema(weights)


def test_latest_weights_schema_rejects_non_unit_sum():
    weights = pd.DataFrame({
        "Asset": ["SPY", "__CASH__"],
        "Weight": [0.2, 0.7],
    })

    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_latest_weights_schema(weights)
