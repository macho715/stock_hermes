"""Extra coverage for kevpe_adapter.py — targets 43% → ≥80%."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Fake KEVPE module fixture
# ---------------------------------------------------------------------------

@dataclass
class _FakeSignal:
    regime: str = "GREEN"
    risk_score: float = 0.3
    score: float = 0.3
    expected_return: float = 2.5
    ci_low: float = 0.5
    ci_high: float = 4.5
    reason: str = "fake signal"


@dataclass
class _FakeConfig:
    red_threshold: float = 0.7
    amber_threshold: float = 0.4
    z_window: int = 20
    __dataclass_fields__: Any = field(default_factory=dict)

    def __post_init__(self):
        import dataclasses
        self.__dataclass_fields__ = {f.name: f for f in dataclasses.fields(self) if f.name != "__dataclass_fields__"}


@dataclass
class _FakeEvent:
    date: Any
    headline: str
    country: str = ""
    tone: float = 0.0
    volume: float = 1.0
    source_diversity: float = 1.0
    topics: tuple = ()


class _FakeFeatureScaler:
    def fit(self, features):
        return self

    def transform(self, features):
        return features


def _make_fake_kevpe_module():
    """Build a SimpleNamespace that mimics the KEVPE_v2 module interface."""

    def validate_ohlcv(df):
        return df

    def detect_volatility_windows(ohlcv, cfg):
        return []

    def match_events_to_windows(windows, events, cfg):
        return []

    def event_relevance_score(event):
        return 0.3

    def feature_vector_from_event(event, **kwargs):
        return [0.1, 0.2, 0.3]

    def current_signal_v2(**kwargs):
        return _FakeSignal()

    return SimpleNamespace(
        KevpeConfig=_FakeConfig,
        Event=_FakeEvent,
        FeatureScaler=_FakeFeatureScaler,
        validate_ohlcv=validate_ohlcv,
        detect_volatility_windows=detect_volatility_windows,
        match_events_to_windows=match_events_to_windows,
        event_relevance_score=event_relevance_score,
        feature_vector_from_event=feature_vector_from_event,
        current_signal_v2=current_signal_v2,
    )


@pytest.fixture(autouse=True)
def reset_singleton(monkeypatch):
    """Reset the global singleton between tests."""
    import stock_rtx4060.kevpe_adapter as ka
    monkeypatch.setattr(ka, "_kevpe_adapter_instance", None)


@pytest.fixture
def fake_kevpe():
    return _make_fake_kevpe_module()


def _make_ohlcv(n: int = 60) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(np.random.randn(n) * 0.3)
    return pd.DataFrame(
        {
            "date": dates,
            "open": close * 0.99,
            "high": close * 1.01,
            "low": close * 0.98,
            "close": close,
            "volume": np.random.randint(100_000, 500_000, n).astype(float),
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# KevpeAdapterResult
# ---------------------------------------------------------------------------

def test_result_fields():
    from stock_rtx4060.kevpe_adapter import KevpeAdapterResult

    r = KevpeAdapterResult(
        regime="GREEN",
        score=0.3,
        expected_return_pct=2.5,
        ci_low_pct=1.0,
        ci_high_pct=4.0,
        reason="test",
        confidence="medium",
        is_available=True,
    )
    assert r.regime == "GREEN"
    assert r.is_available is True


def test_result_unavailable_default():
    from stock_rtx4060.kevpe_adapter import KevpeAdapterResult

    r = KevpeAdapterResult.unavailable()
    assert r.is_available is False
    assert r.regime == "AMBER"
    assert "KEVPE" in r.reason


def test_result_unavailable_custom_reason():
    from stock_rtx4060.kevpe_adapter import KevpeAdapterResult

    r = KevpeAdapterResult.unavailable("custom reason")
    assert r.reason == "custom reason"
    assert r.score == 0.5


# ---------------------------------------------------------------------------
# KevpeAdapter.__init__ and _infer_kevpe_path
# ---------------------------------------------------------------------------

def test_adapter_init_no_path():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    assert adapter._kevpe_pkg_path == "" or isinstance(adapter._kevpe_pkg_path, str)
    assert adapter._initialized is False


def test_adapter_init_explicit_path():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/some/path")
    assert adapter._kevpe_pkg_path == "/some/path"


def test_infer_kevpe_path_not_found(monkeypatch, tmp_path):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter
    import stock_rtx4060.kevpe_adapter as _mod

    # Point the module's __file__ to a temp dir that won't contain KEVPE_final_package
    monkeypatch.setattr(_mod, "__file__", str(tmp_path / "kevpe_adapter.py"))
    adapter = KevpeAdapter.__new__(KevpeAdapter)
    result = adapter._infer_kevpe_path()
    assert result == ""


# ---------------------------------------------------------------------------
# _ensure_init paths
# ---------------------------------------------------------------------------

def test_ensure_init_already_initialized():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    adapter._initialized = True
    adapter._kevpe_module = None
    assert adapter._ensure_init() is False
    # calling again returns same result (no double init)
    assert adapter._ensure_init() is False


def test_ensure_init_empty_path(monkeypatch):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    # Prevent _infer_kevpe_path from finding the real KEVPE package
    monkeypatch.setattr(KevpeAdapter, "_infer_kevpe_path", lambda self: "")
    adapter = KevpeAdapter(kevpe_package_path="")
    result = adapter._ensure_init()
    assert result is False
    assert adapter._initialized is True


def test_ensure_init_nonexistent_path():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/definitely/does/not/exist/12345")
    result = adapter._ensure_init()
    assert result is False


def test_ensure_init_spec_none(tmp_path, monkeypatch):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    (tmp_path / "kevpe_v2.py").write_text("# stub")
    import importlib.util

    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **kw: None)
    adapter = KevpeAdapter(kevpe_package_path=str(tmp_path))
    result = adapter._ensure_init()
    assert result is False


def test_ensure_init_exec_module_raises(tmp_path, monkeypatch):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter
    import importlib.util

    (tmp_path / "kevpe_v2.py").write_text("raise RuntimeError('bad module')")
    adapter = KevpeAdapter(kevpe_package_path=str(tmp_path))
    result = adapter._ensure_init()
    assert result is False
    assert adapter._kevpe_module is None


def test_ensure_init_success_via_direct_inject(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe
    assert adapter._ensure_init() is True


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

def test_is_available_no_kevpe():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/nonexistent/fake/abc/xyz")
    assert adapter.is_available() is False


def test_is_available_with_module(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe
    assert adapter.is_available() is True


# ---------------------------------------------------------------------------
# get_default_config
# ---------------------------------------------------------------------------

def test_get_default_config_unavailable():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/nonexistent/fake/abc/xyz")
    result = adapter.get_default_config()
    assert result is None


def test_get_default_config_available(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe
    cfg = adapter.get_default_config()
    assert isinstance(cfg, _FakeConfig)


def test_get_default_config_with_overrides(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected", default_config_kwargs={})
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe
    cfg = adapter.get_default_config()
    assert cfg is not None


# ---------------------------------------------------------------------------
# get_signal_for_ticker — unavailable paths
# ---------------------------------------------------------------------------

def test_get_signal_unavailable_no_kevpe():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(60)
    result = adapter.get_signal_for_ticker(ohlcv, events=[])
    assert result.is_available is False


def test_get_signal_ohlcv_too_short(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(10)
    result = adapter.get_signal_for_ticker(ohlcv, events=[])
    assert result.is_available is False
    assert "Insufficient" in result.reason


def test_get_signal_exception_returns_unavailable(fake_kevpe, monkeypatch):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    monkeypatch.setattr(adapter, "get_default_config", lambda: (_ for _ in ()).throw(RuntimeError("cfg crash")))
    ohlcv = _make_ohlcv(70)
    result = adapter.get_signal_for_ticker(ohlcv, events=[])
    assert result.is_available is False


def test_get_signal_with_events_few(fake_kevpe):
    """<3 historical events → score-only path."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(80)
    events = [
        _FakeEvent(date=pd.Timestamp("2023-01-10"), headline="Event A"),
        _FakeEvent(date=pd.Timestamp("2023-01-20"), headline="Event B"),
    ]
    result = adapter.get_signal_for_ticker(ohlcv, events=events)
    assert result.is_available is True
    assert result.regime in {"GREEN", "AMBER", "RED"}


