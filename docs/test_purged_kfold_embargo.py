"""Tests for PurgedKFoldEmbargo: API, edges, and the core no-leakage property."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from purged_kfold_embargo import PurgedKFoldEmbargo, make_label_endtimes


def _t1(n: int, horizon_bars: int, seed: int = 0) -> pd.Series:
    """n daily samples, each labelled over `horizon_bars` calendar days."""
    start = pd.date_range("2020-01-01", periods=n, freq="D")
    end = start + pd.Timedelta(days=horizon_bars)
    return pd.Series(end, index=start)


# ─────────────────────────────────────────────────────────── happy path ──
def test_partition_is_exhaustive_and_disjoint():
    t1 = _t1(100, horizon_bars=5)
    cv = PurgedKFoldEmbargo(t1, n_splits=5, embargo_pct=0.0)
    test_sets = [test for _, test in cv.split()]
    assert len(test_sets) == 5
    all_test = np.concatenate(test_sets)
    # every index appears in exactly one test fold
    assert sorted(all_test.tolist()) == list(range(100))
    for i in range(len(test_sets)):
        for j in range(i + 1, len(test_sets)):
            assert set(test_sets[i]).isdisjoint(set(test_sets[j]))


def test_make_label_endtimes_helper():
    start = pd.date_range("2021-06-01", periods=10, freq="D")
    t1 = make_label_endtimes(start, pd.Timedelta(days=3))
    assert (t1.to_numpy() == (start + pd.Timedelta(days=3)).to_numpy()).all()
    assert t1.index.equals(start)


# ─────────────────────────────────────────────────────── edge cases ──
def test_minimal_two_folds_no_embargo():
    t1 = _t1(6, horizon_bars=0)  # zero horizon => purge removes nothing extra
    cv = PurgedKFoldEmbargo(t1, n_splits=2, embargo_pct=0.0)
    folds = list(cv.split())
    assert len(folds) == 2
    for train, test in folds:
        assert set(train).isdisjoint(set(test))
        assert len(test) == 3


def test_invalid_inputs_raise():
    t1 = _t1(20, horizon_bars=2)
    with pytest.raises(ValueError):
        PurgedKFoldEmbargo(t1, n_splits=1)            # too few folds
    with pytest.raises(ValueError):
        PurgedKFoldEmbargo(t1, n_splits=5, embargo_pct=1.0)  # bad embargo
    # unsorted start times
    bad = pd.Series(t1.to_numpy(), index=t1.index[::-1])
    with pytest.raises(ValueError):
        PurgedKFoldEmbargo(bad, n_splits=3)
    # negative horizon (label end before start)
    neg = pd.Series(t1.index - pd.Timedelta(days=1), index=t1.index)
    with pytest.raises(ValueError):
        PurgedKFoldEmbargo(neg, n_splits=3)
    with pytest.raises(TypeError):
        PurgedKFoldEmbargo([1, 2, 3], n_splits=2)     # not a Series


def test_X_length_mismatch_raises():
    t1 = _t1(30, horizon_bars=1)
    cv = PurgedKFoldEmbargo(t1, n_splits=3)
    with pytest.raises(ValueError):
        next(cv.split(X=np.zeros((10, 4))))


# ───────────────────────────────────────────── core leakage property ──
@pytest.mark.parametrize("horizon", [0, 1, 5, 15])
@pytest.mark.parametrize("seed", range(5))
def test_no_label_window_overlaps_test_span(horizon, seed):
    """Property: for every fold, no surviving TRAIN sample's label window
    [start, end] may overlap the test fold's span [t_start, t_end]."""
    rng = np.random.default_rng(seed)
    n = 200
    start = pd.to_datetime("2019-01-01") + pd.to_timedelta(
        np.sort(rng.integers(0, 1000, size=n)), unit="D"
    )
    # variable horizon per sample to stress the overlap logic
    extra = rng.integers(0, horizon + 1, size=n)
    end = start + pd.to_timedelta(extra, unit="D")
    t1 = pd.Series(end.values, index=pd.DatetimeIndex(start))

    cv = PurgedKFoldEmbargo(t1, n_splits=6, embargo_pct=0.02)
    starts = t1.index.to_numpy()
    ends = t1.to_numpy()

    for train, test in cv.split():
        t_start = starts[test].min()
        t_end = ends[test].max()
        # purge invariant: train windows are disjoint from [t_start, t_end]
        tr_start, tr_end = starts[train], ends[train]
        overlaps = (tr_start <= t_end) & (tr_end >= t_start)
        assert not overlaps.any(), "leakage: a train window overlaps the test span"
        assert set(train).isdisjoint(set(test))


def test_embargo_drops_following_samples():
    t1 = _t1(100, horizon_bars=0)  # no purge from horizon; isolate embargo effect
    embargo_pct = 0.05             # => 5 samples
    cv = PurgedKFoldEmbargo(t1, n_splits=5, embargo_pct=embargo_pct)
    folds = list(cv.split())
    # first fold: test = 0..19, embargo removes 20..24 from train
    train0, test0 = folds[0]
    assert 19 == test0[-1]
    for k in range(20, 25):
        assert k not in set(train0)
    assert 25 in set(train0)  # just past the embargo window is allowed


def test_deterministic():
    t1 = _t1(80, horizon_bars=3)
    a = [(*map(tuple, (tr, te)),) for tr, te in PurgedKFoldEmbargo(t1, 4, 0.01).split()]
    b = [(*map(tuple, (tr, te)),) for tr, te in PurgedKFoldEmbargo(t1, 4, 0.01).split()]
    assert a == b
