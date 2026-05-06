import json
from pathlib import Path

from stock_rtx4060.paper_trading import (
    PaperTradingConfig,
    PaperTradingEngine,
    PaperTradingSignal,
    calculate_promotion_drawdown,
    load_paper_status,
    rebuild_daily_report,
)


def _bars(days=5, start=100.0):
    rows = []
    for index in range(days):
        close = start + index
        rows.append(
            {
                "date": f"2026-05-{index + 1:02d}",
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "adjusted_close": close,
                "volume": 1_000_000,
                "provider": "pykrx",
            }
        )
    return rows


def _signal(**overrides):
    payload = {
        "ticker": "AAPL",
        "score": 67.0,
        "signal": "BUY",
        "model_auc": 0.61,
        "model_accuracy": 0.56,
        "oof_coverage": 0.86,
        "warning": None,
    }
    payload.update(overrides)
    return PaperTradingSignal(**payload)


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_paper_trading_rejects_weak_model_and_krx(tmp_path):
    engine = PaperTradingEngine(PaperTradingConfig(output_root=tmp_path))

    weak = engine.evaluate_signal(_signal(model_auc=0.49), _bars())
    krx = engine.evaluate_signal(_signal(ticker="005930.KS"), _bars())

    assert weak.status == "REJECTED"
    assert weak.reason == "weak_model_quality"
    assert weak.paper_trading_only is True
    assert krx.status == "REJECTED"
    assert krx.reason == "market_not_enabled_phase1"


def test_paper_trading_blocks_warning_state_hold_and_missing_evidence(tmp_path):
    engine = PaperTradingEngine(PaperTradingConfig(output_root=tmp_path))

    warning = engine.evaluate_signal(_signal(warning="모델 품질 낮음: 검토 전용"), _bars())
    hold = engine.evaluate_signal(_signal(signal="HOLD"), _bars())
    missing = engine.evaluate_signal(_signal(model_auc=None), _bars())

    assert warning.status == "REJECTED"
    assert warning.reason == "weak_model_quality"
    assert hold.status == "REJECTED"
    assert hold.reason == "hold_not_tradable"
    assert missing.status == "REJECTED"
    assert missing.reason == "model_evidence_missing"


def test_paper_trading_rejects_invalid_and_stale_ohlcv(tmp_path):
    engine = PaperTradingEngine(PaperTradingConfig(output_root=tmp_path))
    invalid_bars = _bars()
    invalid_bars[-1]["close"] = -1.0
    stale_bars = _bars()
    for index, row in enumerate(stale_bars):
        row["date"] = f"2000-01-{index + 1:02d}"

    invalid = engine.evaluate_signal(_signal(), invalid_bars)
    stale = engine.evaluate_signal(_signal(), stale_bars)

    assert invalid.status == "REJECTED"
    assert invalid.reason == "ohlcv_invalid"
    assert stale.status == "REJECTED"
    assert stale.reason == "ohlcv_stale"


def test_paper_trading_rejects_split_uncertainty(tmp_path):
    engine = PaperTradingEngine(PaperTradingConfig(output_root=tmp_path))
    bars = _bars()
    bars[-1]["open"] = 140.0
    bars[-1]["close"] = 141.0
    bars[-1]["adjusted_close"] = 104.0

    decision = engine.evaluate_signal(_signal(), bars)

    assert decision.status == "REJECTED"
    assert decision.reason == "split_dividend_uncertainty"


def test_paper_trading_run_writes_outputs_and_is_idempotent(tmp_path):
    config = PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05")
    engine = PaperTradingEngine(config)

    first = engine.run([_signal()], {"AAPL": _bars(6)})
    second = engine.run([_signal()], {"AAPL": _bars(6)})

    assert first["run_id"] == second["run_id"]
    run_dir = Path(first["run_dir"])
    assert (run_dir / "paper_config.json").exists()
    assert (run_dir / "signals.jsonl").exists()
    assert (run_dir / "orders.jsonl").exists()
    assert (run_dir / "fills.jsonl").exists()
    assert (run_dir / "positions.jsonl").exists()
    assert (run_dir / "equity_curve.csv").exists()
    assert (run_dir / "daily_report.md").exists()

    orders = _read_jsonl(run_dir / "orders.jsonl")
    fills = _read_jsonl(run_dir / "fills.jsonl")
    assert len(orders) == 1
    assert len(fills) == 1
    assert orders[0]["paper_trading_only"] is True
    assert fills[0]["paper_trading_only"] is True

    status = load_paper_status(tmp_path)
    assert status["status"] == "READY"
    assert status["latest_run"]["run_id"] == first["run_id"]
    assert status["positions"]
    assert status["equity_curve"]


