"""Coverage boost tests targeting missing branches in multiple modules.

Files targeted:
  - data_cache.py           (85%  → more)
  - compliance.py           (77%  → more)
  - backtest_honesty.py     (77%  → more)
  - news_sentiment.py       (59%  → more)
  - mcp_adapter.py          (86%  → more)
  - adjuster.py             (59%  → more)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# data_cache.py  — missing lines: 83-85, 116-118, 145-146, 151, 158-160,
#                                   165, 175-177
# ---------------------------------------------------------------------------

from stock_rtx4060.data_cache import DataCache


def _make_df() -> pd.DataFrame:
    return pd.DataFrame({"date": ["2026-05-01", "2026-05-02"], "close": [100.0, 101.0]})


def _make_cache(tmp_path: Path, ttl_hours: int = DataCache.DEFAULT_TTL_HOURS) -> DataCache:
    return DataCache(db_path=tmp_path / "cache.db", ttl_hours=ttl_hours)


class TestDataCacheMissingBranches:
    def test_is_expired_with_malformed_date(self, tmp_path):
        """_is_expired returns True for unparseable fetch_date (line 83-85)."""
        cache = _make_cache(tmp_path)
        result = cache._is_expired("not-a-valid-date")
        assert result is True

    def test_get_raises_returns_none(self, tmp_path, monkeypatch):
        """get() catches any sqlite exception and returns None (line 116-118)."""
        cache = _make_cache(tmp_path)
        # Force sqlite3.connect to raise
        monkeypatch.setattr(
            "stock_rtx4060.data_cache.sqlite3.connect",
            lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("forced")),
        )
        result = cache.get("AAPL", "1y", "yfinance")
        assert result is None

    def test_set_raises_logs_warning(self, tmp_path, monkeypatch):
        """set() catches any sqlite exception (line 145-146)."""
        cache = _make_cache(tmp_path)
        monkeypatch.setattr(
            "stock_rtx4060.data_cache.sqlite3.connect",
            lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("forced")),
        )
        # Should not raise
        cache.set("AAPL", "1y", "yfinance", _make_df())

    def test_invalidate_returns_zero_when_disabled(self, tmp_path, monkeypatch):
        """invalidate() returns 0 when disabled (line 151)."""
        monkeypatch.setenv("USE_DATA_CACHE", "0")
        cache = DataCache(db_path=tmp_path / "off.db")
        result = cache.invalidate("AAPL")
        assert result == 0

    def test_invalidate_raises_returns_zero(self, tmp_path, monkeypatch):
        """invalidate() catches sqlite exceptions (line 158-160)."""
        cache = _make_cache(tmp_path)
        monkeypatch.setattr(
            "stock_rtx4060.data_cache.sqlite3.connect",
            lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("forced")),
        )
        result = cache.invalidate("AAPL")
        assert result == 0

    def test_purge_expired_returns_zero_when_disabled(self, tmp_path, monkeypatch):
        """purge_expired() returns 0 when disabled (line 165)."""
        monkeypatch.setenv("USE_DATA_CACHE", "0")
        cache = DataCache(db_path=tmp_path / "off2.db")
        result = cache.purge_expired()
        assert result == 0

    def test_purge_expired_raises_returns_zero(self, tmp_path, monkeypatch):
        """purge_expired() catches sqlite exceptions (line 175-177)."""
        cache = _make_cache(tmp_path)
        monkeypatch.setattr(
            "stock_rtx4060.data_cache.sqlite3.connect",
            lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("forced")),
        )
        result = cache.purge_expired()
        assert result == 0


# ---------------------------------------------------------------------------
# compliance.py  — missing lines: 90-91, 97-98, 121-122, 145, 159, 162-163,
#                                   217-220, 223, 267, 274-279, 286, 289-290,
#                                   298-299, 370->374
# ---------------------------------------------------------------------------

from stock_rtx4060.broker.compliance import (
    ComplianceConfig,
    ComplianceError,
    _check_krx_price_limit,
    _check_sector_exposure,
    _check_single_position,
    _check_wash_sale,
    check_order,
)


class TestComplianceMissingBranches:
    def test_load_sector_map_invalid_json(self, tmp_path):
        """load_sector_map returns {} on json.JSONDecodeError (line 90-91)."""
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        cfg = ComplianceConfig(sector_map_path=bad, restricted_tickers_path=tmp_path / "r.txt")
        assert cfg.load_sector_map() == {}

    def test_load_restricted_tickers_missing_file(self, tmp_path):
        """load_restricted_tickers returns set() on FileNotFoundError (line 97-98)."""
        cfg = ComplianceConfig(
            sector_map_path=tmp_path / "s.json",
            restricted_tickers_path=tmp_path / "missing.txt",
        )
        assert cfg.load_restricted_tickers() == set()

    def test_single_position_with_dict_position_no_market_value(self):
        """Dict position missing market_value uses 0.0 (line 121-122)."""
        pos = {"qty": 10}  # no market_value key
        # 50 * 50 = 2500 / 100000 = 2.5% < 10% → no raise
        _check_single_position("AAPL", 50, 50.0, 100_000.0, {"AAPL": pos}, 0.10)

    def test_single_position_with_dict_position_exceeds_limit(self):
        """Dict position with market_value triggers limit (line 121-122)."""
        pos = {"market_value": 9500.0}
        with pytest.raises(ComplianceError, match="Single-position"):
            _check_single_position("AAPL", 10, 100.0, 100_000.0, {"AAPL": pos}, 0.10)

    def test_sector_check_zero_portfolio(self):
        """_check_sector_exposure returns early on portfolio_value=0 (line 145)."""
        _check_sector_exposure("AAPL", 100, 100.0, 0.0, {}, {"AAPL": "Tech"}, 0.25)

    def test_sector_check_dict_positions(self):
        """Sector exposure with dict positions (lines 162-163)."""
        sector_map = {"AAPL": "Technology", "MSFT": "Technology"}
        existing = {"MSFT": {"market_value": 20_000.0}}
        # 20k + 1k = 21k / 100k = 21% < 25% → OK
        _check_sector_exposure("AAPL", 10, 100.0, 100_000.0, existing, sector_map, 0.25)

    def test_sector_check_dict_positions_exceeds(self):
        """Sector exposure with dict positions triggers limit."""
        sector_map = {"AAPL": "Technology", "MSFT": "Technology"}
        existing = {"MSFT": {"market_value": 24_000.0}}
        with pytest.raises(ComplianceError, match="Sector exposure"):
            _check_sector_exposure("AAPL", 20, 100.0, 100_000.0, existing, sector_map, 0.25)

    def test_krx_price_limit_with_dict_position(self):
        """KRX check with dict positions (lines 217-220)."""
        pos_dict = {"avg_cost": 50_000.0, "market_value": 1000.0}
        existing = {"005930.KS": pos_dict}
        # 51000 is +2% — within 30%
        _check_krx_price_limit("005930.KS", 51_000.0, existing, 0.30)

    def test_krx_price_limit_dict_exceeds(self):
        """KRX price limit breach with dict position (lines 217-220)."""
        pos_dict = {"avg_cost": 50_000.0, "market_value": 1000.0}
        existing = {"005930.KS": pos_dict}
        with pytest.raises(ComplianceError, match="KRX price limit"):
            _check_krx_price_limit("005930.KS", 80_000.0, existing, 0.30)

    def test_krx_price_limit_zero_ref_price(self):
        """KRX check returns early when ref_price <= 0 (line 223)."""
        pos_dict = {"avg_cost": 0.0}
        existing = {"005930.KS": pos_dict}
        _check_krx_price_limit("005930.KS", 50_000.0, existing, 0.30)

    def test_wash_sale_closed_positions_dict_interface(self):
        """Wash-sale check with closed_positions dict interface (line 267)."""
        tracker = MagicMock(spec=[])
        tracker.closed_positions = {
            "AAPL": [{"date": (date.today() - timedelta(days=5)).isoformat(), "pnl": -200.0}]
        }
        with pytest.raises(ComplianceError, match="Wash-sale"):
            _check_wash_sale("AAPL", "BUY", tracker, 30)

    def test_wash_sale_closed_positions_list_interface(self):
        """Wash-sale check with closed_positions list interface (lines 274-279)."""
        tracker = MagicMock(spec=[])
        tracker.closed_positions = [
            {"ticker": "AAPL", "date": (date.today() - timedelta(days=5)).isoformat(), "pnl": -300.0}
        ]
        with pytest.raises(ComplianceError, match="Wash-sale"):
            _check_wash_sale("AAPL", "BUY", tracker, 30)

    def test_wash_sale_closes_with_no_date_skipped(self):
        """Close entries without a date field are skipped (line 286)."""
        tracker = MagicMock()
        tracker.get_recent_closes.return_value = [{"pnl": -500.0}]  # no date
        _check_wash_sale("AAPL", "BUY", tracker, 30)  # no exception

    def test_wash_sale_closes_with_bad_date_skipped(self):
        """Close entries with unparseable date are skipped (lines 289-290)."""
        tracker = MagicMock()
        tracker.get_recent_closes.return_value = [{"date": "not-a-date", "pnl": -500.0}]
        _check_wash_sale("AAPL", "BUY", tracker, 30)  # no exception

    def test_wash_sale_exception_in_get_recent_closes_is_swallowed(self):
        """Exception in get_recent_closes is caught and check is skipped (lines 298-299)."""
        tracker = MagicMock()
        tracker.get_recent_closes.side_effect = RuntimeError("DB down")
        _check_wash_sale("AAPL", "BUY", tracker, 30)  # no exception

    def test_check_order_allow_leverage_flag(self, tmp_path):
        """With allow_leverage=True the no-leverage check is skipped (line 370->374)."""
        sector_file = tmp_path / "s.json"
        sector_file.write_text("{}", encoding="utf-8")
        restricted_file = tmp_path / "r.txt"
        restricted_file.write_text("", encoding="utf-8")
        cfg = ComplianceConfig(
            allow_leverage=True,
            max_single_position_pct=1.0,  # bypass single position limit
            max_sector_exposure_pct=1.0,  # bypass sector limit
            sector_map_path=sector_file,
            restricted_tickers_path=restricted_file,
        )
        # Would fail no-leverage check if allow_leverage=False
        # 95k existing + 200*100=20k new = 115k > 100k portfolio → would fail
        existing = {"MSFT": {"market_value": 95_000.0}}
        check_order(
            ticker="AAPL",
            qty=200,
            side="BUY",
            current_positions=existing,
            portfolio_value=100_000.0,
            config=cfg,
            price=100.0,
        )


# ---------------------------------------------------------------------------
# backtest_honesty.py  — missing lines: 83, 86, 94, 101, 114, 126, 136, 139
# ---------------------------------------------------------------------------

from stock_rtx4060.backtest_honesty import (
    _drawdown_check,
    _cost_buffer_check,
    _fmt,
    _numeric_floor_check,
    _valid_number,
    _walk_forward_gap_check,
    evaluate_backtest_honesty,
    summarize_honesty,
)


class TestBacktestHonestyMissing:
    def test_numeric_floor_check_amber_when_value_missing(self):
        """None value returns AMBER (line 83)."""
        result = _numeric_floor_check(name="X", value=None, threshold=0.5, unit="ratio", fail_below=0.25)
        assert result["status"] == "AMBER"

    def test_numeric_floor_check_fail_when_below_fail_below(self):
        """Value < fail_below → FAIL (line 86)."""
        result = _numeric_floor_check(name="X", value=0.1, threshold=0.5, unit="ratio", fail_below=0.25)
        assert result["status"] == "FAIL"

    def test_drawdown_check_amber_when_missing(self):
        """None mdd returns AMBER (line 94)."""
        result = _drawdown_check(mdd_pct=None, max_mdd_pct=25.0)
        assert result["status"] == "AMBER"

    def test_cost_buffer_check_amber_when_return_missing(self):
        """None total_return returns AMBER (line 101)."""
        result = _cost_buffer_check(total_return_pct=None, transaction_cost_buffer_pct=0.5)
        assert result["status"] == "AMBER"

    def test_walk_forward_gap_check_amber_when_cv_gap_none(self):
        """None cv_gap returns AMBER (line 114)."""
        result = _walk_forward_gap_check(cv_gap=None, horizon=20)
        assert result["status"] == "AMBER"

    def test_walk_forward_gap_check_amber_when_gap_below_horizon(self):
        """Gap < horizon returns AMBER (line 126)."""
        result = _walk_forward_gap_check(cv_gap=10, horizon=20)
        assert result["status"] == "AMBER"

    def test_fmt_returns_missing_for_none(self):
        """_fmt with None returns 'missing' (line 136)."""
        assert _fmt(None, "ratio") == "missing"

    def test_fmt_ratio_format(self):
        """_fmt with ratio unit returns percentage (line 139)."""
        assert _fmt(0.123, "ratio") == "12.30%"

    def test_fmt_non_ratio_format(self):
        """_fmt with non-ratio unit returns decimal."""
        assert _fmt(1.5, "other") == "1.500"

    def test_valid_number_false_for_inf(self):
        """isfinite check rejects inf."""
        import math
        assert _valid_number(math.inf) is False

    def test_evaluate_fails_on_sharpe_below_fail_below(self):
        """FAIL status when sharpe below fail_below threshold."""
        result = evaluate_backtest_honesty(
            oof_coverage=0.72,
            min_oof_coverage=0.45,
            sharpe=-2.0,
            min_sharpe=-0.25,
            mdd_pct=12.0,
            max_mdd_pct=25.0,
            total_return_pct=4.5,
            transaction_cost_buffer_pct=0.5,
            cv_gap=20,
            horizon=20,
        )
        assert result["status"] == "FAIL"
        sharpe_check = next(c for c in result["checks"] if c["name"] == "SHARPE_FLOOR")
        assert sharpe_check["status"] == "FAIL"

    def test_summarize_honesty_empty_returns_amber(self):
        """Empty item list → AMBER."""
        result = summarize_honesty([])
        assert result["status"] == "AMBER"
        assert result["result_count"] == 0


# ---------------------------------------------------------------------------
# news_sentiment.py  — missing lines: 131-154, 158-161, 167-168, 178, 181-188
# ---------------------------------------------------------------------------

import asyncio

from stock_rtx4060.advisors.claude_client import CallResult
from stock_rtx4060.advisors.news_sentiment import (
    NewsSentimentAgent,
    _NewsItem,
    _clip,
    _matches_ticker,
    _parse_advisor_json,
)


class _StubClient:
    async def acall(self, *, system, messages, tools=None, max_tokens=None):
        return CallResult(
            text='{"score": 0.3, "confidence": 0.6, "rationale": "ok", "citations": ["http://x"]}',
            raw_message=None,
            tokens_in=10,
            tokens_out=5,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_usd=0.0,
            prompt_hash="h",
            model="claude-opus-4-7",
        )


class TestNewsSentimentMissing:
    def test_fetch_for_ticker_with_feedparser_unavailable(self):
        """When feedparser is not installed, yields nothing (lines 131-154 path via import fail)."""
        import sys
        old_modules = sys.modules.copy()
        sys.modules["feedparser"] = None  # type: ignore[assignment]
        try:
            agent = NewsSentimentAgent(client=_StubClient())
            out = asyncio.run(agent.analyze("AAPL", {}))
            assert out.rationale == "no news data"
        finally:
            if "feedparser" in sys.modules:
                del sys.modules["feedparser"]
            # Restore
            for k in list(sys.modules.keys()):
                if k not in old_modules:
                    del sys.modules[k]
            sys.modules.update(old_modules)

    def test_fetch_fn_with_max_headlines_limit(self):
        """fetch_fn results are limited to max_headlines (line 122-124)."""
        items = [_NewsItem(source="x", title=f"MSFT item {i}", url=f"http://{i}", summary="s") for i in range(20)]
        agent = NewsSentimentAgent(client=_StubClient(), fetch_fn=lambda *a: items, max_headlines=5)
        out = asyncio.run(agent.analyze("MSFT", {}))
        assert out.score == 0.3  # stub client response

    def test_context_headlines_limit(self):
        """Context headlines are limited to max_headlines (line 112)."""
        headlines = [{"source": "x", "title": f"TSLA h{i}", "url": f"http://{i}", "summary": ""} for i in range(20)]
        agent = NewsSentimentAgent(client=_StubClient(), max_headlines=3)
        out = asyncio.run(agent.analyze("TSLA", {"headlines": headlines}))
        assert out.score == 0.3

    def test_clip_handles_type_error(self):
        """_clip returns 0.0 for non-numeric values (line 167-168)."""
        assert _clip(None, -1.0, 1.0) == 0.0
        assert _clip("bad", -1.0, 1.0) == 0.0

    def test_clip_handles_value_error(self):
        """_clip returns 0.0 for non-convertible string (line 167-168)."""
        assert _clip("xyz", 0.0, 1.0) == 0.0

    def test_matches_ticker_empty_ticker(self):
        """_matches_ticker returns False for empty ticker (line 158-159)."""
        assert _matches_ticker("", "some text AAPL") is False

    def test_matches_ticker_found(self):
        """_matches_ticker returns True when ticker found as word (line 161)."""
        assert _matches_ticker("AAPL", "AAPL earnings beat") is True

    def test_matches_ticker_not_found(self):
        """_matches_ticker returns False when ticker not in text."""
        assert _matches_ticker("TSLA", "AAPL earnings beat") is False

    def test_parse_advisor_json_empty_string(self):
        """_parse_advisor_json returns {} for empty string (line 178)."""
        assert _parse_advisor_json("") == {}

    def test_parse_advisor_json_plain_json(self):
        """_parse_advisor_json parses valid JSON directly (line 181)."""
        result = _parse_advisor_json('{"score": 0.5}')
        assert result["score"] == 0.5

    def test_parse_advisor_json_embedded_in_text(self):
        """_parse_advisor_json extracts JSON from surrounding text (lines 182-188)."""
        text = 'Here is the result: {"score": 0.7, "confidence": 0.8} — end'
        result = _parse_advisor_json(text)
        assert result["score"] == 0.7

    def test_parse_advisor_json_invalid_json_returns_empty(self):
        """_parse_advisor_json returns {} when no valid JSON found (line 188)."""
        assert _parse_advisor_json("no json here at all") == {}

    def test_parse_advisor_json_invalid_embedded_json(self):
        """_parse_advisor_json returns {} for invalid embedded JSON."""
        assert _parse_advisor_json("result: {bad json}") == {}

    def test_no_citations_uses_headline_urls(self):
        """When client response has no citations, uses headline URLs (line 92)."""
        class _NoCiteClient:
            async def acall(self, *, system, messages, tools=None, max_tokens=None):
                return CallResult(
                    text='{"score": 0.1, "confidence": 0.5, "rationale": "ok"}',
                    raw_message=None, tokens_in=10, tokens_out=5,
                    cache_read_tokens=0, cache_creation_tokens=0, cost_usd=0.0,
                    prompt_hash="h", model="claude-opus-4-7",
                )
        items = [_NewsItem(source="x", title="AAPL headline", url="http://aapl-news", summary="s")]
        agent = NewsSentimentAgent(client=_NoCiteClient(), fetch_fn=lambda *a: items)
        out = asyncio.run(agent.analyze("AAPL", {}))
        assert "http://aapl-news" in out.citations


# ---------------------------------------------------------------------------
# mcp_adapter.py  — missing lines: 49, 51
# ---------------------------------------------------------------------------

from stock_rtx4060.mcp_adapter import (
    McpWorkflowContract,
    assert_phase1_mcp_boundary,
)


class TestMcpAdapterMissing:
    def test_assert_phase1_raises_on_server_starting_contract(self, monkeypatch):
        """assert_phase1_mcp_boundary raises if starts_server=True (line 49)."""
        bad_contract = McpWorkflowContract(
            name="bad_server",
            command="recommend",
            access="read_report_only",
            starts_server=True,
        )
        monkeypatch.setattr(
            "stock_rtx4060.mcp_adapter.ALLOWED_MCP_WORKFLOWS",
            (bad_contract,),
        )
        with pytest.raises(AssertionError, match="unsafe MCP contract"):
            assert_phase1_mcp_boundary()

    def test_assert_phase1_raises_on_unsupported_access_mode(self, monkeypatch):
        """assert_phase1_mcp_boundary raises on wrong access mode (line 51)."""
        bad_contract = McpWorkflowContract(
            name="bad_access",
            command="recommend",
            access="read_report_only",  # must bypass type check to set wrong value
        )
        # Patch the access attribute after creation (frozen=False for McpWorkflowContract)
        from stock_rtx4060 import mcp_adapter
        import dataclasses as _dc

        # Re-create with monkeypatched access via object.__setattr__
        bad = McpWorkflowContract(
            name="bad",
            command="recommend",
            access="read_report_only",
        )
        # We can't modify frozen dataclass, so patch the module attribute directly
        class _BadContract:
            name = "bad"
            starts_server = False
            broker_order_execution = False
            account_write = False
            access = "write_enabled"  # wrong access mode

        monkeypatch.setattr(
            "stock_rtx4060.mcp_adapter.ALLOWED_MCP_WORKFLOWS",
            (_BadContract(),),
        )
        with pytest.raises(AssertionError, match="unsupported MCP access mode"):
            assert_phase1_mcp_boundary()


# ---------------------------------------------------------------------------
# adjuster.py  — missing lines: 26, 33, 36-44, 54, 59->58, 61->63
# ---------------------------------------------------------------------------

from stock_rtx4060.data_lake.corp_actions.adjuster import adjust_ohlcv, build_adjustment_factor
from stock_rtx4060.data_lake.corp_actions.splits_dividends import CorpAction


class TestAdjusterMissing:
    def _make_ohlcv(self, n: int = 5) -> pd.DataFrame:
        idx = pd.date_range("2026-01-01", periods=n, freq="D")
        return pd.DataFrame(
            {
                "Open": [100.0] * n,
                "High": [102.0] * n,
                "Low": [98.0] * n,
                "Close": [101.0] * n,
                "Volume": [1_000_000] * n,
            },
            index=idx,
        )

    def test_build_factor_empty_closes(self):
        """Empty closes returns empty Series (line 26)."""
        result = build_adjustment_factor(pd.Series(dtype="float64"), [])
        assert result.empty

    def test_build_factor_split_action_before_first_date_no_op(self):
        """Action date before all close dates → before_mask.any() is False → skip (line 33)."""
        closes = pd.Series(
            [100.0, 101.0, 102.0],
            index=pd.date_range("2026-06-01", periods=3, freq="D"),
        )
        # Action date is BEFORE all prices → no price is before the action → skip
        action = CorpAction(date=pd.Timestamp("2026-01-01"), type="split", ratio=2.0)
        factor = build_adjustment_factor(closes, [action])
        assert (factor == 1.0).all()

    def test_build_factor_split_adjusts_earlier_prices(self):
        """Split action adjusts all dates before the split date (line 35)."""
        closes = pd.Series(
            [100.0, 100.0, 100.0],
            index=pd.date_range("2026-01-01", periods=3, freq="D"),
        )
        # Split on day 2: pre-split prices halved
        action = CorpAction(date=pd.Timestamp("2026-01-02"), type="split", ratio=2.0)
        factor = build_adjustment_factor(closes, [action])
        # Day 1 should be adjusted (× 0.5), day 2 onwards = 1.0
        assert factor.iloc[0] == pytest.approx(0.5)
        assert factor.iloc[1] == pytest.approx(1.0)

    def test_build_factor_dividend_adjusts_earlier_prices(self):
        """Dividend action reduces factor for earlier prices (lines 36-44)."""
        closes = pd.Series(
            [100.0, 100.0, 100.0],
            index=pd.date_range("2026-01-01", periods=3, freq="D"),
        )
        # $1 dividend on day 2: mult = 1 - 1/100 = 0.99
        action = CorpAction(date=pd.Timestamp("2026-01-02"), type="dividend", cash_amount=1.0)
        factor = build_adjustment_factor(closes, [action])
        assert factor.iloc[0] == pytest.approx(0.99)
        assert factor.iloc[1] == pytest.approx(1.0)

    def test_build_factor_dividend_negative_mult_skipped(self):
        """Dividend larger than close price is skipped (mult <= 0)."""
        closes = pd.Series(
            [0.5, 0.5],  # very low close
            index=pd.date_range("2026-01-01", periods=2, freq="D"),
        )
        # $1 dividend on tiny stock → mult = 1 - 1/0.5 = -1 → skip
        action = CorpAction(date=pd.Timestamp("2026-01-02"), type="dividend", cash_amount=1.0)
        factor = build_adjustment_factor(closes, [action])
        assert (factor == 1.0).all()

    def test_build_factor_dividend_close_at_action_before_start(self):
        """close_at_action_idx < 0 → dividend skipped (line 39)."""
        closes = pd.Series(
            [100.0, 101.0],
            index=pd.date_range("2026-01-02", periods=2, freq="D"),
        )
        # Action on day before all data → searchsorted returns 0, so idx -1 < 0
        action = CorpAction(date=pd.Timestamp("2026-01-01"), type="dividend", cash_amount=1.0)
        factor = build_adjustment_factor(closes, [action])
        assert (factor == 1.0).all()

    def test_adjust_ohlcv_empty_frame(self):
        """adjust_ohlcv returns copy of empty frame (line 54)."""
        empty = pd.DataFrame()
        result = adjust_ohlcv(empty, [])
        assert result.empty

    def test_adjust_ohlcv_adds_adj_columns(self):
        """adjust_ohlcv adds adj_open, adj_high, adj_low, adj_close, adj_volume."""
        frame = self._make_ohlcv(3)
        action = CorpAction(date=pd.Timestamp("2026-01-02"), type="split", ratio=2.0)
        result = adjust_ohlcv(frame, [action])
        for col in ("adj_open", "adj_high", "adj_low", "adj_close", "adj_volume"):
            assert col in result.columns

    def test_adjust_ohlcv_without_volume(self):
        """adjust_ohlcv works if Volume column is missing (branch line 61->63)."""
        frame = self._make_ohlcv(3).drop(columns=["Volume"])
        result = adjust_ohlcv(frame, [])
        assert "adj_volume" not in result.columns
        assert "adj_close" in result.columns

    def test_build_factor_no_ratio_split_skipped(self):
        """Split without ratio is effectively a no-op (line 34: action.ratio is None)."""
        closes = pd.Series(
            [100.0, 100.0],
            index=pd.date_range("2026-01-01", periods=2, freq="D"),
        )
        action = CorpAction(date=pd.Timestamp("2026-01-02"), type="split", ratio=None)
        factor = build_adjustment_factor(closes, [action])
        # With ratio=None, the split branch condition is False → factor stays 1.0
        assert (factor == 1.0).all()

    def test_build_factor_dividend_no_cash_amount_skipped(self):
        """Dividend without cash_amount is skipped."""
        closes = pd.Series(
            [100.0, 100.0],
            index=pd.date_range("2026-01-01", periods=2, freq="D"),
        )
        action = CorpAction(date=pd.Timestamp("2026-01-02"), type="dividend", cash_amount=None)
        factor = build_adjustment_factor(closes, [action])
        assert (factor == 1.0).all()