def test_get_signal_with_events_many(fake_kevpe):
    """≥3 historical events → full signal path via current_signal_v2."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(90)
    events = [_FakeEvent(date=pd.Timestamp("2023-01-10"), headline=f"Event {i}") for i in range(5)]
    result = adapter.get_signal_for_ticker(ohlcv, events=events)
    assert result.is_available is True
    assert result.regime == "GREEN"


# ---------------------------------------------------------------------------
# _normalize_ohlcv_for_kevpe
# ---------------------------------------------------------------------------

def test_normalize_ohlcv_standard(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(30)
    result = adapter._normalize_ohlcv_for_kevpe(ohlcv)
    assert result is not None
    assert "close" in result.columns or "Close" in result.columns


def test_normalize_ohlcv_uppercase_columns(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    dates = pd.date_range("2023-01-01", periods=30, freq="B")
    df = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.5, "Volume": 1000.0}, index=dates)
    result = adapter._normalize_ohlcv_for_kevpe(df)
    assert result is not None


# ---------------------------------------------------------------------------
# _normalize_events
# ---------------------------------------------------------------------------

def test_normalize_events_empty(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._kevpe_module = fake_kevpe
    result = adapter._normalize_events([], fake_kevpe)
    assert result == []


def test_normalize_events_dict_events(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._kevpe_module = fake_kevpe
    events = [
        {"date": "2023-01-10", "headline": "Test headline A", "tone": -0.2, "topics": "macro,fed"},
        {"date": "2023-01-15", "headline": "Test headline B"},
    ]
    result = adapter._normalize_events(events, fake_kevpe)
    assert len(result) == 2
    assert all(isinstance(e, _FakeEvent) for e in result)


def test_normalize_events_native_event_instances(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._kevpe_module = fake_kevpe
    e1 = _FakeEvent(date=pd.Timestamp("2023-01-10"), headline="Native Event")
    result = adapter._normalize_events([e1], fake_kevpe)
    assert len(result) == 1
    assert result[0] is e1


def test_normalize_events_bad_dict_skipped(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._kevpe_module = fake_kevpe
    events = [
        "not a dict or event",
        {"headline": ""},  # empty headline
        {"date": "2023-01-10", "headline": "Good one"},
    ]
    result = adapter._normalize_events(events, fake_kevpe)
    assert len(result) == 1
    assert result[0].headline == "Good one"


def test_normalize_events_topics_list(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._kevpe_module = fake_kevpe
    events = [{"date": "2023-01-10", "headline": "X", "topics": ["macro", "fed"]}]
    result = adapter._normalize_events(events, fake_kevpe)
    assert result[0].topics == ("macro", "fed")


# ---------------------------------------------------------------------------
# _signal_from_events paths
# ---------------------------------------------------------------------------

def test_signal_from_events_few_historical(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(40)
    cfg = _FakeConfig()
    events = [
        _FakeEvent(date=pd.Timestamp("2023-01-10"), headline="E1"),
        _FakeEvent(date=pd.Timestamp("2023-01-15"), headline="E2"),
    ]
    result = adapter._signal_from_events(events, ohlcv, cfg, fake_kevpe, None)
    assert result.is_available is True
    assert result.confidence == "low"


def test_signal_from_events_many_historical(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(80)
    cfg = _FakeConfig()
    events = [_FakeEvent(date=pd.Timestamp(f"2023-01-{10+i:02d}"), headline=f"E{i}") for i in range(5)]
    result = adapter._signal_from_events(events, ohlcv, cfg, fake_kevpe, None)
    assert result.is_available is True
    assert result.regime == "GREEN"


# ---------------------------------------------------------------------------
# _result_from_signal — confidence tiers
# ---------------------------------------------------------------------------

def test_result_from_signal_low_confidence(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    signal = _FakeSignal(ci_low=0.0, ci_high=6.0)
    result = adapter._result_from_signal(signal)
    assert result.confidence == "low"


def test_result_from_signal_medium_confidence(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    signal = _FakeSignal(ci_low=0.0, ci_high=3.0)
    result = adapter._result_from_signal(signal)
    assert result.confidence == "medium"


def test_result_from_signal_high_confidence(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    signal = _FakeSignal(ci_low=0.0, ci_high=1.5)
    result = adapter._result_from_signal(signal)
    assert result.confidence == "high"


# ---------------------------------------------------------------------------
# _recent_return
# ---------------------------------------------------------------------------

def test_recent_return_short_data():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(10)
    assert adapter._recent_return(ohlcv) == 0.0


def test_recent_return_normal():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(30)
    result = adapter._recent_return(ohlcv)
    assert isinstance(result, float)


# ---------------------------------------------------------------------------
# _recent_vol_z
# ---------------------------------------------------------------------------

def test_recent_vol_z_short_data():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(5)
    cfg = _FakeConfig(z_window=20)
    assert adapter._recent_vol_z(ohlcv, cfg) == 0.0


def test_recent_vol_z_normal():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(60)
    cfg = _FakeConfig(z_window=20)
    result = adapter._recent_vol_z(ohlcv, cfg)
    assert isinstance(result, float)


def test_recent_vol_z_zero_std():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    dates = pd.date_range("2023-01-01", periods=30, freq="B")
    ohlcv = pd.DataFrame({"close": [100.0] * 30}, index=dates)
    cfg = _FakeConfig(z_window=20)
    assert adapter._recent_vol_z(ohlcv, cfg) == 0.0


# ---------------------------------------------------------------------------
# _forward_return_after_event
# ---------------------------------------------------------------------------

def test_forward_return_no_matching_date():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(30)  # dates start 2023-01-01, last ~2023-02-10
    # Use a future date so no ohlcv row satisfies date >= event_date
    event = _FakeEvent(date=pd.Timestamp("2030-01-01"), headline="future")
    result = adapter._forward_return_after_event(ohlcv, event)
    assert result == 0.0


def test_forward_return_normal():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(60)
    event = _FakeEvent(date=ohlcv["date"].iloc[10], headline="mid event")
    result = adapter._forward_return_after_event(ohlcv, event)
    assert isinstance(result, float)


# ---------------------------------------------------------------------------
# _merge_config
# ---------------------------------------------------------------------------

def test_merge_config(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    cfg = _FakeConfig(red_threshold=0.7, amber_threshold=0.4)
    result = adapter._merge_config(cfg, {"red_threshold": 0.8})
    assert result.red_threshold == 0.8
    assert result.amber_threshold == 0.4


# ---------------------------------------------------------------------------
# get_kevpe_adapter — singleton
# ---------------------------------------------------------------------------

def test_get_kevpe_adapter_singleton():
    from stock_rtx4060.kevpe_adapter import get_kevpe_adapter

    a1 = get_kevpe_adapter()
    a2 = get_kevpe_adapter()
    assert a1 is a2


def test_get_kevpe_adapter_returns_instance():
    from stock_rtx4060.kevpe_adapter import get_kevpe_adapter, KevpeAdapter

    adapter = get_kevpe_adapter()
    assert isinstance(adapter, KevpeAdapter)


# ---------------------------------------------------------------------------
# kevpe_signal_to_supplement
# ---------------------------------------------------------------------------

def test_supplement_unavailable():
    from stock_rtx4060.kevpe_adapter import KevpeAdapterResult, kevpe_signal_to_supplement

    r = KevpeAdapterResult.unavailable()
    result = kevpe_signal_to_supplement(r)
    assert result == {"kevpe_available": False}


def test_supplement_available():
    from stock_rtx4060.kevpe_adapter import KevpeAdapterResult, kevpe_signal_to_supplement

    r = KevpeAdapterResult(
        regime="GREEN",
        score=0.3,
        expected_return_pct=2.5,
        ci_low_pct=1.0,
        ci_high_pct=4.0,
        reason="test",
        confidence="medium",
        is_available=True,
    )
    result = kevpe_signal_to_supplement(r)
    assert result["kevpe_available"] is True
    assert result["kevpe_regime"] == "GREEN"
    assert result["kevpe_score"] == 0.3
    assert "kevpe_ci" in result
    assert isinstance(result["kevpe_ci"], list)


# ---------------------------------------------------------------------------
# _normalize_ohlcv_for_kevpe — MultiIndex and capital-Date paths
# ---------------------------------------------------------------------------

def test_normalize_ohlcv_multiindex_columns(fake_kevpe):
    """Lines 252: MultiIndex columns are flattened to first level."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(30)
    # Build a MultiIndex column frame (like yfinance raw output sometimes)
    cols = pd.MultiIndex.from_tuples(
        [("open", "AAPL"), ("high", "AAPL"), ("low", "AAPL"), ("close", "AAPL"), ("volume", "AAPL"), ("date", "AAPL")]
    )
    df_multi = ohlcv.copy()
    df_multi.columns = cols
    result = adapter._normalize_ohlcv_for_kevpe(df_multi)
    # After normalization columns should be simple strings
    assert all(isinstance(c, str) for c in result.columns)