def test_paper_trading_rejects_duplicate_and_too_small_orders(tmp_path):
    duplicate = PaperTradingEngine(PaperTradingConfig(output_root=tmp_path / "dup", run_date="2026-05-05"))
    duplicate_status = duplicate.run([_signal(), _signal()], {"AAPL": _bars(6)})
    duplicate_dir = Path(duplicate_status["run_dir"])
    duplicate_signals = _read_jsonl(duplicate_dir / "signals.jsonl")
    duplicate_orders = _read_jsonl(duplicate_dir / "orders.jsonl")

    small = PaperTradingEngine(PaperTradingConfig(output_root=tmp_path / "small", run_date="2026-05-05", starting_cash=1_000.0))
    small_status = small.run([_signal(ticker="MSFT")], {"MSFT": _bars(6, start=2_000.0)})
    small_dir = Path(small_status["run_dir"])
    small_signals = _read_jsonl(small_dir / "signals.jsonl")
    small_orders = _read_jsonl(small_dir / "orders.jsonl")

    assert len(duplicate_orders) == 1
    assert any(row["reason"] == "duplicate_open_order" for row in duplicate_signals)
    assert small_orders == []
    assert any(row["reason"] == "position_size_below_one_share" for row in small_signals)


def test_paper_trading_records_mixed_universe_rejection(tmp_path):
    engine = PaperTradingEngine(PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05"))
    status = engine.run(
        [_signal(ticker="AAPL"), _signal(ticker="005930.KS"), _signal(ticker="SPY")],
        {"AAPL": _bars(6), "005930.KS": _bars(6), "SPY": _bars(6)},
    )
    run_dir = Path(status["run_dir"])
    signals = _read_jsonl(run_dir / "signals.jsonl")
    orders = _read_jsonl(run_dir / "orders.jsonl")

    assert {order["ticker"] for order in orders} == {"AAPL", "SPY"}
    assert any(row["ticker"] == "005930.KS" and row["reason"] == "market_not_enabled_phase1" for row in signals)


def test_krx_pilot_enabled_accepts_valid_krx_signal_and_partitions_output(tmp_path):
    engine = PaperTradingEngine(
        PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05", market="KRX", phase1_us_only=False)
    )
    status = engine.run([_signal(ticker="005930.KS")], {"005930.KS": _bars(6)})
    run_dir = Path(status["run_dir"])
    config = json.loads((run_dir / "paper_config.json").read_text(encoding="utf-8"))
    signals = _read_jsonl(run_dir / "signals.jsonl")
    orders = _read_jsonl(run_dir / "orders.jsonl")
    fills = _read_jsonl(run_dir / "fills.jsonl")
    positions = _read_jsonl(run_dir / "positions.jsonl")

    assert run_dir.parent.name == "krx_runs"
    assert config["market"] == "KRX"
    assert config["currency"] == "KRW"
    assert config["timezone"] == "Asia/Seoul"
    assert config["starting_cash"] == 10_000_000.0
    assert config["max_position_pct"] == 0.10
    assert signals[0]["status"] == "ACCEPTED"
    assert signals[0]["market"] == "KRX"
    assert orders[0]["market"] == "KRX"
    assert fills[0]["currency"] == "KRW"
    assert fills[0]["paper_trading_only"] is True
    assert positions[0]["paper_trading_only"] is True


def test_krx_pilot_calendar_moves_holiday_to_next_session(tmp_path):
    engine = PaperTradingEngine(
        PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05", market="KRX", phase1_us_only=False)
    )
    bars = _bars(1)
    bars[0]["date"] = "2026-05-05"

    status = engine.run([_signal(ticker="005930.KS")], {"005930.KS": bars})
    fills = _read_jsonl(Path(status["run_dir"]) / "fills.jsonl")

    assert fills[0]["fill_date"] == "2026-05-06"
    assert fills[0]["timezone"] == "Asia/Seoul"


def test_krx_pilot_uses_next_eligible_session_open_when_available(tmp_path):
    engine = PaperTradingEngine(
        PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05", market="KRX", phase1_us_only=False, slippage_pct=0.0)
    )
    bars = _bars(2)
    bars[0]["date"] = "2026-05-05"
    bars[0]["open"] = 100.0
    bars[0]["close"] = 100.0
    bars[0]["adjusted_close"] = 100.0
    bars[1]["date"] = "2026-05-06"
    bars[1]["open"] = 115.0
    bars[1]["high"] = 116.0
    bars[1]["low"] = 114.0
    bars[1]["close"] = 115.0
    bars[1]["adjusted_close"] = 115.0

    status = engine.run([_signal(ticker="005930.KS")], {"005930.KS": bars})
    fills = _read_jsonl(Path(status["run_dir"]) / "fills.jsonl")

    assert fills[0]["fill_date"] == "2026-05-06"
    assert fills[0]["fill_price"] == 115.0


def test_krx_pilot_calendar_fails_closed_when_fixture_range_missing(tmp_path):
    engine = PaperTradingEngine(
        PaperTradingConfig(output_root=tmp_path, run_date="2027-01-02", market="KRX", phase1_us_only=False)
    )
    bars = _bars(1)
    bars[0]["date"] = "2027-01-02"

    decision = engine.evaluate_signal(_signal(ticker="005930.KS"), bars)

    assert decision.status == "REJECTED"
    assert decision.reason == "krx_calendar_range_missing"
    assert decision.market == "KRX"
    assert decision.paper_trading_only is True


def test_krx_pilot_rejects_unapproved_provider_and_missing_provider_fields(tmp_path):
    engine = PaperTradingEngine(
        PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05", market="KRX", phase1_us_only=False)
    )
    unapproved = _bars(6)
    unapproved[-1]["provider"] = "yfinance"
    missing_field = _bars(6)
    missing_field[-1].pop("provider")

    bad_provider = engine.evaluate_signal(_signal(ticker="005930.KS"), unapproved)
    missing = engine.evaluate_signal(_signal(ticker="000660.KS"), missing_field)

    assert bad_provider.status == "REJECTED"
    assert bad_provider.reason == "krx_provider_not_approved"
    assert missing.status == "REJECTED"
    assert missing.reason == "krx_provider_field_missing"


def test_krx_pilot_rejects_stale_and_adjusted_raw_mismatch(tmp_path):
    engine = PaperTradingEngine(
        PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05", market="KRX", phase1_us_only=False)
    )
    stale_bars = _bars(6)
    for index, row in enumerate(stale_bars):
        row["date"] = f"2000-01-{index + 1:02d}"
    mismatch_bars = _bars(6)
    mismatch_bars[-1]["open"] = 140.0
    mismatch_bars[-1]["high"] = 142.0
    mismatch_bars[-1]["low"] = 139.0
    mismatch_bars[-1]["close"] = 141.0
    mismatch_bars[-1]["adjusted_close"] = 104.0

    stale = engine.evaluate_signal(_signal(ticker="005930.KS"), stale_bars)
    mismatch = engine.evaluate_signal(_signal(ticker="000660.KS"), mismatch_bars)

    assert stale.status == "REJECTED"
    assert stale.reason == "ohlcv_stale"
    assert mismatch.status == "REJECTED"
    assert mismatch.reason == "split_dividend_uncertainty"


def test_krx_pilot_marks_missing_benchmark_not_promotable_and_records_default_universe(tmp_path):
    engine = PaperTradingEngine(
        PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05", market="KRX", phase1_us_only=False)
    )
    status = engine.run([_signal(ticker="005930.KS")], {"005930.KS": _bars(6)})
    run_dir = Path(status["run_dir"])
    config = json.loads((run_dir / "paper_config.json").read_text(encoding="utf-8"))

    assert config["krx_default_universe"] == ["005930.KS", "000660.KS", "005380.KS", "035420.KS", "035720.KS"]
    assert status["benchmark"]["ticker"] == "069500.KS"
    assert status["benchmark"]["status"] == "MISSING"
    assert status["benchmark"]["not_promotable"] is True
    assert status["drawdown"]["not_promotable"] is True
    assert "krx_benchmark_missing" in status["drawdown"]["review_flags"]


def test_krx_pilot_rejects_limit_up_and_limit_down_fills(tmp_path):
    engine = PaperTradingEngine(
        PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05", market="KRX", phase1_us_only=False)
    )
    limit_up_bars = _bars(2, start=100.0)
    limit_up_bars[-1]["open"] = 131.3
    limit_up_bars[-1]["high"] = 131.3
    limit_up_bars[-1]["low"] = 131.3
    limit_up_bars[-1]["close"] = 131.3
    limit_up_bars[-1]["adjusted_close"] = 131.3
    limit_down_bars = _bars(2, start=100.0)
    limit_down_bars[-1]["open"] = 70.0
    limit_down_bars[-1]["high"] = 70.0
    limit_down_bars[-1]["low"] = 70.0
    limit_down_bars[-1]["close"] = 70.0
    limit_down_bars[-1]["adjusted_close"] = 70.0

    limit_up = engine.evaluate_signal(_signal(ticker="005930.KS"), limit_up_bars)
    limit_down = engine.evaluate_signal(_signal(ticker="000660.KS"), limit_down_bars)

    assert limit_up.status == "REJECTED"
    assert limit_up.reason == "krx_limit_up_fill_blocked"
    assert limit_down.status == "REJECTED"
    assert limit_down.reason == "krx_limit_down_fill_blocked"


def test_paper_trading_marks_failed_incomplete_and_rebuilds_report(tmp_path, monkeypatch):
    import stock_rtx4060.paper_trading as paper_trading

    config = PaperTradingConfig(output_root=tmp_path / "failed", run_date="2026-05-05")
    engine = PaperTradingEngine(config)
    original_write_jsonl = paper_trading._write_jsonl

    def fail_on_fills(path, rows):
        if path.name == "fills.jsonl":
            raise RuntimeError("simulated fill write failure")
        original_write_jsonl(path, rows)

    monkeypatch.setattr(paper_trading, "_write_jsonl", fail_on_fills)
    try:
        engine.run([_signal()], {"AAPL": _bars(6)})
    except RuntimeError:
        pass
    else:
        raise AssertionError("simulated fill write failure did not raise")

    run_dir = next((tmp_path / "failed").iterdir())
    failed_config = json.loads((run_dir / "paper_config.json").read_text(encoding="utf-8"))
    assert failed_config["status"] == "FAILED_INCOMPLETE"

    monkeypatch.setattr(paper_trading, "_write_jsonl", original_write_jsonl)
    complete = PaperTradingEngine(PaperTradingConfig(output_root=tmp_path / "complete", run_date="2026-05-05")).run(
        [_signal()],
        {"AAPL": _bars(6)},
    )
    complete_dir = Path(complete["run_dir"])
    (complete_dir / "daily_report.md").unlink()
    rebuilt = rebuild_daily_report(complete_dir)

    assert rebuilt.exists()
    assert "Paper trading only - no broker orders" in rebuilt.read_text(encoding="utf-8")


def test_paper_trading_promotion_drawdown_rules():
    passing = calculate_promotion_drawdown([
        {"date": "2026-05-01", "equity": 100_000.0},
        {"date": "2026-05-02", "equity": 96_000.0},
        {"date": "2026-05-03", "equity": 101_000.0},
    ])
    hard_fail = calculate_promotion_drawdown([
        {"date": "2026-05-01", "equity": 100_000.0},
        {"date": "2026-05-02", "equity": 89_000.0},
    ])
    benchmark_flag = calculate_promotion_drawdown([
        {"date": "2026-05-01", "equity": 100_000.0},
        {"date": "2026-05-02", "equity": 91_500.0},
    ], spy_max_drawdown_pct=4.0)
    missing = calculate_promotion_drawdown([])

    assert passing["promotion_hard_fail"] is False
    assert passing["review_flags"] == []
    assert hard_fail["promotion_hard_fail"] is True
    assert "mdd_90d_gt_10pct" in hard_fail["review_flags"]
    assert "mdd_30d_gt_8pct_review" in benchmark_flag["review_flags"]
    assert "spy_relative_mdd_review" in benchmark_flag["review_flags"]
    assert missing["not_promotable"] is True
    assert "missing_equity_curve" in missing["review_flags"]


def test_paper_status_api_is_read_only(tmp_path, monkeypatch):
    config = PaperTradingConfig(output_root=tmp_path, run_date="2026-05-05")
    PaperTradingEngine(config).run([_signal()], {"AAPL": _bars(6)})

    import api_server

    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    client = api_server.app.test_client()

    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())
    response = client.get("/api/paper-status")
    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema_version"] == "paper_status.v1"
    assert payload["paper_trading_only"] is True
    assert payload["latest_run"]["run_id"]
    assert before == after


def test_paper_status_api_includes_read_only_krx_pilot_status(tmp_path, monkeypatch):
    us_root = tmp_path / "reports" / "paper_trading" / "runs"
    PaperTradingEngine(PaperTradingConfig(output_root=us_root, run_date="2026-05-05")).run([_signal()], {"AAPL": _bars(6)})
    PaperTradingEngine(PaperTradingConfig(output_root=us_root, run_date="2026-05-05", market="KRX", phase1_us_only=False)).run(
        [_signal(ticker="005930.KS")],
        {"005930.KS": _bars(6)},
    )

    import api_server

    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    client = api_server.app.test_client()

    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())
    response = client.get("/api/paper-status")
    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema_version"] == "paper_status.v1"
    assert payload["paper_trading_only"] is True
    assert payload["krx_pilot"]["paper_trading_only"] is True
    assert payload["krx_pilot"]["latest_run"]["strategy_id"] == "paper-v1"
    assert payload["krx_pilot"]["positions"][0]["market"] == "KRX"
    assert payload["krx_pilot"]["positions"][0]["currency"] == "KRW"
    assert payload["krx_pilot"]["paper_only_label"] == "Paper trading only - no broker orders"
    assert before == after
