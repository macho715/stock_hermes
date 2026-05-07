"""Paper-only virtual trading engine.

The module records simulated decisions and fills for review. It never submits
broker orders or reads broker credentials.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .krx_calendar import KRXCalendarUnavailable, load_krx_calendar_fixture, next_krx_session

SCHEMA_VERSION = "paper_trading.v1"
STATUS_SCHEMA_VERSION = "paper_status.v1"
PAPER_ONLY_LABEL = "Paper trading only - no broker orders"
KRX_PILOT_LABEL = "KRX paper trading pilot"
KRX_DEFAULT_UNIVERSE = ("005930.KS", "000660.KS", "005380.KS", "035420.KS", "035720.KS")
KRX_BENCHMARK_TICKER = "069500.KS"
KRX_APPROVED_PROVIDERS = {"pykrx", "financedatareader", "fdr"}


@dataclass(frozen=True)
class PaperTradingConfig:
    output_root: Path | str = Path("reports/paper_trading/runs")
    run_date: str | None = None
    strategy_id: str = "paper-v1"
    market: str = "US"
    currency: str | None = None
    timezone: str | None = None
    krx_calendar_fixture_path: Path | str | None = None
    krx_default_universe: tuple[str, ...] = KRX_DEFAULT_UNIVERSE
    krx_benchmark_ticker: str = KRX_BENCHMARK_TICKER
    krx_starting_cash: float = 10_000_000.0
    krx_max_position_pct: float = 0.10
    starting_cash: float = 100_000.0
    cash_buffer_pct: float = 0.05
    max_position_pct: float = 0.10
    max_exposure_pct: float = 0.60
    risk_budget_pct: float = 0.0075
    min_model_auc: float = 0.55
    min_model_accuracy: float = 0.52
    min_oof_coverage: float = 0.80
    max_missing_bar_ratio: float = 0.05
    stale_days: int = 10
    split_raw_move_threshold: float = 0.35
    adjusted_raw_mismatch_threshold: float = 0.10
    split_ratio_tolerance: float = 0.03
    krx_price_limit_pct: float = 0.30
    slippage_pct: float = 0.0005
    commission: float = 0.0
    phase1_us_only: bool = True
    force_rerun: bool = False
    rerun_reason: str | None = None
    min_buy_score: float = 56.0
    max_open_positions: int = 10
    max_daily_new_positions: int = 3

    @property
    def effective_run_date(self) -> str:
        return self.run_date or date.today().isoformat()

    @property
    def normalized_market(self) -> str:
        return self.market.upper()

    @property
    def effective_currency(self) -> str:
        return self.currency or ("KRW" if self.normalized_market == "KRX" else "USD")

    @property
    def effective_timezone(self) -> str:
        return self.timezone or ("Asia/Seoul" if self.normalized_market == "KRX" else "America/New_York")

    @property
    def effective_starting_cash(self) -> float:
        return self.krx_starting_cash if self.normalized_market == "KRX" else self.starting_cash

    @property
    def effective_max_position_pct(self) -> float:
        return self.krx_max_position_pct if self.normalized_market == "KRX" else self.max_position_pct


@dataclass(frozen=True)
class PaperTradingSignal:
    ticker: str
    score: float
    signal: str
    model_auc: float | None
    model_accuracy: float | None
    oof_coverage: float | None
    warning: str | None = None


@dataclass(frozen=True)
class PaperDecision:
    ticker: str
    status: str
    reason: str
    signal: str
    score: float
    market: str = "US"
    currency: str = "USD"
    timezone: str = "America/New_York"
    fill_date: str | None = None
    paper_trading_only: bool = True

    def to_record(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": self.ticker,
            "status": self.status,
            "reason": self.reason,
            "signal": self.signal,
            "score": self.score,
            "market": self.market,
            "currency": self.currency,
            "timezone": self.timezone,
            "fill_date": self.fill_date,
            "paper_trading_only": self.paper_trading_only,
        }


class PaperTradingEngine:
    def __init__(self, config: PaperTradingConfig | None = None):
        self.config = config or PaperTradingConfig()

    def evaluate_signal(self, signal: PaperTradingSignal, bars: list[dict[str, Any]] | None) -> PaperDecision:
        ticker = signal.ticker.upper()
        normalized_signal = signal.signal.upper()
        if self.config.phase1_us_only and _is_krx_ticker(ticker):
            return self._reject(signal, "market_not_enabled_phase1")
        if self.config.normalized_market == "KRX" and not _is_krx_ticker(ticker):
            return self._reject(signal, "market_not_krx_pilot")
        if signal.warning and "모델 품질 낮음" in signal.warning:
            return self._reject(signal, "weak_model_quality")
        if signal.model_auc is None or signal.model_accuracy is None or signal.oof_coverage is None:
            return self._reject(signal, "model_evidence_missing")
        if (
            signal.model_auc < self.config.min_model_auc
            or signal.model_accuracy < self.config.min_model_accuracy
            or signal.oof_coverage < self.config.min_oof_coverage
        ):
            return self._reject(signal, "weak_model_quality")
        if normalized_signal == "HOLD":
            return self._reject(signal, "hold_not_tradable")
        if normalized_signal != "BUY":
            return self._reject(signal, "signal_not_open_long")
        if signal.score < self.config.min_buy_score:
            return self._reject(signal, "buy_score_below_threshold")
        if _has_nonpositive_ohlcv(bars or []):
            return self._reject(signal, "ohlcv_invalid")
        if _has_split_uncertainty(bars or [], self.config):
            return self._reject(signal, "split_dividend_uncertainty")
        data_issue = _validate_bars(bars or [], self.config)
        if data_issue:
            return self._reject(signal, data_issue)
        provider_issue = _krx_provider_issue(bars or [], self.config)
        if provider_issue:
            return self._reject(signal, provider_issue)
        price_limit_issue = _krx_price_limit_issue(bars or [], self.config)
        if price_limit_issue:
            return self._reject(signal, price_limit_issue)
        fill_date = self._eligible_fill_date(bars or [])
        if fill_date.startswith("krx_calendar_"):
            return self._reject(signal, fill_date)
        return PaperDecision(
            ticker=ticker,
            status="ACCEPTED",
            reason="passed_paper_gates",
            signal=normalized_signal,
            score=signal.score,
            market=self.config.normalized_market,
            currency=self.config.effective_currency,
            timezone=self.config.effective_timezone,
            fill_date=fill_date,
        )

    def run(self, signals: Iterable[PaperTradingSignal], bars_by_ticker: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        if self.config.force_rerun and not (self.config.rerun_reason and self.config.rerun_reason.strip()):
            raise ValueError("force_rerun requires rerun_reason")

        signal_list = list(signals)
        run_id = self._run_id(signal_list)
        output_root = self._output_root()
        run_dir = output_root / run_id
        required = [
            "paper_config.json",
            "signals.jsonl",
            "orders.jsonl",
            "fills.jsonl",
            "positions.jsonl",
            "equity_curve.csv",
            "daily_report.md",
        ]
        if run_dir.exists() and all((run_dir / name).exists() for name in required) and not self.config.force_rerun:
            return _with_run_identity(load_paper_status(output_root), run_id, run_dir)

        run_dir.mkdir(parents=True, exist_ok=True)
        lock_path = run_dir / ".paper_run.lock"
        lock_path.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
        try:
            return self._write_run(run_id, run_dir, signal_list, bars_by_ticker)
        except Exception:
            _write_json(run_dir / "paper_config.json", self._config_record(run_id, "FAILED_INCOMPLETE"))
            raise
        finally:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _write_run(
        self,
        run_id: str,
        run_dir: Path,
        signals: list[PaperTradingSignal],
        bars_by_ticker: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        starting_cash = float(self.config.effective_starting_cash)
        cash = starting_cash
        positions: list[dict[str, Any]] = []
        orders: list[dict[str, Any]] = []
        fills: list[dict[str, Any]] = []
        signal_records: list[dict[str, Any]] = []
        open_tickers: set[str] = set()
        new_positions_opened = 0

        for signal in signals:
            bars = bars_by_ticker.get(signal.ticker) or bars_by_ticker.get(signal.ticker.upper()) or []
            decision = self.evaluate_signal(signal, bars)
            record = decision.to_record(run_id)
            signal_records.append(record)
            if decision.status != "ACCEPTED":
                continue
            if decision.ticker in open_tickers:
                signal_records.append({**record, "status": "REJECTED", "reason": "duplicate_open_order"})
                continue
            if len(open_tickers) >= self.config.max_open_positions:
                signal_records.append({**record, "status": "REJECTED", "reason": "max_open_positions_reached"})
                continue
            if new_positions_opened >= self.config.max_daily_new_positions:
                signal_records.append({**record, "status": "REJECTED", "reason": "max_daily_new_positions_reached"})
                continue

            fill_price = _fill_open_or_fallback(bars, decision) * (1.0 + self.config.slippage_pct)
            order_value_cap = starting_cash * self.config.effective_max_position_pct
            cash_cap = max(0.0, cash - starting_cash * self.config.cash_buffer_pct)
            max_value = min(order_value_cap, cash_cap)
            shares = int(max_value / fill_price) if fill_price > 0 else 0
            if shares < 1:
                signal_records.append({**record, "status": "REJECTED", "reason": "position_size_below_one_share"})
                continue
            notional = round(shares * fill_price, 2)
            if notional > cash:
                signal_records.append({**record, "status": "REJECTED", "reason": "cash_cap_breach"})
                continue

            order_id = f"{run_id}-{decision.ticker}-OPEN_LONG"
            order = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "order_id": order_id,
                "ticker": decision.ticker,
                "order_type": "OPEN_LONG",
                "status": "FILLED",
                "shares": shares,
                "limit_price": None,
                "reason": decision.reason,
                "market": decision.market,
                "currency": decision.currency,
                "timezone": decision.timezone,
                "paper_trading_only": True,
            }
            fill = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "order_id": order_id,
                "ticker": decision.ticker,
                "fill_date": decision.fill_date or self.config.effective_run_date,
                "fill_price": round(fill_price, 4),
                "shares": shares,
                "notional": notional,
                "slippage_pct": self.config.slippage_pct,
                "commission": self.config.commission,
                "market": decision.market,
                "currency": decision.currency,
                "timezone": decision.timezone,
                "paper_trading_only": True,
            }
            cash = round(cash - notional - self.config.commission, 2)
            last_close = _last_close(bars)
            market_value = round(shares * last_close, 2)
            position = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "ticker": decision.ticker,
                "shares": shares,
                "avg_price": round(fill_price, 4),
                "last_price": round(last_close, 4),
                "market_value": market_value,
                "unrealized_pl": round(market_value - notional, 2),
                "market": decision.market,
                "currency": decision.currency,
                "timezone": decision.timezone,
                "paper_trading_only": True,
            }
            orders.append(order)
            fills.append(fill)
            positions.append(position)
            open_tickers.add(decision.ticker)
            new_positions_opened += 1

        equity = round(cash + sum(float(p["market_value"]) for p in positions), 2)
        equity_rows = [{"date": self.config.effective_run_date, "cash": cash, "equity": equity}]
        drawdown = calculate_promotion_drawdown(equity_rows)
        benchmark_gate = self._benchmark_gate(bars_by_ticker)

        _write_json(run_dir / "paper_config.json", self._config_record(run_id, "READY", benchmark_gate))
        _write_jsonl(run_dir / "signals.jsonl", signal_records)
        _write_jsonl(run_dir / "orders.jsonl", orders)
        _write_jsonl(run_dir / "fills.jsonl", fills)
        _write_jsonl(run_dir / "positions.jsonl", positions)
        _write_equity_curve(run_dir / "equity_curve.csv", equity_rows)
        _write_daily_report(run_dir / "daily_report.md", run_id, signal_records, positions, drawdown, benchmark_gate)
        return _with_run_identity(load_paper_status(self._output_root()), run_id, run_dir)

    def _run_id(self, signals: list[PaperTradingSignal]) -> str:
        tickers = ",".join(sorted(signal.ticker.upper() for signal in signals)) or "empty"
        digest = hashlib.sha1(tickers.encode("utf-8")).hexdigest()[:8]
        return f"{self.config.effective_run_date}-{self.config.strategy_id}-{digest}"

    def _config_record(self, run_id: str, status: str, benchmark_gate: dict[str, Any] | None = None) -> dict[str, Any]:
        cfg = asdict(self.config)
        cfg["output_root"] = str(cfg["output_root"])
        cfg["krx_calendar_fixture_path"] = str(cfg["krx_calendar_fixture_path"]) if cfg["krx_calendar_fixture_path"] else None
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "status": status,
            "market": self.config.normalized_market,
            "currency": self.config.effective_currency,
            "timezone": self.config.effective_timezone,
            "starting_cash": self.config.effective_starting_cash,
            "max_position_pct": self.config.effective_max_position_pct,
            "krx_default_universe": list(self.config.krx_default_universe) if self.config.normalized_market == "KRX" else None,
            "benchmark": benchmark_gate or self._config_benchmark_record(),
            "paper_trading_only": True,
            "paper_only_label": PAPER_ONLY_LABEL,
            "pilot_label": KRX_PILOT_LABEL if self.config.normalized_market == "KRX" else None,
            "config": cfg,
        }

    def _output_root(self) -> Path:
        root = Path(self.config.output_root)
        if self.config.normalized_market == "KRX" and root.name != "krx_runs":
            if root.name == "runs" and root.parent.name == "paper_trading":
                return root.parent / "krx_runs"
            return root / "krx_runs"
        return root

    def _eligible_fill_date(self, bars: list[dict[str, Any]]) -> str:
        if self.config.normalized_market != "KRX":
            return self.config.effective_run_date
        if not bars:
            return "krx_calendar_unavailable"
        latest_day = self.config.effective_run_date
        try:
            fixture = load_krx_calendar_fixture(self.config.krx_calendar_fixture_path) if self.config.krx_calendar_fixture_path else load_krx_calendar_fixture()
            return next_krx_session(latest_day, fixture)
        except KRXCalendarUnavailable as exc:
            message = str(exc)
            if message.startswith("krx_calendar_"):
                return message.split(":", 1)[0]
            return "krx_calendar_unavailable"

    def _benchmark_gate(self, bars_by_ticker: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        if self.config.normalized_market != "KRX":
            return {"ticker": None, "status": "NOT_APPLICABLE", "not_promotable": False, "reason": None}
        ticker = self.config.krx_benchmark_ticker.upper()
        bars = bars_by_ticker.get(ticker) or bars_by_ticker.get(self.config.krx_benchmark_ticker) or []
        if _validate_bars(bars, self.config) or _krx_provider_issue(bars, self.config):
            return {"ticker": ticker, "status": "MISSING", "not_promotable": True, "reason": "krx_benchmark_missing"}
        return {"ticker": ticker, "status": "PASS", "not_promotable": False, "reason": None}

    def _config_benchmark_record(self) -> dict[str, Any] | None:
        if self.config.normalized_market != "KRX":
            return None
        return {"ticker": self.config.krx_benchmark_ticker.upper(), "fallback_allowed": False}

    def _reject(self, signal: PaperTradingSignal, reason: str) -> PaperDecision:
        return PaperDecision(
            ticker=signal.ticker.upper(),
            status="REJECTED",
            reason=reason,
            signal=signal.signal.upper(),
            score=signal.score,
            market=self.config.normalized_market,
            currency=self.config.effective_currency,
            timezone=self.config.effective_timezone,
        )


def calculate_promotion_drawdown(equity_rows: list[dict[str, Any]], spy_max_drawdown_pct: float | None = None) -> dict[str, Any]:
    values = [_to_float(row.get("equity")) for row in equity_rows]
    values = [value for value in values if value is not None and value > 0]
    if not values:
        return {
            "max_drawdown_pct": None,
            "promotion_hard_fail": True,
            "not_promotable": True,
            "review_flags": ["missing_equity_curve"],
        }
    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = min(max_dd, (value / peak) - 1.0)
    max_dd_pct = round(abs(max_dd) * 100.0, 4)
    flags: list[str] = []
    hard_fail = max_dd_pct > 10.0
    if hard_fail:
        flags.append("mdd_90d_gt_10pct")
    if max_dd_pct > 8.0:
        flags.append("mdd_30d_gt_8pct_review")
    if spy_max_drawdown_pct is not None and max_dd_pct - spy_max_drawdown_pct > 3.0:
        flags.append("spy_relative_mdd_review")
    return {
        "max_drawdown_pct": max_dd_pct,
        "promotion_hard_fail": hard_fail,
        "not_promotable": hard_fail,
        "review_flags": flags,
    }


def load_paper_status(output_root: Path | str) -> dict[str, Any]:
    runs_root = _resolve_runs_root(Path(output_root))
    run_dirs = sorted([p for p in runs_root.glob("*") if p.is_dir()]) if runs_root.exists() else []
    if not run_dirs:
        return _empty_status()
    latest = run_dirs[-1]
    config = _read_json(latest / "paper_config.json") or {}
    positions = _read_jsonl(latest / "positions.jsonl")
    signals = _read_jsonl(latest / "signals.jsonl")
    equity_curve = _read_equity_curve(latest / "equity_curve.csv")
    rejected = [row for row in signals if row.get("status") == "REJECTED"]
    drawdown = calculate_promotion_drawdown(equity_curve)
    benchmark_gate = config.get("benchmark") or {"ticker": None, "status": "NOT_APPLICABLE", "not_promotable": False, "reason": None}
    if benchmark_gate.get("not_promotable") and "krx_benchmark_missing" not in drawdown["review_flags"]:
        drawdown = {**drawdown, "not_promotable": True, "review_flags": [*drawdown["review_flags"], "krx_benchmark_missing"]}
    return {
        "schema_version": STATUS_SCHEMA_VERSION,
        "paper_trading_only": True,
        "paper_only_label": PAPER_ONLY_LABEL,
        "status": config.get("status") or "READY",
        "latest_run": {
            "run_id": config.get("run_id") or latest.name,
            "path": str(latest),
            "strategy_id": (config.get("config") or {}).get("strategy_id"),
        },
        "positions": positions,
        "rejected_signals": rejected,
        "equity_curve": equity_curve,
        "drawdown": drawdown,
        "benchmark": benchmark_gate,
        "model_quality_gate": {
            "min_model_auc": (config.get("config") or {}).get("min_model_auc", 0.55),
            "min_model_accuracy": (config.get("config") or {}).get("min_model_accuracy", 0.52),
            "min_oof_coverage": (config.get("config") or {}).get("min_oof_coverage", 0.80),
        },
    }


def rebuild_daily_report(run_dir: Path | str) -> Path:
    path = Path(run_dir)
    config = _read_json(path / "paper_config.json") or {}
    run_id = config.get("run_id") or path.name
    signals = _read_jsonl(path / "signals.jsonl")
    positions = _read_jsonl(path / "positions.jsonl")
    equity = _read_equity_curve(path / "equity_curve.csv")
    drawdown = calculate_promotion_drawdown(equity)
    benchmark_gate = config.get("benchmark") or {"ticker": None, "status": "NOT_APPLICABLE", "not_promotable": False, "reason": None}
    report = path / "daily_report.md"
    _write_daily_report(report, run_id, signals, positions, drawdown, benchmark_gate)
    return report


def _with_run_identity(status: dict[str, Any], run_id: str, run_dir: Path) -> dict[str, Any]:
    return {
        **status,
        "run_id": run_id,
        "run_dir": str(run_dir),
    }


def _is_krx_ticker(ticker: str) -> bool:
    return ticker.endswith(".KS") or ticker.endswith(".KQ")


def _validate_bars(bars: list[dict[str, Any]], config: PaperTradingConfig) -> str | None:
    if not bars:
        return "ohlcv_missing"
    invalid_rows = 0
    seen_dates: set[str] = set()
    for bar in bars:
        day = str(bar.get("date", ""))
        if day in seen_dates:
            return "duplicate_ohlcv_date"
        if day:
            seen_dates.add(day)
        values = [_to_float(bar.get(key)) for key in ("open", "high", "low", "close")]
        volume = _to_float(bar.get("volume"))
        if any(value is None or value <= 0 for value in values) or volume is None or volume < 0:
            invalid_rows += 1
            continue
        open_, high, low, close = values
        if high < low or high < max(open_, close) or low > min(open_, close):
            invalid_rows += 1
    if invalid_rows / max(len(bars), 1) > config.max_missing_bar_ratio:
        return "ohlcv_invalid"
    latest = _parse_day(str(bars[-1].get("date", "")))
    if latest is not None:
        days_old = (date.today() - latest).days
        if days_old > config.stale_days:
            return "ohlcv_stale"
    return None


def _has_nonpositive_ohlcv(bars: list[dict[str, Any]]) -> bool:
    for bar in bars:
        prices = [_to_float(bar.get(key)) for key in ("open", "high", "low", "close")]
        volume = _to_float(bar.get("volume"))
        if any(value is None or value <= 0 for value in prices):
            return True
        if volume is None or volume < 0:
            return True
    return False


def _has_split_uncertainty(bars: list[dict[str, Any]], config: PaperTradingConfig) -> bool:
    if len(bars) < 2:
        return False
    prev = bars[-2]
    cur = bars[-1]
    prev_close = _to_float(prev.get("close"))
    cur_open = _to_float(cur.get("open"))
    cur_close = _to_float(cur.get("close"))
    if not prev_close or cur_open is None or cur_close is None:
        return True
    raw_gap = max(abs(cur_open / prev_close - 1.0), abs(cur_close / prev_close - 1.0))
    if raw_gap < config.split_raw_move_threshold:
        return False
    prev_adj = _to_float(prev.get("adjusted_close") or prev.get("adj_close"))
    cur_adj = _to_float(cur.get("adjusted_close") or cur.get("adj_close"))
    if not prev_adj or cur_adj is None:
        return True
    adjusted_gap = abs(cur_adj / prev_adj - 1.0)
    raw_close_gap = abs(cur_close / prev_close - 1.0)
    mismatch = abs(raw_close_gap - adjusted_gap)
    split_ratio = max(cur_close, prev_close) / max(min(cur_close, prev_close), 1e-9)
    near_common_split = any(abs(split_ratio - ratio) / ratio <= config.split_ratio_tolerance for ratio in (2.0, 3.0, 4.0, 5.0, 10.0))
    return mismatch >= config.adjusted_raw_mismatch_threshold or not near_common_split


def _krx_provider_issue(bars: list[dict[str, Any]], config: PaperTradingConfig) -> str | None:
    if config.normalized_market != "KRX":
        return None
    if not bars:
        return "krx_provider_ohlcv_missing"
    for bar in bars:
        if any(key not in bar for key in ("date", "open", "high", "low", "close", "volume", "adjusted_close", "provider")):
            return "krx_provider_field_missing"
        provider = str(bar.get("provider") or "").strip().lower()
        if provider not in KRX_APPROVED_PROVIDERS:
            return "krx_provider_not_approved"
    return None


def _krx_price_limit_issue(bars: list[dict[str, Any]], config: PaperTradingConfig) -> str | None:
    if config.normalized_market != "KRX" or len(bars) < 2:
        return None
    prev_close = _to_float(bars[-2].get("close"))
    cur_open = _to_float(bars[-1].get("open"))
    cur_close = _to_float(bars[-1].get("close"))
    if not prev_close or cur_open is None or cur_close is None:
        return None
    limit = abs(config.krx_price_limit_pct)
    limit_up = prev_close * (1.0 + limit)
    limit_down = prev_close * (1.0 - limit)
    if max(cur_open, cur_close) >= limit_up * 0.999:
        return "krx_limit_up_fill_blocked"
    if min(cur_open, cur_close) <= limit_down * 1.001:
        return "krx_limit_down_fill_blocked"
    return None


def _next_open_or_last_close(bars: list[dict[str, Any]]) -> float:
    if not bars:
        return 0.0
    return _to_float(bars[-1].get("open")) or _last_close(bars)


def _fill_open_or_fallback(bars: list[dict[str, Any]], decision: PaperDecision) -> float:
    if decision.market == "KRX" and decision.fill_date:
        for bar in bars:
            if str(bar.get("date") or "")[:10] == decision.fill_date:
                return _to_float(bar.get("open")) or _last_close(bars)
    return _next_open_or_last_close(bars)


def _last_close(bars: list[dict[str, Any]]) -> float:
    for bar in reversed(bars):
        close = _to_float(bar.get("close"))
        if close and close > 0:
            return close
    return 0.0


def _to_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _parse_day(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value[:10]).date()
    except ValueError:
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    os.replace(tmp, path)


def _write_equity_curve(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "cash", "equity"])
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def _write_daily_report(
    path: Path,
    run_id: str,
    signals: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    drawdown: dict[str, Any],
    benchmark_gate: dict[str, Any] | None = None,
) -> None:
    rejected = [row for row in signals if row.get("status") == "REJECTED"]
    lines = [
        f"# Paper Trading Daily Report - {run_id}",
        "",
        PAPER_ONLY_LABEL,
        "",
        f"- accepted_positions: {len(positions)}",
        f"- rejected_signals: {len(rejected)}",
        f"- max_drawdown_pct: {drawdown.get('max_drawdown_pct')}",
        f"- promotion_hard_fail: {drawdown.get('promotion_hard_fail')}",
        f"- benchmark: {(benchmark_gate or {}).get('ticker') or 'N/A'}",
        f"- benchmark_status: {(benchmark_gate or {}).get('status') or 'NOT_APPLICABLE'}",
        f"- benchmark_not_promotable: {(benchmark_gate or {}).get('not_promotable') is True}",
        "",
        "## Rejected Signals",
    ]
    if rejected:
        lines.extend(f"- {row.get('ticker')}: {row.get('reason')}" for row in rejected)
    else:
        lines.append("- none")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _read_equity_curve(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [
                {"date": row["date"], "cash": float(row["cash"]), "equity": float(row["equity"])}
                for row in csv.DictReader(handle)
            ]
    except (FileNotFoundError, KeyError, ValueError):
        return []


def _resolve_runs_root(root: Path) -> Path:
    candidates = [
        root / "reports" / "paper_trading" / "runs",
        root / "paper_trading" / "runs",
        root,
    ]
    for candidate in candidates:
        if candidate.exists() and any((child / "paper_config.json").exists() for child in candidate.iterdir() if child.is_dir()):
            return candidate
    if (root / "reports" / "paper_trading" / "runs").exists():
        return root / "reports" / "paper_trading" / "runs"
    return root


def _empty_status() -> dict[str, Any]:
    return {
        "schema_version": STATUS_SCHEMA_VERSION,
        "paper_trading_only": True,
        "paper_only_label": PAPER_ONLY_LABEL,
        "status": "EMPTY",
        "latest_run": None,
        "positions": [],
        "rejected_signals": [],
        "equity_curve": [],
        "drawdown": {
            "max_drawdown_pct": None,
            "promotion_hard_fail": True,
            "not_promotable": True,
            "review_flags": ["missing_equity_curve"],
        },
        "benchmark": {
            "ticker": None,
            "status": "NOT_APPLICABLE",
            "not_promotable": False,
            "reason": None,
        },
        "model_quality_gate": {
            "min_model_auc": 0.55,
            "min_model_accuracy": 0.52,
            "min_oof_coverage": 0.80,
        },
    }
