"""
main.py — i5-13500HX + RTX 4060 최적화 주식 예측 파이프라인
실행: python main.py --ticker AAPL --horizon 5 --lite (Ollama 동시 실행 시 --lite)
테스트: python main.py --test
"""
from __future__ import annotations

import argparse
import sys
import time
import numpy as np
import pandas as pd

from hw_profile import print_hw_summary, HW_PROFILE


# ─────────────────────────────────────────────────
# § TESTS
# ─────────────────────────────────────────────────

def _dummy_ohlcv(n: int = 400, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    price = 100.0
    prices = []
    for _ in range(n):
        price *= 1 + rng.normal(0.0003, 0.015)
        prices.append(float(price))
    close = np.array(prices, dtype=np.float32)
    high = close * (1 + rng.uniform(0.001, 0.02, n)).astype(np.float32)
    low  = close * (1 - rng.uniform(0.001, 0.02, n)).astype(np.float32)
    open_ = (low + rng.uniform(0, 1, n) * (high - low)).astype(np.float32)
    vol  = rng.integers(1_000_000, 5_000_000, n).astype(np.float32)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low,
                          "Close": close, "Volume": vol})


def test_hw_profile():
    """HW 프로파일 설정값 검증"""
    assert HW_PROFILE["cpu"]["logical"] == 20
    assert HW_PROFILE["gpu"]["vram_gb"] == 8
    assert HW_PROFILE["optimization"]["mixed_precision"] is True
    print("✅ test_hw_profile: i5-13500HX + RTX 4060 프로파일 정상")


def test_feature_engine_parallel():
    """16 워커 병렬 피처 생성 + FP32 타입 확인"""
    from feature_engine import TechnicalIndicators
    df = _dummy_ohlcv(400)
    ti = TechnicalIndicators(df)
    t0 = time.time()
    feat = ti.build_all(horizon=5)
    elapsed = time.time() - t0

    assert len(feat) > 0, "피처 비어있음"
    assert "target_direction" in feat.columns
    assert feat["target_direction"].isin([0, 1]).all()
    assert feat.isnull().sum().sum() == 0

    # FP32 메모리 절약 확인
    for col in feat.select_dtypes(include=[np.float64]).columns:
        assert False, f"FP64 컬럼 존재 (메모리 낭비): {col}"

    print(f"✅ test_feature_engine_parallel: "
          f"{len(feat)}행 × {len(feat.columns)-2}피처 | {elapsed:.2f}s")


def test_feature_engine_edge():
    """엣지 케이스: 컬럼 누락 예외"""
    from feature_engine import TechnicalIndicators
    try:
        TechnicalIndicators(pd.DataFrame({"Close": [1.0, 2.0]}))
        assert False, "예외 미발생"
    except ValueError:
        pass
    print("✅ test_feature_engine_edge: 컬럼 누락 예외 정상")


def test_backtester():
    """Kelly 사이징 + 백테스팅 수치 검증"""
    from backtester import Backtester, BacktestConfig, KellyCriterion

    # Kelly 범위 검증
    kelly = KellyCriterion(fraction=0.25)
    assert kelly.optimal_pct() == 0.08  # 초기 보수적
    for _ in range(30):
        kelly.update(0.05)
    for _ in range(12):
        kelly.update(-0.02)
    pct = kelly.optimal_pct()
    assert 0.01 <= pct <= 0.25, f"Kelly 범위 초과: {pct}"

    # 백테스팅 실행
    rng = np.random.default_rng(1)
    n = 300
    prices  = pd.Series(np.cumprod(1 + rng.normal(0.0003, 0.01, n)) * 100)
    signals = pd.Series(rng.uniform(0, 1, n))
    bt = Backtester(BacktestConfig(initial_capital=100_000))
    r = bt.run(prices, signals)

    assert r["final_capital"] > 0
    assert r["max_drawdown_pct"] >= 0
    assert 0 <= r["win_rate"] <= 100
    print(f"✅ test_backtester: "
          f"Return={r['total_return_pct']:.2f}% | "
          f"Sharpe={r['sharpe_ratio']:.3f} | "
          f"MDD={r['max_drawdown_pct']:.2f}% | "
          f"Kelly%={pct:.3f}")


def test_xgb_cpu_fallback():
    """XGBoost CPU fallback (CUDA 미설치 환경)"""
    from feature_engine import TechnicalIndicators
    from ensemble_model import XGBPredictor

    df = _dummy_ohlcv(300)
    feat = TechnicalIndicators(df).build_all(horizon=5)
    TARGET = ["target_direction", "target_return"]
    X = feat[[c for c in feat.columns if c not in TARGET]]
    y = feat["target_direction"]

    xgb = XGBPredictor(use_gpu=False)  # CPU 모드
    xgb.fit(X, y)
    probs = xgb.predict_proba(X)
    assert len(probs) == len(X)
    assert (0 <= probs).all() and (probs <= 1).all()
    print(f"✅ test_xgb_cpu_fallback: {len(probs)} 예측 완료")