def test_normalize_ohlcv_capital_date_column(fake_kevpe):
    """Lines 256-257: 'Date' (capital) column sets DatetimeIndex."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(30).copy()
    ohlcv = ohlcv.rename(columns={"date": "Date"})
    ohlcv = ohlcv.reset_index(drop=True)  # Remove DatetimeIndex so the Date column path activates
    result = adapter._normalize_ohlcv_for_kevpe(ohlcv)
    assert isinstance(result.index, pd.DatetimeIndex) or "date" in result.columns


# ---------------------------------------------------------------------------
# _normalize_events — integer topics path (line 281)
# ---------------------------------------------------------------------------

def test_normalize_events_int_topics(fake_kevpe):
    """Topics that are neither list/str/tuple → treated as () (line 281)."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    event_dict = {
        "headline": "test event",
        "date": "2023-06-01",
        "topics": 42,  # integer — not list, str, or tuple
    }
    result = adapter._normalize_events([event_dict], fake_kevpe)
    assert len(result) == 1
    assert result[0].topics == ()


# ---------------------------------------------------------------------------
# _signal_from_events — RED and AMBER branches (lines 313-316)
# ---------------------------------------------------------------------------

def _make_fake_kevpe_high_score(score: float):
    """Build fake_kevpe module with a fixed event_relevance_score."""
    from types import SimpleNamespace

    def validate_ohlcv(df):
        return df

    def detect_volatility_windows(ohlcv, cfg):
        return []

    def match_events_to_windows(windows, events, cfg):
        return []

    def event_relevance_score(event):
        return score

    def feature_vector_from_event(event, **kwargs):
        return [0.1, 0.2, 0.3]

    def current_signal_v2(**kwargs):
        return _FakeSignal()

    return SimpleNamespace(
        KevpeConfig=_FakeConfig,
        Event=_FakeEvent,
        FeatureScaler=_FakeFeatureScaler,
        validate_ohlcv=validate_ohlcv,
        detect_volatility_windows=detect_volatility_windows,
        match_events_to_windows=match_events_to_windows,
        event_relevance_score=event_relevance_score,
        feature_vector_from_event=feature_vector_from_event,
        current_signal_v2=current_signal_v2,
    )


