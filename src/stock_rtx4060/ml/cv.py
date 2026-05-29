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
        if not (0.0 <= embargo_pct < 1.0):
            raise ValueError(f"embargo_pct must be in [0, 1), got {embargo_pct}")
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
        """Yield ``(train_idx, test_idx)`` index arrays for each fold.

        Full overlap purge (v5.1 spec §8 Phase 1):
        A train row at position ``i`` with label end-time ``ends[i]`` is
        purged if its label window ``[i, ends[i]]`` overlaps the test span
        ``[test_start, test_end]``, i.e.::

            overlap = (starts[i] <= test_end) & (ends[i] >= test_start)

        This is strictly stronger than the old heuristic (``ends[i] >= ends[test_start]``)
        and eliminates the pre-test purge lower-bound under-estimation bug.
        """
        n_samples = len(X)
        if n_samples < self.n_splits + 1:
            raise ValueError(f"PurgedKFold requires n_samples (>{self.n_splits}) but got {n_samples}")

        # Row positions (start of each bar's label window).
        positions = np.arange(n_samples)

        # Label end-times from groups; fall back to row position when absent.
        if groups is not None:
            ends = np.asarray(pd.Series(groups).values)
            if len(ends) != n_samples:
                raise ValueError(f"groups length {len(ends)} does not match X length {n_samples}")
            if np.any(ends < positions):
                raise ValueError("groups must contain label end index >= row position")
        else:
            ends = positions.copy()

        starts = positions  # label start = row position (no look-back)
        embargo = int(np.floor(n_samples * self.embargo_pct))

        # Build contiguous test folds in chronological order.
        fold_sizes = np.full(self.n_splits, n_samples // self.n_splits, dtype=int)
        fold_sizes[: n_samples % self.n_splits] += 1

        current = 0
        for fold_size in fold_sizes:
            test_start = current
            test_stop = current + int(fold_size)
            current = test_stop

            test_idx = positions[test_start:test_stop]
            # The test span's right boundary is the maximum label end-time
            # across the test fold — not merely ``test_stop - 1``.
            test_end = int(np.max(ends[test_idx]))

            train_mask = np.ones(n_samples, dtype=bool)

            # 1) Remove test rows.
            train_mask[test_start:test_stop] = False

            # 2) Full overlap purge: remove any train row whose label window
            #    [start, end] intersects the test span [test_start, test_end].
            #    This replaces the old lower-bound-only heuristic.
            overlap = (starts <= test_end) & (ends >= test_start)
            train_mask &= ~overlap

            # 3) Embargo: remove rows immediately after the test block to
            #    guard against serial auto-correlation leakage.
            if embargo > 0:
                emb_stop = min(test_stop + embargo, n_samples)
                train_mask[test_stop:emb_stop] = False

            train_idx = positions[train_mask]
            yield train_idx, test_idx


__all__ = ["PurgedKFold"]


class CombinatorialPurgedCV:
    """Combinatorial Purged Cross-Validation (CPCV) for overfitting diagnostics.

    Generates C(n_splits, n_test_splits) unique test-path combinations, each
    with full overlap purge and embargo.  Running a backtest on each path
    yields a distribution of OOS Sharpe ratios from which PBO and DSR can be
    computed.

    Reference: López de Prado, AFML §12; Bailey et al., Backtest Overfitting
    in the Machine Learning Era, SSRN 4686376.

    Parameters
    ----------
    n_splits:
        Total number of folds (``k`` in ``C(k, p)``).
    n_test_splits:
        Number of folds held out per path (``p`` in ``C(k, p)``).
        Default 2 → 15 paths for n_splits=6.
    embargo_pct:
        Same as :class:`PurgedKFold`.

    Notes
    -----
    Use :class:`PurgedKFold` for day-to-day OOF training.  Reserve
    ``CombinatorialPurgedCV`` for pre-LIVE_REVIEW_CANDIDATE diagnostics
    only — it is slower (C(k,p) backtests vs k backtests).
    """

    def __init__(
        self,
        n_splits: int = 6,
        n_test_splits: int = 2,
        embargo_pct: float = 0.01,
    ) -> None:
        if n_splits < 2:
            raise ValueError(f"n_splits must be >= 2, got {n_splits}")
        if not (1 <= n_test_splits < n_splits):
            raise ValueError(f"n_test_splits must be in [1, n_splits), got {n_test_splits}")
        if not (0.0 <= embargo_pct < 1.0):
            raise ValueError(f"embargo_pct must be in [0, 1), got {embargo_pct}")
        self.n_splits = int(n_splits)
        self.n_test_splits = int(n_test_splits)
        self.embargo_pct = float(embargo_pct)

    def get_n_splits(self, X=None, y=None, groups=None) -> int:  # noqa: ARG002
        from math import comb
        return comb(self.n_splits, self.n_test_splits)

    def split(self, X, y=None, groups=None):
        """Yield ``(train_idx, test_idx)`` for all C(n_splits, n_test_splits) paths.

        Uses the same full-overlap purge rule as :class:`PurgedKFold`.
        """
        from itertools import combinations

        n_samples = len(X)
        if n_samples < self.n_splits + 1:
            raise ValueError(
                f"CombinatorialPurgedCV requires n_samples > n_splits={self.n_splits}, got {n_samples}"
            )

        positions = np.arange(n_samples)
        if groups is not None:
            ends = np.asarray(pd.Series(groups).values)
            if len(ends) != n_samples:
                raise ValueError(f"groups length {len(ends)} != X length {n_samples}")
            if np.any(ends < positions):
                raise ValueError("groups must contain label end index >= row position")
        else:
            ends = positions.copy()

        starts = positions
        embargo = int(np.floor(n_samples * self.embargo_pct))

        # Build fold boundaries
        fold_sizes = np.full(self.n_splits, n_samples // self.n_splits, dtype=int)
        fold_sizes[: n_samples % self.n_splits] += 1
        fold_bounds: list[tuple[int, int]] = []
        cur = 0
        for fs in fold_sizes:
            fold_bounds.append((cur, cur + int(fs)))
            cur += int(fs)

        for test_fold_indices in combinations(range(self.n_splits), self.n_test_splits):
            # Collect test indices from selected folds
            test_parts = [positions[fold_bounds[fi][0]:fold_bounds[fi][1]] for fi in test_fold_indices]
            test_idx = np.concatenate(test_parts)

            test_start = int(test_idx.min())
            test_end = int(np.max(ends[test_idx]))

            train_mask = np.ones(n_samples, dtype=bool)
            # Remove test positions
            for fi in test_fold_indices:
                s, e = fold_bounds[fi]
                train_mask[s:e] = False

            # Full overlap purge
            overlap = (starts <= test_end) & (ends >= test_start)
            train_mask &= ~overlap

            # Embargo after the last test fold's end
            last_test_stop = fold_bounds[max(test_fold_indices)][1]
            if embargo > 0:
                emb_stop = min(last_test_stop + embargo, n_samples)
                train_mask[last_test_stop:emb_stop] = False

            yield positions[train_mask], test_idx


__all__ = ["PurgedKFold", "CombinatorialPurgedCV"]