def run_all_tests():
    tests = [
        test_hw_profile,
        test_feature_engine_parallel,
        test_feature_engine_edge,
        test_backtester,
        test_xgb_cpu_fallback,
    ]
    print("\n" + "="*52)
    print("  🧪 Tests — i5-13500HX + RTX 4060 최적화 빌드")
    print("="*52)
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*52}")
    print(f"  결과: {passed}/{len(tests)} 통과 | {failed} 실패")
    print("="*52)


# ─────────────────────────────────────────────────
# § PIPELINE
# ─────────────────────────────────────────────────

def run_pipeline(ticker: str, horizon: int, period: str, lite: bool):
    try:
        import yfinance as yf
    except ImportError:
        print("❌ yfinance 미설치: pip install yfinance")
        return

    from feature_engine import TechnicalIndicators
    from ensemble_model import EnsemblePredictor, EnsembleConfig
    from backtester import Backtester, BacktestConfig, print_vram_usage

    print_hw_summary()
    if lite:
        print("  ⚡ LITE 모드: Ollama 공존 (VRAM 4GB 제한)")

    print(f"\n[1/5] 데이터 수집: {ticker} ({period})")
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    if df.empty or len(df) < 250:
        print(f"❌ 데이터 부족 ({len(df)}행)")
        return
    print(f"     {len(df):,}행 | {df.index[0].date()} ~ {df.index[-1].date()}")

    print("\n[2/5] 피처 생성 (16 워커 병렬)")
    t0 = time.time()
    feat = TechnicalIndicators(df).build_all(horizon=horizon)
    n_feat = len(feat.columns) - 2
    print(f"     {len(feat):,}행 × {n_feat}피처 | {time.time()-t0:.2f}s")

    print("\n[3/5] 앙상블 학습 (XGBoost-GPU + LSTM-FP16)")
    cfg = EnsembleConfig(horizon=horizon, lite_mode=lite)
    model = EnsemblePredictor(cfg)
    cv = model.fit(feat)
    cv_df = pd.DataFrame(cv)

    print("\n[4/5] 최신 신호 예측")
    TARGET = ["target_direction", "target_return"]
    X_all = feat[[c for c in feat.columns if c not in TARGET]]
    pred = model.predict(X_all)
    print(f"\n  ╔══════════════════════════════════╗")
    print(f"  ║ 신호:      {pred['signal']:<23}║")
    print(f"  ║ 방향 확률: {pred['direction_prob']:.1%}{'':>22}║")
    print(f"  ║ 신뢰도:    {pred['confidence']:.1%}{'':>22}║")
    print(f"  ║ XGB:       {pred['xgb_prob']:.1%} │ LSTM: {pred['lstm_prob']:.1%}{'':>8}║")
    print(f"  ╚══════════════════════════════════╝")

    print("\n[5/5] 백테스팅")
    signals_all = model.xgb.predict_proba(X_all)
    prices_bt = df["Close"].iloc[-len(feat):].reset_index(drop=True)
    result = Backtester(BacktestConfig()).run(prices_bt, pd.Series(signals_all))

    print(f"\n  ╔══════════════════════════════════╗")
    print(f"  ║ 총 수익률:  {result['total_return_pct']:>7.2f}%{'':>16}║")
    print(f"  ║ Sharpe:    {result['sharpe_ratio']:>7.3f}{'':>18}║")
    print(f"  ║ Calmar:    {result['calmar_ratio']:>7.3f}{'':>18}║")
    print(f"  ║ 최대낙폭:  {result['max_drawdown_pct']:>7.2f}%{'':>16}║")
    print(f"  ║ 승률:      {result['win_rate']:>7.2f}%{'':>16}║")
    print(f"  ║ 거래 수:   {result['n_trades']:>7}{'':>18}║")
    print(f"  ╚══════════════════════════════════╝")

    # KPI 게이트
    print("\n📊 KPI 판정:")
    kpi = {
        f"정확도 ≥55%  [{cv_df['accuracy'].mean():.1%}]":
            cv_df['accuracy'].mean() >= 0.55,
        f"AUC ≥0.60   [{cv_df['auc'].mean():.3f}]":
            cv_df['auc'].mean() >= 0.60,
        f"Sharpe ≥1.5 [{result['sharpe_ratio']:.3f}]":
            result['sharpe_ratio'] >= 1.5,
        f"MDD ≤20%    [{result['max_drawdown_pct']:.2f}%]":
            result['max_drawdown_pct'] <= 20.0,
    }
    for label, ok in kpi.items():
        print(f"  {'✅' if ok else '⚠️ AMBER'} {label}")

    print("\n📡 VRAM 상태:")
    print_vram_usage()

    # Top features
    print("\n🔬 주요 피처 (XGBoost 기여도):")
    top = model.top_features(10)
    for feat_name, score in top.items():
        bar = "▓" * int(score * 200)
        print(f"  {feat_name:<20} {bar} {score:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RTX 4060 + i5-13500HX 최적화 주식 예측"
    )
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--period", default="5y")
    parser.add_argument("--lite", action="store_true",
                        help="Ollama 동시 실행 모드 (VRAM 4GB 제한)")
    parser.add_argument("--test", action="store_true",
                        help="전체 테스트 실행")
    args = parser.parse_args()

    if args.test:
        run_all_tests()
    else:
        run_pipeline(args.ticker, args.horizon, args.period, args.lite)
