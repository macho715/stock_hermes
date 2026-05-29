"""Tests for PurgedKFold splitter (López de Prado AFML §7)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_rtx4060.ml.cv import PurgedKFold


@pytest.fixture
def synthetic_X() -> pd.DataFrame:
    np.random.seed(42)
    return pd.DataFrame(np.random.randn(500, 5), columns=[f"f{i}" for i in range(5)])


def test_get_n_splits_returns_5(synthetic_X):
    splitter = PurgedKFold(n_splits=5, embargo_pct=0.02)
    assert splitter.get_n_splits() == 5
    assert splitter.get_n_splits(synthetic_X) == 5


def test_no_train_test_overlap(synthetic_X):
    splitter = PurgedKFold(n_splits=5, embargo_pct=0.02)
    for train_idx, test_idx in splitter.split(synthetic_X):
        assert len(np.intersect1d(train_idx, test_idx)) == 0
        assert len(test_idx) > 0
        assert len(train_idx) > 0


def test_embargo_gap_size(synthetic_X):
    """After every test fold, ``embargo_pct * len(X)`` rows must be excluded
    from the start of the subsequent training segment."""
    n = len(synthetic_X)
    embargo_pct = 0.02
    expected_embargo = int(np.floor(n * embargo_pct))
    splitter = PurgedKFold(n_splits=5, embargo_pct=embargo_pct)

    folds = list(splitter.split(synthetic_X))
    for fold_i, (train_idx, test_idx) in enumerate(folds):
        test_stop = int(test_idx.max()) + 1
        if test_stop >= n:
            continue  # last fold has no embargo to verify
        forbidden_zone = set(range(test_stop, min(test_stop + expected_embargo, n)))
        assert forbidden_zone.isdisjoint(
            train_idx.tolist()
        ), f"fold {fold_i}: embargo zone {forbidden_zone} leaked into training"


def test_n_splits_validation():
    with pytest.raises(ValueError, match="n_splits"):
        PurgedKFold(n_splits=1)


def test_negative_embargo_rejected():
    with pytest.raises(ValueError, match="embargo"):
        PurgedKFold(n_splits=5, embargo_pct=-0.1)


def test_groups_purges_overlapping_horizons():
    """Train rows whose label end-time falls inside the test window must be purged."""
    n = 100
    X = pd.DataFrame(np.random.randn(n, 3))
    # Label horizon = 5 rows: end_times[i] = i + 5
    end_times = np.arange(n) + 5
    splitter = PurgedKFold(n_splits=5, embargo_pct=0.0)
    for train_idx, test_idx in splitter.split(X, groups=end_times):
        if len(test_idx) == 0 or len(train_idx) == 0:
            continue
        t_lo = end_times[test_idx.min()]
        # Verify no train row before the test fold has end_time intruding on the test window.
        before_train = train_idx[train_idx < test_idx.min()]
        for i in before_train:
            assert end_times[i] < t_lo


def test_split_returns_n_folds(synthetic_X):
    splitter = PurgedKFold(n_splits=5, embargo_pct=0.01)
    folds = list(splitter.split(synthetic_X))
    assert len(folds) == 5


def test_split_too_few_samples_raises():
    splitter = PurgedKFold(n_splits=5)
    X = pd.DataFrame(np.zeros((3, 2)))
    with pytest.raises(ValueError):
        list(splitter.split(X))


def test_groups_length_mismatch():
    splitter = PurgedKFold(n_splits=3)
    X = pd.DataFrame(np.zeros((10, 2)))
    with pytest.raises(ValueError, match="groups length"):
        list(splitter.split(X, groups=np.arange(5)))


# ---------------------------------------------------------------------------
# P0 no-leakage property tests (v5.1 spec §8 Phase 1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("horizon", [0, 1, 5, 15])
@pytest.mark.parametrize("seed", range(5))
def test_no_label_window_overlaps_test_span(horizon: int, seed: int) -> None:
    """No train row's label window [i, groups[i]] may overlap [test_start, test_end].

    This is the full no-leakage property: overlap = (start <= test_end) & (end >= test_start).
    Parametrised over 4 horizons × 5 seeds = 20 cases.
    """
    rng = np.random.default_rng(seed)
    n = 200
    X = pd.DataFrame(rng.standard_normal((n, 4)))
    groups = np.arange(n) + horizon  # fixed horizon: end_times[i] = i + horizon

    cv = PurgedKFold(n_splits=6, embargo_pct=0.02)

    for train_idx, test_idx in cv.split(X, groups=groups):
        if len(test_idx) == 0 or len(train_idx) == 0:
            continue
        test_start = int(test_idx.min())
        test_end = int(groups[test_idx].max())

        train_starts = train_idx
        train_ends = groups[train_idx]

        overlaps = (train_starts <= test_end) & (train_ends >= test_start)
        assert not overlaps.any(), (
            f"horizon={horizon} seed={seed}: "
            f"{overlaps.sum()} train rows have label windows overlapping "
            f"test span [{test_start}, {test_end}]"
        )


def test_embargo_pct_gte_one_rejected() -> None:
    """embargo_pct >= 1.0 must raise ValueError (v5.1 spec §2 CV-02)."""
    with pytest.raises(ValueError, match="embargo_pct"):
        PurgedKFold(n_splits=5, embargo_pct=1.0)


def test_embargo_pct_exactly_one_rejected() -> None:
    with pytest.raises(ValueError, match="embargo_pct"):
        PurgedKFold(n_splits=5, embargo_pct=1.001)


def test_groups_ends_before_start_rejected() -> None:
    """groups values < row position must be rejected (end cannot precede start)."""
    splitter = PurgedKFold(n_splits=3)
    X = pd.DataFrame(np.zeros((30, 2)))
    bad_groups = np.arange(30) - 5  # end_times[i] = i - 5 < i → invalid
    with pytest.raises(ValueError, match="groups must contain label end index"):
        list(splitter.split(X, groups=bad_groups))
