"""Tests for ``stock_rtx4060.portfolio.rebalance``."""

from __future__ import annotations

from stock_rtx4060.portfolio import TradeOrder, TransactionCosts, compute_target_weights


def test_zero_trades_when_already_at_target():
    candidates = [
        {"ticker": "AAA", "score": 80.0, "target_weight": 0.5},
        {"ticker": "BBB", "score": 70.0, "target_weight": 0.5},
    ]
    current = {"AAA": 5_000.0, "BBB": 5_000.0}
    orders = compute_target_weights(candidates, current, portfolio_value=10_000.0, min_trade_value=10.0)
    assert orders == []


def test_min_trade_value_filters_tiny_rebalance():
    candidates = [{"ticker": "AAA", "score": 70.0, "target_weight": 1.0}]
    current = {"AAA": 9_950.0}
    orders = compute_target_weights(candidates, current, portfolio_value=10_000.0, min_trade_value=100.0)
    # 50 dollar rebalance is below the 100 min — no order.
    assert orders == []


def test_buy_order_for_underweight():
    candidates = [
        {"ticker": "AAA", "target_weight": 0.6},
        {"ticker": "BBB", "target_weight": 0.4},
    ]
    current = {"AAA": 0.0, "BBB": 0.0}
    orders = compute_target_weights(candidates, current, portfolio_value=10_000.0, min_trade_value=10.0)
    by_ticker = {o.ticker: o for o in orders}
    assert by_ticker["AAA"].side == "BUY"
    assert by_ticker["AAA"].target_value == 6_000.0
    assert by_ticker["BBB"].side == "BUY"


def test_sell_order_for_dropped_holding():
    candidates = [{"ticker": "AAA", "target_weight": 1.0}]
    current = {"AAA": 5_000.0, "OLD": 3_000.0}
    orders = compute_target_weights(candidates, current, portfolio_value=8_000.0, min_trade_value=10.0)
    sells = [o for o in orders if o.side == "SELL"]
    sell_tickers = [o.ticker for o in sells]
    assert "OLD" in sell_tickers


def test_quantity_uses_price_when_present():
    candidates = [{"ticker": "AAA", "target_weight": 1.0, "price": 50.0}]
    current = {"AAA": 0.0}
    orders = compute_target_weights(candidates, current, portfolio_value=1_000.0, min_trade_value=10.0)
    assert len(orders) == 1
    assert orders[0].quantity == 1_000.0 / 50.0


def test_costs_floor_increases_threshold():
    # Without costs: 200 dollar rebalance is above 50 min and would trade.
    candidates = [{"ticker": "AAA", "target_weight": 1.0}]
    current = {"AAA": 9_800.0}
    orders_no_costs = compute_target_weights(candidates, current, 10_000.0, min_trade_value=50.0)
    # With high-cost model the floor should suppress the trade
    high_cost = TransactionCosts(commission_bps=300.0, spread_bps=300.0)
    orders_with_costs = compute_target_weights(candidates, current, 10_000.0, costs=high_cost, min_trade_value=50.0)
    assert len(orders_no_costs) == 1
    assert len(orders_with_costs) == 0


def test_zero_portfolio_value_returns_empty():
    candidates = [{"ticker": "AAA", "target_weight": 1.0}]
    orders = compute_target_weights(candidates, {}, portfolio_value=0.0)
    assert orders == []


def test_trade_order_to_dict():
    order = TradeOrder(ticker="AAA", side="BUY", quantity=12.345678, target_value=1234.5678)
    payload = order.to_dict()
    assert payload["ticker"] == "AAA"
    assert payload["side"] == "BUY"
    assert payload["quantity"] == 12.345678
    assert payload["target_value"] == 1234.57
