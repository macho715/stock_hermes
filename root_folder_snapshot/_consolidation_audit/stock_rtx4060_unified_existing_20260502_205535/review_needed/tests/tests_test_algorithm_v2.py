from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import (  # noqa: E402
    test_backtester_basic,
    test_ensemble_leak_safe_cv,
    test_feature_engine_basic,
    test_feature_engine_edge,
    test_kelly_criterion,
    test_recommendation_engine_synthetic,
)
