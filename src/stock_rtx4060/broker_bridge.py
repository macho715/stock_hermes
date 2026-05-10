"""
Broker Bridge — 브로커 어댑터 + 주문 시뮬레이션 구조

Stage 5 of 5-stage investment system upgrade.

⚠️  IMPORTANT SECURITY NOTE ⚠️
==============================
This module provides broker adapter structure and order simulation ONLY.
Actual broker API key integration, real order execution, and account
actions require EXPLICIT USER APPROVAL and must comply with:
  - AGENTS.md financial safety boundaries
  - Local regulations for the user's jurisdiction
  - Broker's API terms of service

This module operates in SIMULATION MODE by default.
No real orders are placed without explicit user approval.

The `screening_output_only` flag remains TRUE in all outputs.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from .position_tracker import TrackedPosition

SCHEMA_VERSION = "broker_bridge.v1"
SIMULATION_MODE = True  # Always True unless explicitly overridden with user approval
logger = logging.getLogger(__name__)


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    SIMULATED = "SIMULATED"  # simulation only


@dataclass
class Quote:
    ticker: str
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    volume: int = 0
    timestamp_utc: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp_utc:
            self.timestamp_utc = datetime.now(UTC).isoformat()

    @property
    def mid_price(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.last

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AccountInfo:
    schema_version: str = SCHEMA_VERSION
    broker: str = "PAPER"
    account_id: str = "SIMULATED"
    cash: float = 100_000.0
    buying_power: float = 100_000.0
    portfolio_value: float = 100_000.0
    currency: str = "USD"
    timestamp_utc: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp_utc:
            self.timestamp_utc = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BrokerPosition:
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    timestamp_utc: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp_utc:
            self.timestamp_utc = datetime.now(UTC).isoformat()

    @classmethod
    def from_tracked_position(cls, pos: TrackedPosition) -> BrokerPosition:
        market_value = pos.current_price * pos.quantity
        cost_basis = pos.entry_price * pos.quantity
        unrealized = market_value - cost_basis
        unrealized_pct = unrealized / cost_basis if cost_basis > 0 else 0.0
        return cls(
            symbol=pos.ticker,
            quantity=pos.quantity,
            avg_cost=pos.entry_price,
            current_price=pos.current_price,
            market_value=market_value,
            unrealized_pnl=unrealized,
            unrealized_pnl_pct=unrealized_pct,
            timestamp_utc=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrderRequest:
    """주문 요청 — 반드시 simulation mode에서 사용."""

    schema_version: str = SCHEMA_VERSION
    order_id: str = ""
    ticker: str = ""
    side: str = OrderSide.BUY.value
    order_type: str = OrderType.MARKET.value
    quantity: int = 0
    limit_price: float | None = None
    stop_price: float | None = None
    # Simulation metadata
    simulation_only: bool = True
    recommendation_source: str | None = None
    recommendation_score: float | None = None
    entry_price: float | None = None
    stop_price_plan: float | None = None
    tp2_price_plan: float | None = None
    risk_budget_pct: float | None = None
    track: str | None = None
    notes: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.order_id:
            import hashlib
            import time
            raw = f"{time.time()}{self.ticker}".encode()
            self.order_id = hashlib.sha256(raw).hexdigest()[:16]
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()
        # Force simulation_only True always
        self.simulation_only = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrderResult:
    """주문 결과 — simulation 결과를 기록."""

    schema_version: str = SCHEMA_VERSION
    order_id: str = ""
    ticker: str = ""
    side: str = ""
    status: str = OrderStatus.SIMULATED.value
    quantity: int = 0
    fill_price: float | None = None
    fill_price_effective: float | None = None
    simulation_only: bool = True
    simulation_reason: str = "PAPER_MODE: No real broker API keys configured"
    error_message: str | None = None
    created_at: str = ""
    filled_at: str | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BrokerAdapter(ABC):
    """브로커 어댑터 추상 베이스."""

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """브로커 이름."""
        ...

    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """계정 정보 조회 (simulation 또는 실계정)."""
        ...

    @abstractmethod
    def get_positions(self) -> list[BrokerPosition]:
        """현재 포지션 조회."""
        ...

    @abstractmethod
    def get_quote(self, ticker: str) -> Quote | None:
        """호가 조회."""
        ...

    @abstractmethod
    def submit_order(self, order: OrderRequest) -> OrderResult:
        """
        주문 제출 (simulation mode에서는 simulated fill만 반환).
        실계정 연동은 명시적 사용자 승인 필요.
        """
        ...

    def close(self) -> None:  # noqa: B027
        """리소스 정리."""
        pass


class PaperBroker(BrokerAdapter):
    """
    시뮬레이션 전용 브로커.
    모든 주문은 simulated fill로 기록.
    API 키 불필요.
    """

    def __init__(self, starting_cash: float = 100_000.0):
        self._starting_cash = starting_cash
        self._cash = starting_cash
        self._positions: dict[str, BrokerPosition] = {}
        self._order_log: list[OrderResult] = []

    @property
    def broker_name(self) -> str:
        return "PAPER"

    def get_account_info(self) -> AccountInfo:
        portfolio_value = sum(p.market_value for p in self._positions.values())
        total_value = self._cash + portfolio_value
        return AccountInfo(
            broker="PAPER",
            account_id="PAPER-001",
            cash=round(self._cash, 2),
            buying_power=round(self._cash * 2, 2),  # 2x margin假设
            portfolio_value=round(total_value, 2),
            currency="USD",
        )

    def get_positions(self) -> list[BrokerPosition]:
        return list(self._positions.values())

    def get_quote(self, ticker: str) -> Quote | None:
        # Paper broker: return simulated quote based on tracked positions
        pos = self._positions.get(ticker.upper())
        if pos:
            return Quote(ticker=ticker, bid=pos.current_price * 0.999, ask=pos.current_price * 1.001, last=pos.current_price, volume=0)
        return None

    def submit_order(self, order: OrderRequest) -> OrderResult:
        """시뮬레이션 주문 — 항상 simulated fill."""
        assert order.simulation_only, "PaperBroker only accepts simulation orders"

        result = OrderResult(
            order_id=order.order_id,
            ticker=order.ticker,
            side=order.side,
            status=OrderStatus.SIMULATED.value,
            quantity=order.quantity,
            fill_price=order.limit_price or order.entry_price or 0.0,
            fill_price_effective=order.limit_price or order.entry_price or 0.0,
            simulation_only=True,
            simulation_reason="PAPER_MODE: No real broker API keys configured",
            filled_at=datetime.now(UTC).isoformat(),
        )
        self._order_log.append(result)
        return result

    def order_log(self) -> list[OrderResult]:
        return list(self._order_log)


def build_order_from_recommendation(
    ticker: str,
    quantity: int,
    entry_price: float,
    stop_price: float,
    tp2_price: float,
    side: str = OrderSide.BUY.value,
    track: str | None = None,
    recommendation_score: float | None = None,
    risk_budget_pct: float | None = None,
) -> OrderRequest:
    """추천 결과를 주문 요청으로 변환."""
    return OrderRequest(
        ticker=ticker.upper(),
        side=side,
        order_type=OrderType.LIMIT.value,
        quantity=quantity,
        limit_price=entry_price,
        entry_price=entry_price,
        stop_price_plan=stop_price,
        tp2_price_plan=tp2_price,
        track=track,
        recommendation_score=recommendation_score,
        risk_budget_pct=risk_budget_pct,
        simulation_only=True,
        notes=f"Recommendation-based order. Track: {track}. Score: {recommendation_score}. Paper simulation only.",
    )


def generate_trade_plan(
    order: OrderRequest,
    account_info: AccountInfo,
    quote: Quote | None,
    output_dir: Path | str | None = None,
) -> tuple[Path, Path]:
    """
    Trade Plan 문서 생성.
    반드시 다음을 명시:
    - 본 문서는 시뮬레이션 전용
    - 실제 주문은 사용자가 직접 검토하고 승인해야 함
    - screening_output_only=True 유지
    """
    output_dir = Path(output_dir or "reports/trade_plans")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"trade_plan_{order.ticker}_{timestamp}.json"
    md_path = output_dir / f"trade_plan_{order.ticker}_{timestamp}.md"

    plan_data = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "simulation_only": True,
        "warning": "DRAFT — User review and explicit approval required before any real order",
        "order": order.to_dict(),
        "account": account_info.to_dict(),
        "quote": quote.to_dict() if quote else None,
        "approval_required": True,
        "checklist": {
            "ticker_correct": False,
            "quantity_verified": False,
            "entry_price_verified": False,
            "stop_price_acceptable": False,
            "risk_budget_acceptable": False,
            "position_size_within_limits": False,
            "user_approved": False,
        },
    }

    json_path.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8")

    entry_price = order.entry_price or 0.0
    stop_price = order.stop_price_plan or 0.0
    tp2_price = order.tp2_price_plan or 0.0
    risk_per_share = entry_price - stop_price if entry_price > 0 and stop_price > 0 else 0.0
    risk_reward = (tp2_price - entry_price) / risk_per_share if risk_per_share > 0 else 0.0

    md_lines = [
        f"# 📋 Trade Plan — {order.ticker} — {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}Z",
        "",
        "## ⚠️ SIMULATION ONLY — APPROVAL REQUIRED",
        "",
        "```",
        "This trade plan is generated for review purposes ONLY.",
        "No real order will be placed without your explicit approval.",
        "screening_output_only = True",
        "```",
        "",
        "## Order Details",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Ticker | {order.ticker} |",
        f"| Side | {order.side} |",
        f"| Order Type | {order.order_type} |",
        f"| Quantity | {order.quantity} |",
        f"| Limit Price | ${order.limit_price:.4f} |" if order.limit_price else "",
        f"| Entry Price (Plan) | ${entry_price:.4f} |",
        f"| Stop Price (Plan) | ${stop_price:.4f} |",
        f"| TP2 Price (Plan) | ${tp2_price:.4f} |",
        f"| Risk/Reward | {risk_reward:.2f}x |",
        f"| Risk/Share | ${risk_per_share:.4f} |",
        f"| Track | {order.track} |",
        f"| Recommendation Score | {order.recommendation_score} |",
        f"| Risk Budget % | {order.risk_budget_pct:.2%} |" if order.risk_budget_pct else "",
        "",
        "## Risk Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Position Value | ${entry_price * order.quantity:,.2f} |",
        f"| Risk Per Trade | ${risk_per_share * order.quantity:,.2f} |",
        f"| Account Buying Power | ${account_info.buying_power:,.2f} |",
        f"| Portfolio Value | ${account_info.portfolio_value:,.2f} |",
        f"| Position/Portfolio | {entry_price * order.quantity / account_info.portfolio_value:.1%} |",
        "",
        "## Pre-Trade Checklist",
        "",
        "- [ ] 티커 일치 확인",
        "- [ ] 수량 재확인",
        "- [ ] 진입가 acceptable 확인",
        "- [ ] 손절가 acceptable 확인",
        "- [ ] 리스크 예산 이내인지 확인",
        "- [ ] 포지션 크기 적절한지 확인",
        "- [ ] **본인만** 'user_approved=True'로 변경 후 실제 주문",
        "",
        "## Quote",
        "",
    ]

    if quote:
        md_lines.extend([
            f"| Bid | ${quote.bid:.4f} |",
            f"| Ask | ${quote.ask:.4f} |",
            f"| Last | ${quote.last:.4f} |",
            f"| Mid | ${quote.mid_price:.4f} |",
        ])
    else:
        md_lines.append("_Quote not available_")

    md_lines.extend(["", "---", f"*Generated: {datetime.now(UTC).isoformat()}Z | Broker Bridge v{SCHEMA_VERSION} | simulation_only=True*"])
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path, md_path


def log_order_result(result: OrderResult, output_dir: Path | str = Path("reports/broker_bridge")) -> Path:
    """주문 결과 로그 저장."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "order_log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
    return log_path


