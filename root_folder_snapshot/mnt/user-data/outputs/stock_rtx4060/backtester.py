"""
backtester.py — Kelly Criterion 포지션 사이징 + 성과 분석
Time: O(n)  Space: O(n)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    transaction_cost: float = 0.001      # 0.1%
    slippage: float = 0.0005             # 0.05%
    kelly_fraction: float = 0.25         # 1/4 Kelly (보수적)
    max_position_pct: float = 0.25       # 최대 25% 포지션
    threshold_buy: float = 0.55
    threshold_sell: float = 0.45
    stop_loss_pct: float = 0.05          # 5% 손절
    take_profit_pct: float = 0.12        # 12% 익절


class KellyCriterion:
    """분수 Kelly: W - (1-W)/R, 1/4 적용"""
    def __init__(self, fraction: float = 0.25):
        self.fraction = fraction
        self._wins: list[float] = []
        self._losses: list[float] = []

    def update(self, pnl: float):
        (self._wins if pnl > 0 else self._losses).append(abs(pnl))

    def optimal_pct(self) -> float:
        if len(self._wins) < 5 or len(self._losses) < 5:
            return 0.08   # 초기 보수적 8%
        w = len(self._wins) / (len(self._wins) + len(self._losses))
        r = np.mean(self._wins) / max(np.mean(self._losses), 1e-6)
        k = w - (1 - w) / r
        return float(np.clip(self.fraction * k, 0.01, self.max_position_pct))

    @property
    def max_position_pct(self) -> float:
        return 0.25


class Backtester:
    """Walk-Forward 백테스팅 + 리스크 관리"""

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.cfg = config or BacktestConfig()
        self.kelly = KellyCriterion(self.cfg.kelly_fraction)

    def run(self, prices: pd.Series, signals: pd.Series) -> dict:
        prices = prices.reset_index(drop=True).astype(np.float64)
        signals = signals.reset_index(drop=True).astype(np.float64)
        n = min(len(prices), len(signals))

        capital = self.cfg.initial_capital
        position = 0.0
        entry_price = 0.0
        portfolio_values = np.zeros(n)
        trades: list[dict] = []

        for i in range(n):
            price = prices.iloc[i]
            sig   = signals.iloc[i]
            portfolio_values[i] = capital + position * price

            # 청산 조건
            if position > 0:
                pnl_pct = (price - entry_price) / entry_price
                if (pnl_pct <= -self.cfg.stop_loss_pct or
                    pnl_pct >= self.cfg.take_profit_pct or
                    sig < self.cfg.threshold_sell):
                    gross = position * price
                    fee = gross * (self.cfg.transaction_cost + self.cfg.slippage)
                    capital += gross - fee
                    pnl = gross - fee - position * entry_price
                    self.kelly.update(pnl)
                    trades.append({"idx": i, "type": "SELL", "price": price,
                                   "pnl": pnl, "pnl_pct": pnl_pct * 100})
                    position = entry_price = 0.0

            # 진입 조건
            if position == 0 and sig >= self.cfg.threshold_buy:
                pct = self.kelly.optimal_pct()
                invest = capital * pct
                fee = invest * (self.cfg.transaction_cost + self.cfg.slippage)
                net = invest - fee
                if net > price:
                    position = net / price
                    capital -= invest
                    entry_price = price
                    trades.append({"idx": i, "type": "BUY", "price": price,
                                   "kelly_pct": pct * 100})

        if position > 0:
            capital += position * prices.iloc[n-1] * (1 - self.cfg.transaction_cost)

        pv = pd.Series(portfolio_values)
        daily_ret = pv.pct_change().dropna()
        closed = [t for t in trades if t["type"] == "SELL"]
        wins = [t for t in closed if t.get("pnl", 0) > 0]

        sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(252)
                  if daily_ret.std() > 0 else 0.0)
        mdd = self._mdd(pv)
        calmar = (pv.iloc[-1] / pv.iloc[0] - 1) / max(mdd, 0.001) if mdd else 0.0

        return {
            "total_return_pct":  round((pv.iloc[-1] / pv.iloc[0] - 1) * 100, 2),
            "sharpe_ratio":      round(sharpe, 3),
            "max_drawdown_pct":  round(mdd * 100, 2),
            "calmar_ratio":      round(calmar, 3),
            "win_rate":          round(len(wins) / max(len(closed), 1) * 100, 2),
            "n_trades":          len(closed),
            "final_capital":     round(capital, 2),
            "portfolio_values":  pv.tolist(),
        }

    @staticmethod
    def _mdd(pv: pd.Series) -> float:
        peak = pv.expanding().max()
        return abs(((pv - peak) / peak).min())


def print_vram_usage():
    """RTX 4060 VRAM 사용량 실시간 출력"""
    try:
        import subprocess, re
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            encoding="utf-8", timeout=5
        ).strip()
        used, total = map(int, out.split(", "))
        pct = used / total * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  VRAM [{bar}] {used:,}/{total:,}MB ({pct:.1f}%)")
    except Exception:
        print("  VRAM: nvidia-smi 미감지 (Windows에서 실행 시 정상)")
