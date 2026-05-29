"""Leakage-free time-series cross-validation: Purged K-Fold with embargo.

[REFERENCE IMPLEMENTATION]
This file is a reference implementation only. The operating implementation
is in src/stock_rtx4060/ml/cv.py ::PurgedKFold. Do not use this file as the
primary import; import from src.stock_rtx4060.ml.cv instead.

Implements the validation split described in INVESTMENT_INFORMATION_ALGORITHM_
RESEARCH_2026-05-29.md (§4.3 예측 계층, §5.1 step 7-9): time-ordered test folds,
*purging* of training samples whose label window overlaps a test fold, and an
*embargo* removing serially-correlated samples immediately after each test block.

Reference: M. López de Prado, "Advances in Financial Machine Learning" (2018),
Ch. 7 — PurgedKFold. scikit-learn TimeSeriesSplit does NOT purge or embargo and
therefore leaks information through overlapping label horizons.

Standalone: depends only on numpy and pandas. sklearn-compatible `split()`.

Time:  O(n_splits * n)      Space: O(n)
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd


def make_label_endtimes(
    start_times: pd.DatetimeIndex, horizon: pd.Timedelta
) -> pd.Series:
    """Build the t1 Series (index=prediction start, value=label end) from a fixed
    horizon. Convenience for fixed-holding-period labels (e.g. Track-S/Track-L).

    Time: O(n)  Space: O(n)
    """
    start_times = pd.DatetimeIndex(start_times)
    return pd.Series(start_times + horizon, index=start_times)


@dataclass
class PurgedKFoldEmbargo:
    """Purged K-Fold CV with embargo for leakage-free time-series validation.

    Each sample i has a prediction start time ``t1.index[i]`` and a label
    realization end time ``t1.values[i]`` (start <= end). Test folds are
    contiguous blocks of the time-ordered samples. A training sample is kept
    only if its label window is disjoint from the test fold's time span;
    overlapping samples are *purged*. An *embargo* of ``embargo_pct`` of all
    samples immediately following each test block is additionally dropped.

    Parameters
    ----------
    t1 : pd.Series
        Index = prediction start time (must be monotonic increasing), value =
        label end time. ``value >= index`` is required for every sample.
    n_splits : int
        Number of folds (>= 2).
    embargo_pct : float
        Embargo size as a fraction of the total sample count, in [0, 1).
        Implemented as a count of samples after the test block (a deterministic
        simplification of López de Prado's time-based embargo).

    Time:  O(n_splits * n)   Space: O(n)
    """

    t1: pd.Series
    n_splits: int = 5
    embargo_pct: float = 0.01

    def __post_init__(self) -> None:
        if not isinstance(self.t1, pd.Series):
            raise TypeError("t1 must be a pandas Series (index=start, value=end)")
        if self.n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        if not (0.0 <= self.embargo_pct < 1.0):
            raise ValueError("embargo_pct must be in [0, 1)")
        if len(self.t1) < self.n_splits:
            raise ValueError("need at least n_splits samples")
        if not self.t1.index.is_monotonic_increasing:
            raise ValueError("t1 must be sorted by prediction start time")
        # label end must not precede prediction start (no negative horizon)
        if (self.t1.to_numpy() < self.t1.index.to_numpy()).any():
            raise ValueError("every label end time must be >= its start time")

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return self.n_splits

    def split(
        self, X: object | None = None, y=None, groups=None
    ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        """Yield (train_idx, test_idx) positional integer arrays per fold.

        ``X`` is accepted for sklearn API compatibility but unused: the split is
        defined entirely by ``t1``. If supplied, its length must match ``t1``.
        """
        n = len(self.t1)
        if X is not None and hasattr(X, "__len__") and len(X) != n:
            raise ValueError("X length does not match t1 length")

        indices = np.arange(n)
        starts = self.t1.index.to_numpy()      # prediction start times
        ends = self.t1.to_numpy()              # label end times
        embargo = int(n * self.embargo_pct)

        for test_block in np.array_split(indices, self.n_splits):
            lo, hi = test_block[0], test_block[-1]          # inclusive bounds
            test_idx = indices[lo : hi + 1]

            t_start = starts[lo]                            # earliest test start
            t_end = ends[lo : hi + 1].max()                 # latest test label end

            train_mask = np.ones(n, dtype=bool)
            train_mask[lo : hi + 1] = False                 # exclude test itself

            # Purge: drop any train sample whose window [start, end] overlaps the
            # test span [t_start, t_end]. Intervals overlap iff start <= t_end and
            # end >= t_start.
            overlap = (starts <= t_end) & (ends >= t_start)
            train_mask &= ~overlap

            # Embargo: drop the `embargo` samples immediately after the test block.
            if embargo > 0:
                emb_end = min(hi + 1 + embargo, n)
                train_mask[hi + 1 : emb_end] = False

            yield indices[train_mask], test_idx


__all__ = ["PurgedKFoldEmbargo", "make_label_endtimes"]