# ---------------------------------------------------------------------------
# Phase 8 — backward-compat import shim
#
# Code that imports from broker_bridge continues to work unchanged.
# New code should prefer:  from stock_rtx4060.broker import get_broker
# ---------------------------------------------------------------------------

def get_broker(name: str = "paper", **kwargs):
    """Factory — see broker/__init__.py for full documentation."""
    from .broker import get_broker as _get_broker  # noqa: PLC0415
    return _get_broker(name, **kwargs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Broker Bridge — Stage 5 (Paper/Simulation)")
    parser.add_argument("--broker", type=str, default="paper", choices=["paper"], help="Broker type (paper only in simulation)")
    parser.add_argument("--ticker", type=str, default="AAPL", help="Ticker")
    parser.add_argument("--quantity", type=int, default=10, help="Quantity")
    parser.add_argument("--entry-price", type=float, default=185.0, help="Entry price")
    parser.add_argument("--stop-price", type=float, default=177.0, help="Stop price")
    parser.add_argument("--tp2-price", type=float, default=203.5, help="TP2 price")
    parser.add_argument("--track", type=str, default="S", help="Track: S or L")
    parser.add_argument("--score", type=float, default=78.5, help="Recommendation score")
    parser.add_argument("--output-dir", type=str, default="reports/broker_bridge", help="Output directory")
    args = parser.parse()

    broker = PaperBroker(starting_cash=100_000.0)
    account = broker.get_account_info()
    print(f"Broker: {broker.broker_name} | Cash: ${account.cash:,.2f} | Portfolio: ${account.portfolio_value:,.2f}")

    order = build_order_from_recommendation(
        ticker=args.ticker,
        quantity=args.quantity,
        entry_price=args.entry_price,
        stop_price=args.stop_price,
        tp2_price=args.tp2_price,
        track=args.track,
        recommendation_score=args.score,
    )

    quote = Quote(ticker=args.ticker, bid=args.entry_price * 0.999, ask=args.entry_price * 1.001, last=args.entry_price)
    json_path, md_path = generate_trade_plan(order, account, quote, output_dir=args.output_dir)

    result = broker.submit_order(order)
    log_path = log_order_result(result, output_dir=args.output_dir)

    print(f"\nOrder Result: {result.status} | Fill: ${result.fill_price:.4f}")
    print(f"Simulation: {result.simulation_reason}")
    print(f"\nTrade Plan: {md_path}")
    print(f"Order Log: {log_path}")
