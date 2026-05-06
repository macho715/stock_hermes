"""
Portfolio Analytics — 리스크 집계 및 포트폴리오 분석

Stage 3 of 5-stage investment system upgrade.
읽기 전용. 주문 실행 없음.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .position_tracker import PortfolioSnapshot, TrackedPosition, PositionStatus

SCHEMA_VERSION = "portfolio_analytics.v1"


@dataclass
class PortfolioAnalytics:
    """포트폴리오 분석 결과."""

    schema_version: str = SCHEMA_VERSION
    generated_at: str = ""
    capital: float = 100_000.0

    # Exposure
    total_position_value: float = 0.0
    total_exposure_pct: float = 0.0
    track_s_exposure_pct: float = 0.0
    track_l_exposure_pct: float = 0.0
    cash_remaining_pct: float = 0.0
    max_position_exposure_pct: float = 0.0

    # Concentration
    concentration_risk_pct: float = 0.0
    concentrated_sector: str | None = None

    # Risk
    beta_to_spy: float = 1.0
    var_1d_95_pct: float = 0.0

    # Drawdown
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    days_in_drawdown: int = 0

    # Rebalance
    rebalance_needed: bool = False
    rebalance_suggestions: list[str] = field(default_factory=list)

    # Sector
    sector_weights: dict[str, float] = field(default_factory=dict)

    # Performance
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    monthly_pnl_pct: float = 0.0
    unrealized_pnl_abs: float = 0.0
    realized_pnl_abs: float = 0.0

    # Exposure limits
    max_total_exposure_pct: float = 0.60
    max_track_s_exposure_pct: float = 0.20
    max_track_l_exposure_pct: float = 0.75
    max_sector_concentration_pct: float = 0.30

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_snapshot(cls, snapshot: PortfolioSnapshot, capital: float = 100_000.0) -> "PortfolioAnalytics":
        analytics = cls(capital=capital)
        analytics.total_position_value = snapshot.total_position_value

        analytics.total_exposure_pct = snapshot.total_position_value / capital if capital > 0 else 0.0
        analytics.track_s_exposure_pct = snapshot.track_s_value / capital if capital > 0 else 0.0
        analytics.track_l_exposure_pct = snapshot.track_l_value / capital if capital > 0 else 0.0
        analytics.cash_remaining_pct = 1.0 - analytics.total_exposure_pct
        analytics.unrealized_pnl_abs = snapshot.total_unrealized_pnl_abs
        analytics.realized_pnl_abs = snapshot.realized_pnl_abs

        # Max single-position exposure
        open_positions = [p for p in snapshot.positions if _is_open(p.get("status", ""))]
        if open_positions and capital > 0:
            position_values = [p["current_price"] * p["quantity"] for p in open_positions]
            analytics.max_position_exposure_pct = max(position_values) / capital if position_values else 0.0

        # Sector analysis
        analytics.sector_weights = _compute_sector_weights(open_positions)
        if analytics.sector_weights:
            max_sector, max_weight = max(analytics.sector_weights.items(), key=lambda x: x[1])
            analytics.concentration_risk_pct = max_weight
            if max_weight > analytics.max_sector_concentration_pct:
                analytics.concentrated_sector = max_sector

        # Beta estimation (simplified — use equal-weight of track betas)
        analytics.beta_to_spy = _estimate_portfolio_beta(open_positions)

        # VaR (simplified: 1.65 * avg 20d hist_vol for open positions)
        analytics.var_1d_95_pct = _compute_var_1d_95(open_positions)

        # Rebalance check
        suggestions: list[str] = []
        if analytics.track_s_exposure_pct > analytics.max_track_s_exposure_pct:
            suggestions.append(f"Track-S 노출 초과: {analytics.track_s_exposure_pct:.1%} > {analytics.max_track_s_exposure_pct:.1%}")
        if analytics.track_l_exposure_pct > analytics.max_track_l_exposure_pct:
            suggestions.append(f"Track-L 노출 초과: {analytics.track_l_exposure_pct:.1%} > {analytics.max_track_l_exposure_pct:.1%}")
        if analytics.total_exposure_pct > analytics.max_total_exposure_pct:
            suggestions.append(f"총 노출 초과: {analytics.total_exposure_pct:.1%} > {analytics.max_total_exposure_pct:.1%}")
        if analytics.concentrated_sector:
            suggestions.append(f"Sector 집중 초과: {analytics.concentrated_sector} = {analytics.concentration_risk_pct:.1%}")
        if analytics.cash_remaining_pct < 0.05:
            suggestions.append(f"현금 잔액 부족: {analytics.cash_remaining_pct:.1%} < 5%")
        analytics.rebalance_needed = len(suggestions) > 0
        analytics.rebalance_suggestions = suggestions

        # Drawdown: based on peak-to-current unrealized pnl
        # We track peak_unrealized_pnl in the snapshot via max_favorable_move
        peak_value = _compute_peak_value(open_positions)
        if peak_value > 0:
            current_value = snapshot.total_position_value
            analytics.current_drawdown_pct = (peak_value - current_value) / peak_value
            # Simplified days-in-drawdown: count open positions that have adverse moves
            analytics.days_in_drawdown = _estimate_days_in_drawdown(open_positions)

        analytics.max_drawdown_pct = max(analytics.current_drawdown_pct, analytics.max_drawdown_pct)

        return analytics

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_open(status: str) -> bool:
    return status in (
        PositionStatus.OPEN.value,
        PositionStatus.STOP_APPROACHING.value,
        PositionStatus.TP_APPROACHING.value,
    )


def _compute_sector_weights(positions: list[dict]) -> dict[str, float]:
    """추정 sector权重 — yfinance info에서 sector 정보 조회."""
    sector_map: dict[str, float] = {}
    total_value = 0.0

    for p in positions:
        value = p.get("current_price", 0.0) * p.get("quantity", 0)
        if value <= 0:
            continue
        total_value += value
        # Estimate sector from ticker (simplified — in production, query yfinance info)
        sector = _estimate_sector(p.get("ticker", ""))
        sector_map[sector] = sector_map.get(sector, 0.0) + value

    if total_value <= 0:
        return {}
    return {sector: weight / total_value for sector, weight in sector_map.items()}


_SECTOR_ESTIMATES: dict[str, str] = {
    # Tech
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "AMD": "Technology",
    "AVGO": "Technology", "GOOGL": "Technology", "AMZN": "Technology", "META": "Technology",
    "TSLA": "Consumer Cyclical", "NFLX": "Communication Services",
    # Finance
    "JPM": "Financial Services", "BAC": "Financial Services", "GS": "Financial Services",
    # Healthcare
    "LLY": "Healthcare", "UNH": "Healthcare", "JNJ": "Healthcare",
    # Energy
    "XOM": "Energy", "CVX": "Energy",
    # Industrial
    "CAT": "Industrials", "BA": "Industrials",
    # Consumer
    "COST": "Consumer Defensive", "WMT": "Consumer Defensive",
    # Gold
    "GLD": "Commodities",
    # Broad
    "QQQ": "Technology", "SPY": "Broad Market", "XLK": "Technology", "XLE": "Energy",
}


def _estimate_sector(ticker: str) -> str:
    return _SECTOR_ESTIMATES.get(ticker.upper(), "Other")


def _estimate_portfolio_beta(positions: list[dict]) -> float:
    """간략한 포트폴리오 beta 추정 — sector β 사용."""
    sector_betas: dict[str, float] = {
        "Technology": 1.30, "Consumer Cyclical": 1.25, "Communication Services": 1.10,
        "Financial Services": 1.15, "Healthcare": 0.70, "Energy": 1.05,
        "Industrials": 1.10, "Consumer Defensive": 0.55, "Commodities": 0.15,
        "Broad Market": 1.00, "Other": 1.00,
    }
    total_value = 0.0
    weighted_beta = 0.0
    for p in positions:
        value = p.get("current_price", 0.0) * p.get("quantity", 0)
        if value <= 0:
            continue
        total_value += value
        sector = _estimate_sector(p.get("ticker", ""))
        beta = sector_betas.get(sector, 1.0)
        weighted_beta += value * beta
    return weighted_beta / total_value if total_value > 0 else 1.0


def _compute_var_1d_95(positions: list[dict]) -> float:
    """1-day 95% VaR — simplified: 1.65 * avg(hist_vol_20)."""
    if not positions:
        return 0.0
    # Use hist_vol_20 from position if available, else default
    vols = []
    for p in positions:
        vol = p.get("hist_vol_20", 0.02)  # default 2% daily vol
        vols.append(float(vol))
    avg_vol = sum(vols) / len(vols) if vols else 0.02
    return 1.65 * avg_vol


def _compute_peak_value(positions: list[dict]) -> float:
    """계산된 peak portfolio value (using max_favorable_move)."""
    total = 0.0
    for p in positions:
        entry_price = p.get("entry_price", 0.0)
        quantity = p.get("quantity", 0)
        max_fav_pct = p.get("max_favorable_move_pct", 0.0)
        if entry_price <= 0 or quantity <= 0:
            continue
        # Peak value = entry * (1 + max_favorable_move) * quantity
        peak_price = entry_price * (1.0 + max_fav_pct)
        total += peak_price * quantity
    return total


def _estimate_days_in_drawdown(positions: list[dict]) -> int:
    """추정: adverse move > 0이면 drawdown 중."""
    for p in positions:
        mame_pct = p.get("max_adverse_move_pct", 0.0)
        if mame_pct > 0.01:  # >1% adverse
            return 1  # at least 1 day
    return 0


def analyze_portfolio(snapshot: PortfolioSnapshot, capital: float = 100_000.0) -> PortfolioAnalytics:
    """주 포트폴리오 분석 엔트리포인트."""
    return PortfolioAnalytics.from_snapshot(snapshot, capital=capital)


def save_analytics_report(analytics: PortfolioAnalytics, output_dir: str | Path) -> tuple[Path, Path]:
    """분석 결과를 JSON + Markdown으로 저장."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"portfolio_analytics_{timestamp}.json"
    md_path = output_dir / f"portfolio_analytics_{timestamp}.md"

    json_path.write_text(json.dumps(analytics.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    a = analytics
    md_lines = [
        f"# Portfolio Analytics — {a.generated_at[:19]}Z",
        "",
        "## Exposure",
        "",
        f"| Metric | Value | Limit | Status |",
        f"|--------|-------|-------|--------|",
        f"| Total Exposure | {a.total_exposure_pct:.1%} | {a.max_total_exposure_pct:.1%} | {'✅' if a.total_exposure_pct <= a.max_total_exposure_pct else '🚨'} |",
        f"| Track-S Exposure | {a.track_s_exposure_pct:.1%} | {a.max_track_s_exposure_pct:.1%} | {'✅' if a.track_s_exposure_pct <= a.max_track_s_exposure_pct else '🚨'} |",
        f"| Track-L Exposure | {a.track_l_exposure_pct:.1%} | {a.max_track_l_exposure_pct:.1%} | {'✅' if a.track_l_exposure_pct <= a.max_track_l_exposure_pct else '🚨'} |",
        f"| Cash Remaining | {a.cash_remaining_pct:.1%} | min 5% | {'✅' if a.cash_remaining_pct >= 0.05 else '🚨'} |",
        f"| Max Single Position | {a.max_position_exposure_pct:.1%} | — | {'⚠️' if a.max_position_exposure_pct > 0.15 else '✅'} |",
        "",
        "## Risk",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Portfolio Beta (vs SPY) | {a.beta_to_spy:.2f} |",
        f"| 1-Day 95% VaR | {a.var_1d_95_pct:.2%} |",
        f"| Current Drawdown | {a.current_drawdown_pct:.2%} |",
        f"| Max Drawdown | {a.max_drawdown_pct:.2%} |",
        f"| Days in Drawdown | {a.days_in_drawdown} |",
        "",
        "## Sector Distribution",
        "",
    ]

    for sector, weight in sorted(a.sector_weights.items(), key=lambda x: -x[1]):
        bar = "█" * int(weight * 40)
        emoji = "🚨" if weight > a.max_sector_concentration_pct else "  "
        md_lines.append(f"{emoji} {sector}: {weight:.1%} {bar}")

    if a.concentrated_sector:
        md_lines.append(f"\n⚠️ **Sector Concentration Alert:** {a.concentrated_sector} = {a.concentration_risk_pct:.1%} (max {a.max_sector_concentration_pct:.1%})")

    md_lines.extend(["", "## P&L", "", f"| Metric | Value |", f"|--------|-------|", f"| Unrealized P&L | {a.unrealized_pnl_abs:+,.2f} |", f"| Realized P&L | {a.realized_pnl_abs:+,.2f} |"])

    if a.rebalance_needed:
        md_lines.extend(["", "## ⚠️ Rebalance Required", ""])
        for suggestion in a.rebalance_suggestions:
            md_lines.append(f"- {suggestion}")
    else:
        md_lines.extend(["", "## ✅ Rebalance OK — All within limits", ""])

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    import argparse
    import tempfile
    from datetime import datetime, timezone
    from stock_rtx4060.position_tracker import TrackedPosition, PortfolioSnapshot, save_portfolio_snapshot

    parser = argparse.ArgumentParser(description="Portfolio Analytics — Stage 3")
    parser.add_argument("--portfolio-json", type=str, default=None, help="Load from portfolio snapshot JSON")
    parser.add_argument("--capital", type=float, default=100_000.0, help="Total capital")
    parser.add_argument("--output-dir", type=str, default="reports/portfolio_analytics", help="Output directory")
    args = parser.parse_args()

    if args.portfolio_json:
        import json
        from pathlib import Path
        data = json.loads(Path(args.portfolio_json).read_text(encoding="utf-8"))
        positions = [TrackedPosition(**p) for p in data.get("positions", [])]
        snapshot = PortfolioSnapshot.from_positions(positions)
    else:
        positions = [
            TrackedPosition(ticker="AAPL", track="S", entry_date="2026-05-01", entry_price=185.0, quantity=10, stop=177.0, tp1=194.0, tp2=203.5),
            TrackedPosition(ticker="MSFT", track="L", entry_date="2026-05-01", entry_price=415.0, quantity=5, stop=375.0, tp1=450.0, tp2=498.0),
        ]
        for i, p in enumerate(positions):
            current = p.entry_price * (1 + (i + 1) * 0.01)  # slight gain
            p.mark_open(current_price=current, timestamp_utc=datetime.now(timezone.utc).isoformat())
        snapshot = PortfolioSnapshot.from_positions(positions)

    analytics = analyze_portfolio(snapshot, capital=args.capital)
    json_path, md_path = save_analytics_report(analytics, args.output_dir)
    print(f"Analytics ({analytics.total_exposure_pct:.1%} exposure, β={analytics.beta_to_spy:.2f}, VaR={analytics.var_1d_95_pct:.2%}):")
    print(f"  Sector: {analytics.sector_weights}")
    if analytics.rebalance_needed:
        for s in analytics.rebalance_suggestions:
            print(f"  ⚠️ {s}")
    else:
        print(f"  ✅ Rebalance OK")
    print(f"\nReports: {json_path}")
    print(f"         {md_path}")