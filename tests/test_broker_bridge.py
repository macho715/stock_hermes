"""Tests for broker_bridge module (Stage 5)."""

from __future__ import annotations

import json

from stock_rtx4060.broker_bridge import (
    SCHEMA_VERSION,
    SIMULATION_MODE,
    AccountInfo,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    PaperBroker,
    Quote,
    build_order_from_recommendation,
    generate_trade_plan,
    log_order_result,
)


class TestQuote:
    """Quote 테스트."""

    def test_mid_price_with_bid_ask(self):
        q = Quote(ticker="AAPL", bid=184.0, ask=186.0, last=185.0)
        assert q.mid_price == 185.0

    def test_mid_price_last_only(self):
        q = Quote(ticker="AAPL", last=185.0)
        assert q.mid_price == 185.0


class TestAccountInfo:
    """AccountInfo 테스트."""

    def test_to_dict(self):
        d = AccountInfo().to_dict()
        assert d["broker"] == "PAPER"
        assert d["schema_version"] == SCHEMA_VERSION

    def test_account_defaults(self):
        info = AccountInfo()
        assert info.cash == 100_000.0
        assert info.currency == "USD"


class TestOrderRequest:
    """OrderRequest 테스트."""

    def test_simulation_only_flag(self):
        order = OrderRequest(ticker="AAPL", quantity=10)
        assert order.simulation_only is True
        d = order.to_dict()
        assert d["simulation_only"] is True

    def test_order_id_generated(self):
        order = OrderRequest(ticker="AAPL", quantity=10)
        assert order.order_id != ""
        assert len(order.order_id) == 16


class TestPaperBroker:
    """PaperBroker 시뮬레이션 테스트."""

    def test_broker_name(self):
        broker = PaperBroker()
        assert broker.broker_name == "PAPER"

    def test_get_account_info(self):
        broker = PaperBroker(starting_cash=50000.0)
        info = broker.get_account_info()
        assert info.cash == 50000.0
        assert info.portfolio_value == 50000.0

    def test_get_positions_empty(self):
        broker = PaperBroker()
        assert broker.get_positions() == []

    def test_submit_order_simulated(self):
        broker = PaperBroker(starting_cash=100000.0)
        order = OrderRequest(ticker="AAPL", side=OrderSide.BUY.value, quantity=10, limit_price=185.0)
        result = broker.submit_order(order)
        assert result.status == OrderStatus.SIMULATED.value
        assert result.simulation_only is True
        assert "PAPER_MODE" in result.simulation_reason

    def test_order_log(self):
        broker = PaperBroker()
        order = OrderRequest(ticker="AAPL", quantity=10)
        broker.submit_order(order)
        log = broker.order_log()
        assert len(log) == 1
        assert log[0].ticker == "AAPL"


class TestBuildOrderFromRecommendation:
    """주문 변환 테스트."""

    def test_build_order_fields(self):
        order = build_order_from_recommendation(
            ticker="AAPL",
            quantity=10,
            entry_price=185.0,
            stop_price=177.0,
            tp2_price=203.5,
            track="S",
            recommendation_score=82.0,
        )
        assert order.ticker == "AAPL"
        assert order.quantity == 10
        assert order.entry_price == 185.0
        assert order.stop_price_plan == 177.0
        assert order.tp2_price_plan == 203.5
        assert order.track == "S"
        assert order.recommendation_score == 82.0
        assert order.simulation_only is True


class TestGenerateTradePlan:
    """Trade Plan 생성 테스트."""

    def test_trade_plan_contains_simulation_warning(self, tmp_path):
        order = OrderRequest(ticker="AAPL", side=OrderSide.BUY.value, quantity=10, limit_price=185.0)
        account = AccountInfo()
        quote = Quote(ticker="AAPL", bid=184.0, ask=186.0, last=185.0)
        json_path, md_path = generate_trade_plan(order, account, quote, output_dir=tmp_path)

        assert json_path.exists()
        assert md_path.exists()

        md = md_path.read_text(encoding="utf-8")
        assert "SIMULATION ONLY" in md
        assert "APPROVAL REQUIRED" in md
        assert "AAPL" in md
        assert "screening_output_only" in md.lower()

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["simulation_only"] is True
        assert data["approval_required"] is True


class TestLogOrderResult:
    """주문 로그 테스트."""

    def test_log_writes_jsonl(self, tmp_path):
        result = OrderResult(
            order_id="test123",
            ticker="AAPL",
            side=OrderSide.BUY.value,
            status=OrderStatus.SIMULATED.value,
            quantity=10,
        )
        log_path = log_order_result(result, output_dir=tmp_path)
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert "AAPL" in lines[0]


class TestSimulationMode:
    """simulation mode 상수 테스트."""

    def test_simulation_mode_true(self):
        assert SIMULATION_MODE is True