def test_signal_from_events_red_branch():
    """Score >= red_threshold (0.7) → regime='RED' (line 314)."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    fake_kv = _make_fake_kevpe_high_score(0.8)  # >= 0.7 → RED
    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(60)
    cfg = _FakeConfig()
    # Only 2 events so historical_events < 3 → score-only path
    events = [
        _FakeEvent(date=ohlcv["date"].iloc[10], headline="e1"),
        _FakeEvent(date=ohlcv["date"].iloc[20], headline="e2"),
    ]
    result = adapter._signal_from_events(events, ohlcv, cfg, fake_kv, None)
    assert result.regime == "RED"
    assert result.is_available is True


def test_signal_from_events_amber_branch():
    """Score >= amber_threshold (0.4) but < red_threshold (0.7) → regime='AMBER' (line 316)."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    fake_kv = _make_fake_kevpe_high_score(0.5)  # 0.4 <= 0.5 < 0.7 → AMBER
    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(60)
    cfg = _FakeConfig()
    events = [
        _FakeEvent(date=ohlcv["date"].iloc[10], headline="e1"),
        _FakeEvent(date=ohlcv["date"].iloc[20], headline="e2"),
    ]
    result = adapter._signal_from_events(events, ohlcv, cfg, fake_kv, None)
    assert result.regime == "AMBER"


