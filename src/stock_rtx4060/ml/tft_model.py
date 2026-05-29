"""Temporal Fusion Transformer (TFT) — optional 4th ensemble model stub.

Wave 4 BEST-3: adds TFT as a gracefully-degrading 4th model alongside
LightGBM, XGBoost, and GRU/LSTM.  The implementation is intentionally
progressive:

* **Phase 1 (this file)**: stub that returns 0.5 (no-op) when
  ``pytorch_forecasting`` or ``torch`` is absent — CI safe.
* **Phase 2**: implement :meth:`TFTPredictor.fit` and :meth:`TFTPredictor.predict`
  with proper ``TimeSeriesDataSet`` wiring.

Feature flag: ``TFT_MODEL_ENABLED=true`` (default: false).
"""

from __future__ import annotations

import logging
import os
from typing import Any

_LOGGER = logging.getLogger("stock_rtx4060.ml.tft_model")

# ---------------------------------------------------------------------------
# Optional import guard
# ---------------------------------------------------------------------------
try:
    import torch  # type: ignore[import-not-found]  # noqa: F401
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet  # type: ignore[import-not-found]

    _TFT_AVAILABLE = True
except Exception:  # pragma: no cover — torch / pytorch_forecasting optional
    _TFT_AVAILABLE = False

TFT_MODEL_ENABLED: bool = os.environ.get("TFT_MODEL_ENABLED", "false").lower() in (
    "1", "true", "yes"
)


class TFTPredictor:  # pragma: no cover — guarded by _TFT_AVAILABLE in all entry points
    """Temporal Fusion Transformer wrapper — optional 4th ensemble model.

    When ``_TFT_AVAILABLE`` is ``False`` (no torch / pytorch_forecasting),
    :meth:`fit` is a no-op and :meth:`predict` returns ``0.5`` for every
    sample so the ensemble still runs with three models.

    Parameters
    ----------
    max_epochs:
        Training epochs.  Kept small for daily research flows.
    hidden_size:
        TFT hidden state size.  Scales model capacity vs. latency.
    """

    def __init__(
        self,
        max_epochs: int = 30,
        hidden_size: int = 64,
        learning_rate: float = 1e-3,
    ) -> None:
        self.max_epochs = max_epochs
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self._model: Any = None
        self._trained = False

    # ------------------------------------------------------------------
    # Public API — mirrors the _make_* pattern in ensemble_model.py
    # ------------------------------------------------------------------

    def fit(
        self,
        X_train: Any,
        y_train: Any,
        *,
        time_idx: Any = None,
        group_ids: Any = None,
    ) -> None:
        """Fit the TFT model.

        Phase 1 stub: logs a warning and returns without training when
        ``pytorch_forecasting`` is absent.
        """
        if not _TFT_AVAILABLE:
            _LOGGER.warning(
                "TFTPredictor.fit: pytorch_forecasting not installed — skipping TFT training. "
                "Install with: pip install pytorch_forecasting torch"
            )
            return
        # Phase 2: implement TimeSeriesDataSet + Trainer here.
        raise NotImplementedError(
            "TFTPredictor.fit Phase 2 not yet implemented. "
            "See docs/plan.md BEST-3 PR-T2 for the implementation plan."
        )

    def predict(self, X: Any) -> list[float]:
        """Return predicted probabilities in [0, 1].

        Phase 1 stub: returns 0.5 for every sample when not trained or when
        ``pytorch_forecasting`` is absent.
        """
        if not _TFT_AVAILABLE or not self._trained:
            n = len(X) if hasattr(X, "__len__") else 1
            return [0.5] * n
        # Phase 2: implement inference here.
        raise NotImplementedError("TFTPredictor.predict Phase 2 not yet implemented.")

    @property
    def is_available(self) -> bool:
        """``True`` when pytorch_forecasting is installed and the model is trained."""
        return _TFT_AVAILABLE and self._trained


def make_tft_predictor(
    *,
    max_epochs: int = 30,
    hidden_size: int = 64,
) -> TFTPredictor | None:
    """Return a :class:`TFTPredictor` when the feature flag is on, else ``None``.

    Used by :mod:`stock_rtx4060.ensemble_model` as the ``_make_tft()`` factory.
    Returning ``None`` means the ensemble skips TFT silently — no error raised.
    """
    if not TFT_MODEL_ENABLED:
        return None
    return TFTPredictor(max_epochs=max_epochs, hidden_size=hidden_size)


__all__ = ["TFTPredictor", "make_tft_predictor", "_TFT_AVAILABLE", "TFT_MODEL_ENABLED"]
