# Stage 3: Portfolio Analytics — 스펙

## 개요
전체 포트폴리오의 리스크 집계, setor 분포, drawdown 추적, VaR估算. Position Tracker 및 Alert Engine의 데이터를 활용.

## 파일 위치
`src/stock_rtx4060/portfolio_analytics.py`

## 핵심 기능

### 1. Sector/Tema 분포
- 추천 결과의 sector 정보 추출 (yfinance info에서 sector/theme)
- Concentration risk: single sector > 30% 경고

### 2. 리스크 집계
| 지표 | 계산 |
|------|------|
| `total_exposure_pct` | total_position_value / capital |
| `track_s_exposure_pct` | Track-S value / capital |
| `track_l_exposure_pct` | Track-L value / capital |
| `max_position_exposure_pct` | largest single position / capital |
| `beta_to_benchmark` | estimated portfolio beta vs SPY |
| `var_1d_95` | 1-day 95% VaR (simplified: 1.65 * hist_vol) |
| `concentration_risk` | largest sector weight |

### 3. Drawdown 추적
- peak-to-trough equity curve
- Max Drawdown (MDD)聚合
- Recover 시간 계산

### 4. Rebalance 제안
- Track-S / Track-L allocation drift detection
- Cash buffer adequacy check
- 재형형 필요시 경고

### 5. Performance 지표
- 일간/주간/월간 수익률
- Unrealized vs Realized 분리
- Benchmark 대비 excess return

## 데이터 구조

```python
@dataclass
class PortfolioAnalytics:
    generated_at: str
    capital: float
    total_position_value: float
    total_exposure_pct: float
    track_s_exposure_pct: float
    track_l_exposure_pct: float
    cash_remaining_pct: float
    max_position_exposure_pct: float
    concentration_risk_pct: float
    concentrated_sector: str | None
    beta_to_spy: float
    var_1d_95_pct: float
    current_drawdown_pct: float
    max_drawdown_pct: float
    days_in_drawdown: int
    rebalance_needed: bool
    rebalance_suggestions: list[str]
    sector_weights: dict[str, float]
    daily_pnl_pct: float
    weekly_pnl_pct: float
    monthly_pnl_pct: float
    unrealized_pnl_abs: float
    realized_pnl_abs: float
```

## Position Tracker 통합
- `portfolio_analytics.analyze(snapshot: PortfolioSnapshot)` 
- `snapshot.positions` 및 `position_tracker` 데이터 활용

## 검증
1. `python -m py_compile src/stock_rtx4060/portfolio_analytics.py`
2. `pytest tests/test_portfolio_analytics.py -v`

## 의존성
- `yfinance` (sector/beta 정보)
- 기존 `position_tracker.py`
- 기존 `risk_rules.py` (RiskConfig)