# ---------------------------------------------------------------------------
# _forward_return_after_event — end <= start path (line 369)
# ---------------------------------------------------------------------------

def test_forward_return_end_le_start():
    """Single-row ohlcv after event: end == start → returns 0.0 (line 369)."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    # One-row ohlcv — start=0, end=min(0+20, 0)=0 → end <= start → 0.0
    single_date = pd.Timestamp("2023-06-15")
    ohlcv = pd.DataFrame({
        "date": [single_date],
        "open": [100.0],
        "high": [101.0],
        "low": [99.0],
        "close": [100.5],
        "volume": [50000.0],
    })
    event = _FakeEvent(date=single_date, headline="single")
    result = adapter._forward_return_after_event(ohlcv, event)
    assert result == 0.0


# ---------------------------------------------------------------------------
# _extract_feature_from_windows (lines 382-392)
# ---------------------------------------------------------------------------

def _make_fake_window(start_idx, end_idx):
    from types import SimpleNamespace
    return SimpleNamespace(start=start_idx, end=end_idx)


def _make_fake_kevpe_for_windows():
    """Like _make_fake_kevpe_module but feature_vector_from_event accepts cfg positional arg."""
    from types import SimpleNamespace

    def validate_ohlcv(df):
        return df

    def feature_vector_from_event(event_or_ohlcv, cfg=None, **kwargs):
        return [0.1, 0.2, 0.3]

    def current_signal_v2(**kwargs):
        return _FakeSignal()

    return SimpleNamespace(
        KevpeConfig=_FakeConfig,
        Event=_FakeEvent,
        FeatureScaler=_FakeFeatureScaler,
        validate_ohlcv=validate_ohlcv,
        feature_vector_from_event=feature_vector_from_event,
        current_signal_v2=current_signal_v2,
    )


def test_extract_feature_from_windows_success():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = _make_fake_kevpe_for_windows()

    ohlcv = _make_ohlcv(40)
    window = _make_fake_window(ohlcv.index[5], ohlcv.index[20])
    cfg = _FakeConfig()
    result = adapter._extract_feature_from_windows(ohlcv, window, cfg)
    assert result is not None


def test_extract_feature_from_windows_none_window(fake_kevpe):
    """window=None → returns None (line 383)."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(20)
    cfg = _FakeConfig()
    result = adapter._extract_feature_from_windows(ohlcv, None, cfg)
    assert result is None


