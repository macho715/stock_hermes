"""KEVPE v2 — End-to-End demo on synthetic KOSPI-like data.

실데이터 연결 전 알고리즘 동작 확인용. PyKRX/FinanceDataReader 연결 시
make_market() 를 실데이터 로더로 교체하면 그대로 동작한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kevpe_v2 import (
    KevpeConfig, Event, FeatureScaler,
    detect_volatility_windows, match_events_to_windows,
    feature_vector_from_event, current_signal_v2,
    apply_regime_hysteresis, backtest_v2, walk_forward_validate,
    compute_performance_stats,
)


def make_synth_kospi(n=500, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # 정상 + 충격 일자 5건 삽입
    rets = rng.normal(0.0004, 0.011, size=n)
    shock_days = [80, 175, 260, 350, 430]
    shocks = [-0.07, -0.05, +0.06, -0.09, -0.04]
    for d, s in zip(shock_days, shocks):
        rets[d] += s
    close = 2500 * np.cumprod(1 + rets)
    return pd.DataFrame({
        "date": pd.date_range("2022-01-03", periods=n, freq="B"),
        "open": close * 0.999, "high": close * 1.005,
        "low": close * 0.995, "close": close,
        "volume": rng.uniform(2e8, 5e8, size=n),
    })


def make_synth_events(ohlcv: pd.DataFrame, seed=11) -> list[Event]:
    rng = np.random.default_rng(seed)
    events = []
    for d in ohlcv["date"]:
        if rng.random() < 0.05:  # 5% 일자에 이벤트
            tone = float(rng.normal(-2, 4))
            vol = float(rng.uniform(50, 800))
            div = float(rng.uniform(5, 80))
            kind = rng.choice(["war", "rate", "oil", "chip", "gen"])
            head = {
                "war": "war conflict in middle east escalates",
                "rate": "FOMC rate decision surprises markets",
                "oil": "OPEC oil supply cut announcement",
                "chip": "Samsung HBM AI chip demand soars",
                "gen": "regulatory policy review",
            }[kind]
            events.append(Event(d, head, country="Korea", tone=tone,
                                volume=vol, source_diversity=div))
    return events


def main():
    print("=" * 70)
    print("KEVPE v2 — End-to-End Demo (synthetic KOSPI-like data)")
    print("=" * 70)

    cfg = KevpeConfig(
        z_threshold=2.5,
        cost_bps_per_turn=5.0,
        confirm_days=2, cooloff_days=3,
        dd_circuit_breaker=0.20, dd_recovery_threshold=0.05,
        vol_target_annual=0.15,
        wf_n_folds=4, wf_embargo_days=5, wf_min_train_size=80,
        top_k=10, min_similarity=0.20,
    )

    ohlcv = make_synth_kospi(n=500)
    events = make_synth_events(ohlcv)
    print(f"\n[데이터] OHLCV bars={len(ohlcv)}, events={len(events)}")

    # 1) 변동성 윈도우 탐지
    windows = detect_volatility_windows(ohlcv, cfg)
    print(f"\n[1] 변동성 윈도우 {len(windows)}건 탐지")
    print(windows.head(5).to_string(index=False))

    # 2) 이벤트 매칭
    matches = match_events_to_windows(windows, events, cfg)
    print(f"\n[2] 이벤트-윈도우 매칭 {len(matches)}건")
    if not matches.empty:
        print(matches.head(5)[["window_start", "event_date", "headline",
                                "match_score", "topics"]].to_string(index=False))

    # 3) 일별 raw 신호 생성 (각 윈도우 시작점에서 패턴 매칭)
    feat_records = []
    for _, w in windows.iterrows():
        as_of = w["start"]
        pre = ohlcv[ohlcv["date"] < as_of].tail(20)
        market_ret = float(pre["close"].pct_change().iloc[-1]) if len(pre) > 1 else 0.0
        recent_events = [e for e in events if 0 <= (as_of - e.date).days <= 3]
        if not recent_events:
            continue
        ev = recent_events[0]
        feat = feature_vector_from_event(ev, market_ret=market_ret, vol_z=w["vol_z_max"])
        feat_records.append({"as_of": as_of, "feat": feat,
                             "fwd_5d": float(w["cum_return"])})

    print(f"\n[3] feature 레코드 {len(feat_records)}건")

    if len(feat_records) >= 12:
        # 학습/현재 분리 (마지막 1건이 '현재', 나머지 historic)
        feats = [r["feat"] for r in feat_records[:-1]]
        fwds = [r["fwd_5d"] for r in feat_records[:-1]]
        cur = feat_records[-1]["feat"]
        scaler = FeatureScaler().fit(feats)
        sig = current_signal_v2(
            current_feature=cur, historical_features=feats,
            historical_forward_returns=fwds,
            config=cfg, scaler=scaler,
            as_of=feat_records[-1]["as_of"],
        )
        print(f"\n[4] 현재 시그널: regime={sig.regime}, score={sig.score:.3f}")
        print(f"    expected={sig.expected_return:+.2%}, "
              f"CI=[{sig.ci_low:+.2%}, {sig.ci_high:+.2%}], "
              f"sim={sig.similarity_mean:.2f}, n={sig.n_matches}")

    # 5) regime 시계열 만들기 (간단 가정: 윈도우 시작일에만 신호 갱신)
    sig_rows = []
    if windows.empty:
        sig_rows.append({"date": ohlcv["date"].iloc[0], "regime": "GREEN"})
    else:
        for _, w in windows.iterrows():
            regime = "RED" if w["direction"] == "DOWN" else "AMBER"
            sig_rows.append({"date": w["start"], "regime": regime})
    raw_sig = pd.DataFrame(sig_rows).drop_duplicates("date").sort_values("date")
    smooth_sig = apply_regime_hysteresis(raw_sig, cfg)
    print(f"\n[5] hysteresis: raw 전환 {sum(raw_sig['regime'].iloc[1:].values != raw_sig['regime'].iloc[:-1].values) if len(raw_sig) > 1 else 0}건 → smooth 전환 "
          f"{sum(smooth_sig['regime'].iloc[1:].values != smooth_sig['regime'].iloc[:-1].values) if len(smooth_sig) > 1 else 0}건")

    # 6) backtest
    res = backtest_v2(ohlcv, smooth_sig, cfg)
    s = res["stats"]
    bh = res["buy_and_hold_stats"]
    print(f"\n[6] 백테스트 (cost={cfg.cost_bps_per_turn:.1f}bps, vol_target={cfg.vol_target_annual:.0%}):")
    print(f"    {'Metric':<20}{'Strategy':>12}{'BuyHold':>12}")
    rows = [
        ("Ann Return",   s.ann_return,    bh.ann_return),
        ("Ann Vol",      s.ann_vol,       bh.ann_vol),
        ("Sharpe",       s.sharpe,        bh.sharpe),
        ("Sortino",      s.sortino,       bh.sortino),
        ("Max Drawdown", s.max_drawdown,  bh.max_drawdown),
        ("Calmar",       s.calmar,        bh.calmar),
        ("CVaR(5%)",     s.cvar_5,        bh.cvar_5),
        ("Hit Rate",     s.hit_rate,      bh.hit_rate),
        ("Turnover/yr",  s.turnover_ann,  bh.turnover_ann),
        ("Cost Drag",    s.cost_drag,     bh.cost_drag),
        ("Total Return", s.net_total_return, bh.net_total_return),
    ]
    for name, a, b in rows:
        if "Rate" in name or "Return" in name or "Drag" in name or "Drawdown" in name or "CVaR" in name:
            print(f"    {name:<20}{a:>11.2%}{b:>11.2%} ")
        else:
            print(f"    {name:<20}{a:>12.3f}{b:>12.3f}")

    # 7) walk-forward (충분한 feat 가 있을 때만)
    if len(feat_records) >= 100:
        feats = [r["feat"] for r in feat_records]
        fwds = [r["fwd_5d"] for r in feat_records]
        dates = [r["as_of"] for r in feat_records]
        wf = walk_forward_validate(ohlcv, feats, fwds, dates, cfg)
        print(f"\n[7] Walk-forward {len(wf)} folds:")
        print(wf.to_string(index=False))
    else:
        print(f"\n[7] Walk-forward skip (feat 레코드 {len(feat_records)} < 100, "
              f"실데이터에서는 충분)")

    print("\n" + "=" * 70)
    print("DONE — 위 결과는 synthetic data 기준. 실데이터 (PyKRX, GDELT) 연결 후")
    print("`KEVPE_v2_upgrade_report.md` 의 운영 전 체크리스트를 통과해야 운용 가능.")
    print("=" * 70)


if __name__ == "__main__":
    main()
