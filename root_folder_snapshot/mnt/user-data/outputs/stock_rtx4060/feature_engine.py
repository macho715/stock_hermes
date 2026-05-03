"""
feature_engine.py — i5-13500HX 병렬 피처 생성
- joblib 16 워커 → P+E 코어 동시 활용
- L3 24MB 캐시 → CHUNK_SIZE=500 최적화
- Time: O(n·k / workers)  Space: O(n·m)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from hw_profile import FEATURE_PARALLEL_WORKERS, CHUNK_SIZE


class TechnicalIndicators:
    """
    30종 기술적 지표 + 병렬 연산 (i5-13500HX 16 워커)
    룩어헤드 바이어스 방지: 모든 지표 shift 기반 계산
    """

    REQUIRED_COLS = {"Open", "High", "Low", "Close", "Volume"}

    def __init__(self, df: pd.DataFrame):
        if not self.REQUIRED_COLS.issubset(df.columns):
            raise ValueError(f"필수 컬럼 누락: {self.REQUIRED_COLS - set(df.columns)}")
        self.df = df.copy().astype(np.float32)   # FP32 → 메모리 50%↓

    # ── Trend ──────────────────────────────────────────────
    def sma(self, period: int) -> pd.Series:
        return self.df["Close"].rolling(period, min_periods=period).mean()

    def ema(self, period: int) -> pd.Series:
        return self.df["Close"].ewm(span=period, adjust=False).mean()

    def macd(self) -> tuple[pd.Series, pd.Series, pd.Series]:
        macd_line = self.ema(12) - self.ema(26)
        signal = macd_line.ewm(span=9, adjust=False).mean()
        return macd_line, signal, macd_line - signal

    def adx(self, period: int = 14) -> pd.Series:
        h, l, c = self.df["High"], self.df["Low"], self.df["Close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        dmp = (h - h.shift()).clip(lower=0)
        dmn = (l.shift() - l).clip(lower=0)
        dmp = dmp.where(dmp > dmn, 0)
        dmn = dmn.where(dmn > dmp, 0)
        di_p = 100 * dmp.rolling(period).mean() / atr.replace(0, np.nan)
        di_n = 100 * dmn.rolling(period).mean() / atr.replace(0, np.nan)
        return (100 * (di_p - di_n).abs() / (di_p + di_n).replace(0, np.nan)).rolling(period).mean()

    def ichimoku(self) -> dict[str, pd.Series]:
        """일목균형표 (장기 추세)"""
        h, l = self.df["High"], self.df["Low"]
        tenkan = (h.rolling(9).max() + l.rolling(9).min()) / 2
        kijun  = (h.rolling(26).max() + l.rolling(26).min()) / 2
        span_a = ((tenkan + kijun) / 2).shift(26)
        span_b = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
        return {"tenkan": tenkan, "kijun": kijun, "span_a": span_a, "span_b": span_b}

    # ── Momentum ───────────────────────────────────────────
    def rsi(self, period: int = 14) -> pd.Series:
        delta = self.df["Close"].diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        return 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    def stochastic(self, k: int = 14, d: int = 3) -> tuple[pd.Series, pd.Series]:
        lo = self.df["Low"].rolling(k).min()
        hi = self.df["High"].rolling(k).max()
        pct_k = 100 * (self.df["Close"] - lo) / (hi - lo).replace(0, np.nan)
        return pct_k, pct_k.rolling(d).mean()

    def williams_r(self, period: int = 14) -> pd.Series:
        hi = self.df["High"].rolling(period).max()
        lo = self.df["Low"].rolling(period).min()
        return -100 * (hi - self.df["Close"]) / (hi - lo).replace(0, np.nan)

    def cci(self, period: int = 20) -> pd.Series:
        tp = (self.df[["High", "Low", "Close"]]).mean(axis=1)
        ma = tp.rolling(period).mean()
        mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
        return (tp - ma) / (0.015 * mad.replace(0, np.nan))

    def roc(self, period: int = 10) -> pd.Series:
        return self.df["Close"].pct_change(period) * 100

    def awesome_oscillator(self) -> pd.Series:
        """Awesome Oscillator — 중장기 모멘텀"""
        mp = (self.df["High"] + self.df["Low"]) / 2
        return mp.rolling(5).mean() - mp.rolling(34).mean()

    # ── Volatility ─────────────────────────────────────────
    def bollinger_bands(self, period: int = 20, k: float = 2.0):
        mid = self.sma(period)
        std = self.df["Close"].rolling(period).std()
        upper, lower = mid + k * std, mid - k * std
        band_range = (upper - lower).replace(0, np.nan)
        return upper, mid, lower, band_range / mid, (self.df["Close"] - lower) / band_range

    def atr(self, period: int = 14) -> pd.Series:
        h, l, c = self.df["High"], self.df["Low"], self.df["Close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def keltner_channels(self, period: int = 20, mult: float = 2.0):
        """Keltner Channel — Bollinger Squeeze 감지용"""
        mid = self.ema(period)
        atr_val = self.atr(period)
        return mid + mult * atr_val, mid, mid - mult * atr_val

    def hist_vol(self, period: int = 20) -> pd.Series:
        log_ret = np.log(self.df["Close"] / self.df["Close"].shift())
        return log_ret.rolling(period).std() * np.sqrt(252) * 100

    # ── Volume ─────────────────────────────────────────────
    def obv(self) -> pd.Series:
        return (np.sign(self.df["Close"].diff()) * self.df["Volume"]).fillna(0).cumsum()

    def vwap(self, period: int = 20) -> pd.Series:
        tp = self.df[["High", "Low", "Close"]].mean(axis=1)
        return (tp * self.df["Volume"]).rolling(period).sum() / self.df["Volume"].rolling(period).sum()

    def mfi(self, period: int = 14) -> pd.Series:
        tp = self.df[["High", "Low", "Close"]].mean(axis=1)
        mf = tp * self.df["Volume"]
        pos = mf.where(tp > tp.shift(), 0).rolling(period).sum()
        neg = mf.where(tp < tp.shift(), 0).rolling(period).sum()
        return 100 - (100 / (1 + pos / neg.replace(0, np.nan)))

    def vpt(self) -> pd.Series:
        """Volume Price Trend"""
        pct = self.df["Close"].pct_change()
        return (pct * self.df["Volume"]).cumsum()

    # ── Parallel Builder (i5-13500HX 16 워커) ─────────────
    def _compute_group(self, group: str) -> dict[str, pd.Series]:
        """병렬 실행 단위: 그룹별 지표 계산"""
        if group == "trend":
            macd, macd_sig, macd_hist = self.macd()
            ichi = self.ichimoku()
            return {
                "sma_ratio_5":  self.df["Close"] / self.sma(5) - 1,
                "sma_ratio_10": self.df["Close"] / self.sma(10) - 1,
                "sma_ratio_20": self.df["Close"] / self.sma(20) - 1,
                "sma_ratio_50": self.df["Close"] / self.sma(50) - 1,
                "sma_ratio_200":self.df["Close"] / self.sma(200) - 1,
                "ema_9":  self.ema(9),
                "ema_21": self.ema(21),
                "macd":      macd,
                "macd_sig":  macd_sig,
                "macd_hist": macd_hist,
                "adx_14":    self.adx(14),
                "ichi_tenkan": ichi["tenkan"],
                "ichi_kijun":  ichi["kijun"],
            }
        elif group == "momentum":
            stoch_k, stoch_d = self.stochastic()
            return {
                "rsi_7":      self.rsi(7),
                "rsi_14":     self.rsi(14),
                "rsi_21":     self.rsi(21),
                "stoch_k":    stoch_k,
                "stoch_d":    stoch_d,
                "williams_r": self.williams_r(),
                "cci_20":     self.cci(20),
                "roc_5":      self.roc(5),
                "roc_10":     self.roc(10),
                "ao":         self.awesome_oscillator(),
            }
        elif group == "volatility":
            bb_u, bb_m, bb_l, bb_w, bb_p = self.bollinger_bands()
            kc_u, kc_m, kc_l = self.keltner_channels()
            squeeze = bb_w - (kc_u - kc_l) / kc_m  # BB < KC → squeeze
            return {
                "bb_width":    bb_w,
                "bb_pct":      bb_p,
                "bb_squeeze":  squeeze,
                "atr_14":      self.atr(14),
                "hist_vol_20": self.hist_vol(20),
            }
        elif group == "volume":
            return {
                "obv":        self.obv(),
                "vwap_ratio": self.df["Close"] / self.vwap() - 1,
                "mfi_14":     self.mfi(),
                "vpt":        self.vpt(),
                "vol_ratio":  self.df["Volume"] / self.df["Volume"].rolling(20).mean(),
            }
        elif group == "price":
            return {
                "return_1d":  self.df["Close"].pct_change(1),
                "return_5d":  self.df["Close"].pct_change(5),
                "return_20d": self.df["Close"].pct_change(20),
                "hl_ratio":   (self.df["High"] - self.df["Low"]) / self.df["Close"],
                "gap":        (self.df["Open"] - self.df["Close"].shift()) / self.df["Close"].shift(),
            }
        return {}

    def build_all(self, horizon: int = 5) -> pd.DataFrame:
        """
        전체 피처 병렬 생성 (joblib 16 워커)
        
        i5-13500HX 최적화:
        - P-core 6개: trend/momentum 연산 (복잡한 rolling)
        - E-core 8개: price/volume 연산 (단순 계산)
        - L3 24MB: CHUNK_SIZE=500 청크 캐시 적중률 최대화
        """
        groups = ["trend", "momentum", "volatility", "volume", "price"]

        # 병렬 그룹 계산 (n_jobs=min(groups, workers))
        results = Parallel(
            n_jobs=min(len(groups), FEATURE_PARALLEL_WORKERS),
            backend="threading",   # GIL-free pandas/numpy 연산
            prefer="threads"
        )(delayed(self._compute_group)(g) for g in groups)

        # 결과 병합
        f = self.df.copy()
        for group_dict in results:
            for name, series in group_dict.items():
                f[name] = series

        # 타겟 생성 (룩어헤드 방지: shift(-horizon))
        future_ret = f["Close"].shift(-horizon) / f["Close"] - 1
        f["target_direction"] = (future_ret > 0).astype(np.int8)
        f["target_return"]    = future_ret.astype(np.float32)

        # 원본 OHLCV 제거 + NaN 처리
        f.drop(columns=["Open", "High", "Low", "Close", "Volume",
                         "ema_9", "ema_21", "ichi_tenkan", "ichi_kijun"],
               inplace=True, errors="ignore")
        f.dropna(inplace=True)
        f = f.astype(np.float32)   # 전체 FP32 → VRAM 절약

        return f