def test_extract_feature_from_windows_exception(fake_kevpe, monkeypatch):
    """feature_vector_from_event raises → returns None (line 392)."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter
    from types import SimpleNamespace

    def bad_fvfe(*a, **kw):
        raise ValueError("feature error")

    fk = _make_fake_kevpe_high_score(0.3)
    fk.feature_vector_from_event = bad_fvfe

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fk

    ohlcv = _make_ohlcv(40)
    window = _make_fake_window(ohlcv.index[5], ohlcv.index[20])
    cfg = _FakeConfig()
    result = adapter._extract_feature_from_windows(ohlcv, window, cfg)
    assert result is None


# ---------------------------------------------------------------------------
# _build_historical_features (lines 396-407)
# ---------------------------------------------------------------------------

def test_build_historical_features_success():
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = _make_fake_kevpe_for_windows()

    ohlcv = _make_ohlcv(60)
    windows = [
        _make_fake_window(ohlcv.index[0], ohlcv.index[10]),
        _make_fake_window(ohlcv.index[10], ohlcv.index[20]),
        _make_fake_window(ohlcv.index[20], ohlcv.index[30]),
    ]
    cfg = _FakeConfig()
    result = adapter._build_historical_features(ohlcv, windows, cfg)
    # windows[:-1] = first 2 windows
    assert isinstance(result, list)
    assert len(result) == 2


def test_build_historical_features_empty_windows():
    """Single-window list → windows[:-1] is empty → returns []."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = _make_fake_kevpe_for_windows()

    ohlcv = _make_ohlcv(30)
    windows = [_make_fake_window(ohlcv.index[0], ohlcv.index[10])]
    cfg = _FakeConfig()
    result = adapter._build_historical_features(ohlcv, windows, cfg)
    assert result == []


# ---------------------------------------------------------------------------
# _build_historical_forward_returns (lines 411-420)
# ---------------------------------------------------------------------------

def test_build_historical_forward_returns_success(fake_kevpe):
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter(kevpe_package_path="/injected")
    adapter._initialized = True
    adapter._kevpe_module = fake_kevpe

    ohlcv = _make_ohlcv(60)
    windows = [
        _make_fake_window(ohlcv.index[0], ohlcv.index[10]),
        _make_fake_window(ohlcv.index[10], ohlcv.index[20]),
        _make_fake_window(ohlcv.index[20], ohlcv.index[30]),
    ]
    result = adapter._build_historical_forward_returns(ohlcv, windows)
    # windows[:-1] has 2 items → 2 returns
    assert isinstance(result, list)
    assert len(result) == 2


def test_build_historical_forward_returns_single_window():
    """Single window → windows[:-1] is empty → returns [0.0]."""
    from stock_rtx4060.kevpe_adapter import KevpeAdapter

    adapter = KevpeAdapter()
    ohlcv = _make_ohlcv(30)
    windows = [_make_fake_window(ohlcv.index[0], ohlcv.index[10])]
    result = adapter._build_historical_forward_returns(ohlcv, windows)
    assert result == [0.0]
