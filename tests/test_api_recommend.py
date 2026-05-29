from types import SimpleNamespace

import api_server


def test_full_universe_both_track_expands_top_for_dedupe():
    universe = ["005930.KS", "000660.KS", "005380.KS"]

    assert api_server._expanded_top_for_full_universe(universe, "BOTH", 3) == 6
    assert api_server._expanded_top_for_full_universe(universe, "S", 3) == 3
    assert api_server._expanded_top_for_full_universe(universe, "BOTH", 2) == 2


def test_full_universe_both_track_dedupes_best_sorted_result_per_ticker():
    universe = ["005930.KS", "000660.KS", "005380.KS"]
    rows = [
        SimpleNamespace(ticker="005930.KS", track="L", score=99),
        SimpleNamespace(ticker="000660.KS", track="S", score=95),
        SimpleNamespace(ticker="005930.KS", track="S", score=91),
        SimpleNamespace(ticker="005380.KS", track="L", score=90),
        SimpleNamespace(ticker="000660.KS", track="L", score=89),
    ]

    result = api_server._dedupe_full_universe_results(rows, universe, "BOTH", 3)

    assert [row.ticker for row in result] == ["005930.KS", "000660.KS", "005380.KS"]
    assert [row.track for row in result] == ["L", "S", "L"]


def test_partial_top_request_keeps_track_level_candidates():
    universe = ["005930.KS", "000660.KS", "005380.KS"]
    rows = [
        SimpleNamespace(ticker="005930.KS", track="L"),
        SimpleNamespace(ticker="005930.KS", track="S"),
    ]

    assert api_server._dedupe_full_universe_results(rows, universe, "BOTH", 2) is rows


def test_local_alt_vite_origin_is_allowed_by_cors():
    client = api_server.app.test_client()

    response = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5174"})

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5174"
