# Phase 1: Source Contract Design
## Real Data Ops Upgrade — provider selection & thresholds

**Date**: 2026-05-03
**Status**: ✅ APPROVED (2026-05-03) — Q-1=Y, Q-2=Y, Q-3=Y, Q-4=optional
**Primary provider**: PyKRX (한국 주식)

---

## 1. Provider Priority Table

| Priority | Provider | Scope | Status |
|----------|----------|--------|--------|
| 1 (primary) | **PyKRX** | KRX 한국 주식 (KRX-only tickers: 0xxxx.KS, 1xxxx.KS) | ✅ Approved (2026-05-03) |
| 2 (fallback) | **FinanceDataReader** | 한국 주식 +海外股票的 | Installation required |
| 3 (research) | **yfinance** | 海外 주식 (NYSE, NASDAQ) + research-only | Existing (no credential) |
| 4 (optional) | **OpenBB** | Multiple providers, optional | Existing, remains optional |

**Fallback chain**: PyKRX → FinanceDataReader → yfinance (research) → FAIL

---

## 2. Provider Metadata Contract

Each `ProviderResult` produced by `load_ohlcv_with_provider()` carries:

```python
@dataclass(frozen=True)
class ProviderResult:
    frame: pd.DataFrame              # OHLCV DataFrame
    provider_requested: str         # what user/cli requested
    provider_used: str               # what actually loaded
    source: str                       # canonical source name
    endpoint: str | None             # API endpoint used (if applicable)
    fallback_reason: str | None      # why fallback was triggered (if applicable)
    metadata: dict[str, Any] | None  # freshness, ticker_type, etc.
```

**Required metadata fields**:

| Field | Type | Description |
|-------|------|-------------|
| `ticker_type` | `str` | `"KRX"` for Korean tickers, `"NASDAQ"`, `"NYSE"`, `"UNKNOWN"` |
| `data_freshness_minutes` | `int` | Minutes since last close (0 = just updated) |
| `market_close_adj` | `bool` | True if OHLCV adjusted for market close |
| `source_timestamp` | `str` | ISO timestamp of data retrieval |
| `error_reason` | `str \| None` | Populated on FAIL status only |

---

## 3. Freshness Rules

| Market | Max staleness | Action if stale |
|--------|----------------|-----------------|
| KRX (PyKRX) | 1 business day | AMBER — flag but allow |
| NYSE | 1 calendar day | RED — block |
| NASDAQ | 1 calendar day | RED — block |
| Unknown | 0 | RED — block (must specify market) |

**Freshness gate**: `DATA_FRESHNESS`

```
input:  ProviderResult.metadata.data_freshness_minutes
output: PASS / AMBER / RED

PASS  → freshness within limit for known market
AMBER → KRX >1bd but <3bd stale (flag in audit, allow)
RED   → stale beyond AMBER threshold, or unknown market
```

---

## 4. yfinance Research-Only Boundaries

| Usage | Allowed? | Reason |
|-------|----------|--------|
| Price-only lookup for NYSE/NASDAQ | ✅ Yes | Research-grade, no credential |
| Primary source for KRX | ❌ No | PyKRX is primary |
| Forward-filled data fill | ⚠️ AMBER | Acceptable for low-frequency work |
| Corporate action data | ❌ No | Use official sources only |

---

## 5. PyKRX Integration Notes

**Installation** (to be done at implementation time):
```bash
pip install pykrx
```

**OHLCV fetch pattern** (from PyKRX docs):
```python
from pykrx import stock
df = stock.get_ohlcv(ticker="005930", end="20260503", freq="d")
# columns: date, open, high, low, close, volume
```

**Required normalization** (must map to lowercase columns for feature_engine):
```python
# PyKRX output: ['date', 'open', 'high', 'low', 'close', 'volume']
# Normalize to: ['date', 'open', 'high', 'low', 'close', 'volume']  # same
# If index is DatetimeIndex already → use as-is
# If columns are named differently → rename before passing to normalize_ohlcv()
```

**KRX ticker patterns**:
- ordinary: `0xxxx.KS` (KOSPI), `1xxxx.KS` (KOSDAQ)
- preferred: `2xxxx.KS`
- ETN: `3xxxx.KS`

---

## 6. Approval Required

Before Phase 2 (Validation Gate Design) can begin:

| Item | Question | User Answer |
|------|----------|-------------|
| Q-1 | **FinanceDataReader fallback** — install as fallback alongside PyKRX? (Y/N) | Pending |
| Q-2 | **NYSE/NASDAQ source** — keep yfinance as research-only for海外股票? | Pending |
| Q-3 | **Data freshness thresholds** — AMBER: KRX >1bd stale, RED: >3bd stale — accept? | Pending |
| Q-4 | **OpenBB** — remain optional or remove from ALLOWED_PROVIDERS? | Pending |

---

## 7. Next Phase Gate

Phase 2 (Validation Gate Design) entry requires:
- ✅ Q-1, Q-2, Q-3, Q-4 answers received
- ✅ provider selection finalized
- ⏳ Currently: Q-1 through Q-4 pending user input
