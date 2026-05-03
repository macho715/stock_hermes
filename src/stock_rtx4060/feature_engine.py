"""
Leak-safe OHLCV feature engineering for stock_rtx4060.

The feature matrix is designed for post-close decision support.  By default,
features are shifted by one bar so the model never trains on the same close used
as the label origin.  Targets are forward returns over ``horizon`` bars.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")
TARGET_COLUMNS = ("target_direction", "target_return")


@dataclass(frozen=True)
class FeatureBuildResult:
    frame: pd.DataFrame
    feature_columns: list[str]
    target_columns: list[str]


@dataclass(frozen=True)
class FeatureConfig:
    """Feature generation controls."""

    feature_lag: int = 1
    min_periods_ratio: float = 1.0
    target_threshold: float = 0.0
    include_raw_ohlcv: bool = False


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize common CSV/yfinance OHLCV variants to flat OHLCV columns."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [str(col[0]) for col in df.columns]
    rename_map = {column.lower(): column for column in OHLCV_COLUMNS}
    normalized = df.rename(columns={col: rename_map.get(str(col).lower(), col) for col in df.columns})
    missing = set(OHLCV_COLUMNS) - set(normalized.columns)
    if missing:
        raise ValueError(f"필수 컬럼 누락: {sorted(missing)}")
    result = normalized.loc[:, list(OHLCV_COLUMNS)].copy()
    for column in OHLCV_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=list(OHLCV_COLUMNS))
    result = result[result["Close"] > 0]
    result["Volume"] = result["Volume"].clip(lower=0)
    return result


def make_synthetic_ohlcv(n: int = 720, seed: int = 42) -> pd.DataFrame:
    """Generate deterministic synthetic OHLCV data for tests and benchmarks."""
    if n < 30:
        raise ValueError("n must be >= 30")
    rng = np.random.default_rng(seed)
    price = 100.0
    closes: list[float] = []
    for i in range(n):
        seasonal = 0.00025 * np.sin(i / 45.0) + 0.00015 * np.cos(i / 90.0)
        volatility = 0.010 + 0.006 * (1 + np.sin(i / 70.0)) / 2
        price *= 1.0 + rng.normal(0.00035 + seasonal, volatility)
        closes.append(float(max(price, 1.0)))
    close = np.asarray(closes, dtype=float)
    high = close * (1.0 + rng.uniform(0.002, 0.020, n))
    low = close * (1.0 - rng.uniform(0.002, 0.020, n))
    open_ = low + rng.uniform(0.0, 1.0, n) * (high - low)
    volume = rng.integers(1_000_000, 7_000_000, n).astype(float)
    index = pd.bdate_range("2022-01-03", periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=index)


class TechnicalIndicators:
    """Vectorized technical indicator builder.

    The implementation favors deterministic pandas/NumPy operations and avoids
    slow Python loops except where a rolling robust statistic is unavoidable.
    """

    def __init__(self, df: pd.DataFrame, config: FeatureConfig | None = None):
        self.config = config or FeatureConfig()
        self.df = normalize_ohlcv(df)
        self.df = self.df.sort_index()

    @property
    def close(self) -> pd.Series:
        return self.df["Close"].astype(float)

    @property
    def high(self) -> pd.Series:
        return self.df["High"].astype(float)

    @property
    def low(self) -> pd.Series:
        return self.df["Low"].astype(float)

    @property
    def volume(self) -> pd.Series:
        return self.df["Volume"].astype(float)

    def sma(self, period: int) -> pd.Series:
        return self.close.rolling(period, min_periods=period).mean()

    def ema(self, period: int) -> pd.Series:
        return self.close.ewm(span=period, adjust=False, min_periods=period).mean()

    def true_range(self) -> pd.Series:
        return pd.concat(
            [
                self.high - self.low,
                (self.high - self.close.shift(1)).abs(),
                (self.low - self.close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)

    def atr(self, period: int = 14) -> pd.Series:
        # Wilder smoothing is standard for ATR and more stable than a simple MA.
        return self.true_range().ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    def rsi(self, period: int = 14) -> pd.Series:
        delta = self.close.diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        return (100.0 - (100.0 / (1.0 + rs))).clip(0.0, 100.0)

    def macd(self) -> tuple[pd.Series, pd.Series, pd.Series]:
        line = self.ema(12) - self.ema(26)
        signal = line.ewm(span=9, adjust=False, min_periods=9).mean()
        hist = line - signal
        return line, signal, hist

    def adx(self, period: int = 14) -> pd.Series:
        high_diff = self.high.diff()
        low_diff = -self.low.diff()
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0.0), 0.0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0.0), 0.0)
        atr = self.atr(period)
        plus_di = 100.0 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
        minus_di = 100.0 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
        return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    def stochastic(self, k: int = 14, d: int = 3) -> tuple[pd.Series, pd.Series]:
        low_min = self.low.rolling(k, min_periods=k).min()
        high_max = self.high.rolling(k, min_periods=k).max()
        pct_k = 100.0 * (self.close - low_min) / (high_max - low_min).replace(0.0, np.nan)
        pct_d = pct_k.rolling(d, min_periods=d).mean()
        return pct_k.clip(0.0, 100.0), pct_d.clip(0.0, 100.0)

    def williams_r(self, period: int = 14) -> pd.Series:
        high_max = self.high.rolling(period, min_periods=period).max()
        low_min = self.low.rolling(period, min_periods=period).min()
        return (-100.0 * (high_max - self.close) / (high_max - low_min).replace(0.0, np.nan)).clip(-100.0, 0.0)

    def cci(self, period: int = 20) -> pd.Series:
        typical = (self.high + self.low + self.close) / 3.0
        ma = typical.rolling(period, min_periods=period).mean()
        mad = typical.rolling(period, min_periods=period).apply(
            lambda arr: float(np.mean(np.abs(arr - np.mean(arr)))), raw=True
        )
        return (typical - ma) / (0.015 * mad.replace(0.0, np.nan))

    def bollinger_bands(self, period: int = 20, width: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        mid = self.sma(period)
        std = self.close.rolling(period, min_periods=period).std()
        upper = mid + width * std
        lower = mid - width * std
        band_width = (upper - lower) / mid.replace(0.0, np.nan)
        pct_b = (self.close - lower) / (upper - lower).replace(0.0, np.nan)
        return upper, mid, lower, band_width, pct_b

    def mfi(self, period: int = 14) -> pd.Series:
        typical = (self.high + self.low + self.close) / 3.0
        raw_flow = typical * self.volume
        positive = raw_flow.where(typical > typical.shift(1), 0.0).rolling(period, min_periods=period).sum()
        negative = raw_flow.where(typical < typical.shift(1), 0.0).rolling(period, min_periods=period).sum()
        ratio = positive / negative.replace(0.0, np.nan)
        return (100.0 - 100.0 / (1.0 + ratio)).clip(0.0, 100.0)

    def chaikin_money_flow(self, period: int = 20) -> pd.Series:
        """Chaikin Money Flow: volume-weighted close position within high-low range."""
        hl_range = (self.high - self.low).replace(0.0, np.nan)
        mfv = ((self.close - self.low) - (self.high - self.close)) / hl_range * self.volume
        return (mfv.rolling(period, min_periods=period).sum() /
                self.volume.rolling(period, min_periods=period).sum().replace(0.0, np.nan)).clip(-1.0, 1.0)

    def keltner_channel(self, period: int = 20, atr_mult: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Keltner Channels: EMA ± (atr_mult * ATR).  Returns (upper, mid, lower)."""
        mid = self.ema(period)
        atr = self.atr(period)
        upper = mid + atr_mult * atr
        lower = mid - atr_mult * atr
        return upper, mid, lower

    def vortex_indicator(self, period: int = 14) -> tuple[pd.Series, pd.Series]:
        """Vortex Indicator VI+ and VI- (directional movement over True Range sum)."""
        tr = self.true_range()
        tr_sum = tr.rolling(period, min_periods=period).sum().replace(0.0, np.nan)
        vi_plus_raw = (self.high - self.low.shift(1)).abs().rolling(period, min_periods=period).sum()
        vi_minus_raw = (self.low - self.high.shift(1)).abs().rolling(period, min_periods=period).sum()
        return vi_plus_raw / tr_sum, vi_minus_raw / tr_sum

    def trix(self, period: int = 15) -> pd.Series:
        """TRIX: 1-period Rate-of-Change of the triple-smoothed EMA (noise filter)."""
        ema1 = self.close.ewm(span=period, adjust=False, min_periods=period).mean()
        ema2 = ema1.ewm(span=period, adjust=False, min_periods=period).mean()
        ema3 = ema2.ewm(span=period, adjust=False, min_periods=period).mean()
        return ema3.pct_change(1, fill_method=None) * 100.0

    def elder_ray(self, period: int = 13) -> tuple[pd.Series, pd.Series]:
        """Elder Ray: Bull Power (High - EMA) and Bear Power (Low - EMA)."""
        ema = self.ema(period)
        return self.high - ema, self.low - ema

    def dpo(self, period: int = 20) -> pd.Series:
        """Detrended Price Oscillator: removes trend to expose short-term cycles."""
        shift = period // 2 + 1
        sma = self.close.rolling(period, min_periods=period).mean()
        return self.close - sma.shift(shift)

    @staticmethod
    def _rolling_zscore(series: pd.Series, period: int) -> pd.Series:
        mean = series.rolling(period, min_periods=period).mean()
        std = series.rolling(period, min_periods=period).std()
        return (series - mean) / std.replace(0.0, np.nan)

    def _feature_columns(self, frame: pd.DataFrame) -> list[str]:
        excluded = set(TARGET_COLUMNS) | set(OHLCV_COLUMNS)
        return [col for col in frame.columns if col not in excluded]

    def build_all(self, horizon: int = 5, include_targets: bool = True) -> pd.DataFrame:
        """Build the full feature matrix.

        Parameters
        ----------
        horizon:
            Forward return horizon in bars.
        include_targets:
            If ``True``, append ``target_direction`` and ``target_return`` and
            drop rows where the target is not yet knowable.
        """
        if horizon <= 0:
            raise ValueError("horizon은 양수여야 합니다")
        if len(self.df) < max(30, horizon + 5):
            return pd.DataFrame(index=self.df.index)

        f = self.df.copy()
        close = self.close
        high = self.high
        low = self.low
        volume = self.volume
        log_ret = np.log(close / close.shift(1))

        # Returns and price structure.
        for period in (1, 2, 5, 10, 20, 60, 120, 252):
            f[f"return_{period}d"] = close.pct_change(period, fill_method=None)
            f[f"log_return_{period}d"] = np.log(close / close.shift(period))
        f["gap_return"] = f["Open"] / close.shift(1) - 1.0
        candle_range = (high - low).replace(0.0, np.nan)
        f["candle_body_pct"] = (close - f["Open"]).abs() / candle_range
        f["upper_shadow_pct"] = (high - np.maximum(close, f["Open"])) / candle_range
        f["lower_shadow_pct"] = (np.minimum(close, f["Open"]) - low) / candle_range

        # Moving averages and slopes.
        for period in (5, 10, 20, 50, 100, 200):
            sma = self.sma(period)
            f[f"sma_ratio_{period}"] = close / sma - 1.0
            f[f"sma_slope_{period}"] = sma.pct_change(5, fill_method=None)
        for period in (9, 21, 55):
            ema = self.ema(period)
            f[f"ema_ratio_{period}"] = close / ema - 1.0
            f[f"ema_slope_{period}"] = ema.pct_change(5, fill_method=None)

        macd_line, macd_signal, macd_hist = self.macd()
        f["macd_line"] = macd_line / close
        f["macd_signal"] = macd_signal / close
        f["macd_hist"] = macd_hist / close
        f["adx_14"] = self.adx(14)

        # Momentum oscillators.
        for period in (7, 14, 28):
            f[f"rsi_{period}"] = self.rsi(period)
        f["stoch_k"], f["stoch_d"] = self.stochastic(14, 3)
        f["williams_r_14"] = self.williams_r(14)
        f["cci_20"] = self.cci(20)
        f["roc_10"] = close.pct_change(10, fill_method=None) * 100.0

        # Volatility and tail risk proxies.
        atr14 = self.atr(14)
        f["atr_14"] = atr14
        f["atr_pct_14"] = atr14 / close
        for period in (10, 20, 60):
            f[f"hist_vol_{period}"] = log_ret.rolling(period, min_periods=period).std() * np.sqrt(252.0)
            downside = log_ret.where(log_ret < 0.0, 0.0)
            f[f"downside_vol_{period}"] = downside.rolling(period, min_periods=period).std() * np.sqrt(252.0)
            f[f"ret_z_{period}"] = self._rolling_zscore(log_ret, period)
        _, _, _, f["bb_width"], f["bb_pct"] = self.bollinger_bands(20, 2.0)

        # Volume and liquidity features.
        dollar_volume = close * volume
        f["obv"] = (np.sign(close.diff()).fillna(0.0) * volume).cumsum()
        f["obv_slope_20"] = f["obv"].pct_change(20, fill_method=None).replace([np.inf, -np.inf], np.nan)
        f["vwap_ratio_20"] = close / (((high + low + close) / 3.0 * volume).rolling(20).sum() / volume.rolling(20).sum()) - 1.0
        f["mfi_14"] = self.mfi(14)
        f["volume_ratio_20"] = volume / volume.rolling(20, min_periods=20).mean()
        f["dollar_volume_20"] = dollar_volume.rolling(20, min_periods=20).mean()
        f["dollar_volume_z_60"] = self._rolling_zscore(dollar_volume, 60)
        f["cmf_20"] = self.chaikin_money_flow(20)

        # Keltner Channel position.
        kc_upper, kc_mid, kc_lower = self.keltner_channel(20, 2.0)
        kc_width = (kc_upper - kc_lower).replace(0.0, np.nan)
        f["kc_pct"] = (close - kc_lower) / kc_width
        f["kc_width"] = kc_width / kc_mid.replace(0.0, np.nan)

        # Vortex Indicator.
        vi_plus, vi_minus = self.vortex_indicator(14)
        f["vi_plus_14"] = vi_plus
        f["vi_minus_14"] = vi_minus
        f["vi_diff_14"] = vi_plus - vi_minus

        # TRIX and Elder Ray.
        f["trix_15"] = self.trix(15)
        bull_power, bear_power = self.elder_ray(13)
        f["elder_bull_13"] = bull_power / close.replace(0.0, np.nan)
        f["elder_bear_13"] = bear_power / close.replace(0.0, np.nan)

        # Detrended Price Oscillator.
        f["dpo_20"] = self.dpo(20) / close.replace(0.0, np.nan)

        # Breakout, drawdown, and regime proxies.
        for period in (20, 60, 252):
            rolling_high = high.rolling(period, min_periods=period).max()
            rolling_low = low.rolling(period, min_periods=period).min()
            f[f"dist_high_{period}"] = close / rolling_high - 1.0
            f[f"dist_low_{period}"] = close / rolling_low - 1.0
            f[f"drawdown_{period}"] = close / rolling_high - 1.0
        f["trend_regime_fast"] = ((close > self.sma(20)) & (self.sma(20) > self.sma(50))).astype(float)
        f["trend_regime_slow"] = ((close > self.sma(50)) & (self.sma(50) > self.sma(200))).astype(float)

        # Optional raw data retention for debugging only.
        if not self.config.include_raw_ohlcv:
            f = f.drop(columns=[c for c in OHLCV_COLUMNS if c in f.columns])

        feature_cols = self._feature_columns(f)
        if self.config.feature_lag > 0:
            f.loc[:, feature_cols] = f.loc[:, feature_cols].shift(self.config.feature_lag)

        if include_targets:
            future_return = close.shift(-horizon) / close - 1.0
            f["target_return"] = future_return
            f["target_direction"] = (future_return > self.config.target_threshold).astype(int)
            # Rows whose future return is unknowable must not be used for training.
            f.loc[future_return.isna(), list(TARGET_COLUMNS)] = np.nan

        f = f.replace([np.inf, -np.inf], np.nan)
        needed = self._feature_columns(f)
        if include_targets:
            needed += list(TARGET_COLUMNS)
        f = f.dropna(subset=needed)
        return f


def feature_columns(frame: pd.DataFrame) -> list[str]:
    """Return model feature columns from a feature frame."""
    excluded = set(TARGET_COLUMNS)
    return [col for col in frame.columns if col not in excluded]


def build_feature_frame(df: pd.DataFrame, horizon: int = 5) -> FeatureBuildResult:
    frame = TechnicalIndicators(df).build_all(horizon=horizon)
    return FeatureBuildResult(frame=frame, feature_columns=feature_columns(frame), target_columns=list(TARGET_COLUMNS))


def align_feature_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column not in result:
            result[column] = 0.0
    return result.loc[:, list(columns)].fillna(0.0)
