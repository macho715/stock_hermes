"""Purged K-Fold cross-validation per López de Prado, AFML §7.

The standard scikit-learn ``KFold`` / ``TimeSeriesSplit`` splitters do not
respect the fact that financial labels frequently overlap their feature
windows: a label at time ``t`` may depend on prices realised at ``t + h``.
That overlap leaks information from the test fold into the training fold.
Purged K-Fold removes (purges) any training observation whose label horizon
intersects the held-out test fold, and inserts a small *embargo* gap after
each test fold to defend against serial autocorrelation across the boundary.

Reference: López de Prado, *Advances in Financial Machine Learning*,
Chapter 7 ("Cross-Validation in Finance").
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd


class PurgedKFold:
    """sklearn-compatible purged K-Fold splitter with embargo.

    Parameters
    ----------
    n_splits:
        Number of folds. Must be at least 2.
    embargo_pct:
        Fraction of total samples used as an embargo gap inserted *after*
        each test fold. ``0.01`` → 1% of rows are removed from the start of
        the next training segment.

    Notes
    -----
    The ``groups`` argument of :py:meth:`split` carries label end-times
    (one per row of ``X``). When supplied, training rows whose label
    horizon overlaps the test fold's time window are purged. When omitted,
    the splitter degrades gracefully to a contiguous time-ordered K-Fold
    with embargo (i.e. assumes a 1-row label horizon).
    """

    def __init__(self, n_splits: int = 5, embargo_pct: float = 0.01) -> None:
        if n_splits < 2:
            raise ValueError(f"n_splits must be >= 2, got {n_splits}")
        if embargo_pct < 0:
            raise ValueError(f"embargo_pct must be >= 0, got {embargo_pct}")
        self.n_splits = int(n_splits)
        self.embargo_pct = float(embargo_pct)

    def get_n_splits(self, X=None, y=None, groups=None) -> int:  # noqa: D401, ARG002
        """Return the configured number of splits."""
        return self.n_splits

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _times(X, groups) -> np.ndarray:
        """Return label end-time index for each sample.

        Falls back to a positional integer index when ``groups`` is missing.
        """
        if groups is not None:
            arr = np.asarray(pd.Series(groups).values)
            if len(arr) != len(X):
                raise ValueError(f"groups length {len(arr)} does not match X length {len(X)}")
            return arr
        # When no horizon information is supplied, use the row position as
        # both the start- and end-time of the label. This makes the splitter
        # behave like KFold + embargo and trivially satisfies the no-overlap
        # invariant.
        return np.arange(len(X))

    # ------------------------------------------------------------------
    def split(self, X, y=None, groups=None) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        """Yield ``(train_idx, test_idx)`` index arrays for each fold."""
        n_samples = len(X)
        if n_samples < self.n_splits + 1:
            raise ValueError(f"PurgedKFold requires n_samples (>{self.n_splits}) but got {n_samples}")

        end_times = self._times(X, groups)
        # Sort by start position (assumed equal to row order). The label
        # end-times must be monotonically non-decreasing in row order; we do
        # not re-sort to keep the index alignment stable for callers.
        positions = np.arange(n_samples)
        embargo = int(np.floor(n_samples * self.embargo_pct))

        # Build contiguous test folds in time order.
        fold_sizes = np.full(self.n_splits, n_samples // self.n_splits, dtype=int)
        fold_sizes[: n_samples % self.n_splits] += 1

        current = 0
        starts: list[int] = []
        stops: list[int] = []
        for fs in fold_sizes:
            starts.append(current)
            stops.append(current + int(fs))
            current += int(fs)

        for fold_idx in range(self.n_splits):
            test_start = starts[fold_idx]
            test_stop = stops[fold_idx]
            test_idx = positions[test_start:test_stop]

            # Test fold spans label end-times starting at t_lo. The right
            # bound is implicit in the test indices and unused below.
            t_lo = end_times[test_start]

            train_mask = np.ones(n_samples, dtype=bool)
            # Drop the test rows themselves.
            train_mask[test_start:test_stop] = False

            # Embargo: drop rows whose *position* falls in [test_stop,
            # test_stop + embargo). This protects the next training block
            # from leakage via serial dependence.
            if embargo > 0:
                emb_stop = min(test_stop + embargo, n_samples)
                train_mask[test_stop:emb_stop] = False

            # Purge training rows whose label horizon overlaps the test
            # fold's time window. A train row at position i is purged if
            # its end-time ``end_times[i]`` lies within [t_lo, t_hi].
            # We also purge rows whose *start* (i.e. position) is inside
            # the test window — already removed above. Symmetric purge:
            # any train row with end_times[i] >= t_lo while i < test_start
            # leaks future info backwards.
            for i in range(0, test_start):
                if end_times[i] >= t_lo:
                    train_mask[i] = False

            # Post-test purge: remove post-test training rows whose *position*
            # still falls within the label horizon of the test fold.  A row at
            # position p (p > test_stop) leaks backward if p ≤ max(end_times
            # for the test fold) — i.e. the test fold's labels extend into the
            # post-test training region.
            if test_start < test_stop:
                t_hi_labels = float(np.max(end_times[test_start:test_stop]))
                for i in range(test_stop, n_samples):
                    if positions[i] <= t_hi_labels:
                        train_mask[i] = False

            train_idx = positions[train_mask]
            yield train_idx, test_idx


__all__ = ["PurgedKFold"]
