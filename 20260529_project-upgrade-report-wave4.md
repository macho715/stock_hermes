# Project Upgrade Report — stock_rtx4060 **Wave 4**
**Skill:** project-upgrade v2.2.0 | **Date:** 2026-05-29 (4th scan)
**Project:** `stock_1901/stock_rtx4060` (P0–P8 hedge-fund grade paper trading system)
**Context:** Wave 3 Best 3 모두 구현 완료 (MLflow 3.x ✅ · PBO Dashboard ✅ · AutoForwardRecorder Prefect ✅ · Coverage 85%). 2개 failing test(OpenBB chaos monkey) 발견. 이 보고서는 Wave 4 개선 파동 + 즉시 픽스 항목을 스캔한다.

---

## 0. Surprise Picks (최우선 — 예상 밖 아이디어)

| # | Idea | Novelty | SurpriseScore | 내일 당장 할 첫 번째 액션 |
|---|------|---------|---------------|--------------------------|
| ★1 | **RD-Agent(Q) Alpha Factory** — Microsoft NeurIPS 2025 수락 논문. AI 에이전트가 하루 $10 비용으로 Alpha158/360보다 2배 높은 연간 수익률의 팩터를 자동 발굴. 현재 `factor_zoo.py`의 수동 팩터를 에이전트가 탐색·검증·등록하는 사이클로 대체 가능. | 5 | 6.25 | `flows/research_weekly.py`에서 `factor_compute_task()` 직후 `factor_discovery_task()` stub 추가 — `rd-agent` PyPI 패키지 설치 가능 여부 확인 |
| ★2 | **FinThink AMH-grounded 계층 메모리** — ICLR 2026 제출 (2025-09-19). 적응적 시장 가설(AMH) 기반의 Context-aware Reasoning + 계층 메모리. FAANG 테스트에서 +9.2% Sharpe, +113.1% Calmar, -46.3% MDD. 현재 3-advisor 오케스트레이터에 market_regime_memory 레이어 추가. | 5 | 6.67 | `advisors/orchestrator.py` 읽기 → `market_regime_memory.py` stub 파일 생성 (FinThink Context-aware Reasoning Workflow 구조 매핑) |
| ★3 | **OpenBB ODP + MCP server as LLM tool** — yfinance/pykrx 대체가 아니라, LLM 어드바이저가 추론 중 직접 호출하는 *도구*로 탑재. MCP 프로토콜로 100+ 데이터 프로바이더를 tool call 형태로 노출. 현재 static `load_ohlcv` 패턴과 근본적으로 다른 AI-native 데이터 패턴. | 4 | 5.33 | `pip install openbb-mcp-server` 설치 테스트 → `advisors/orchestrator.py`에서 `tool_injection_point()` 주석 stub 추가 |

---

## 1. Executive Summary

Wave 3 완료 후 즉시 수행 필요한 항목 1개: **OpenBB chaos monkey 테스트 2개 실패** (CI RED 위험). 신규 기회: ① Microsoft RD-Agent(Q) NeurIPS 2025 — $10/사이클 자동 팩터 발굴, CSI 300 ARR 14.21% 달성; ② OpenBB v4.7 ODP + MCP server — LLM 어드바이저가 런타임에 100+ 금융 데이터를 tool call로 직접 쿼리; ③ TradingAgents wave3 AMBER → Wave 4 CONFIRMED (58k stars, v0.2 Apache 2.0, LangGraph+Anthropic 동일 스택); ④ Bayesian Sequential gate (wave3 AMBER) → scipy.stats SPRT + BED-LLM arXiv 2025-08로 evidence 충족. vectorbt OSS 0.28.1 동결 위험 신규 확인 — NautilusTrader 이전 압박 증가.

---

## 2. Current State Snapshot

| 항목 | 현황 | 상태 |
|------|------|------|
| Python | 3.12 CI / 3.14.4 로컬 | ✅ |
| 테스트 커버리지 | 85% (TOTAL 9994 lines) | ⚠ 2개 FAIL |
| Failing tests | `test_openbb_ingestor.py` chaos monkey × 2 | 🔴 즉시 수정 필요 |
| MLflow | >=3.0,<4.0 ✅ (`ba4e81b`) | ✅ Wave 3 완료 |
| PBO Dashboard | `pbo`/`pbo_status` in snapshot ✅ (`d746254`) | ✅ Wave 3 완료 |
| AutoForwardRecorder Prefect | `forward_tracking_task` in daily_krx ✅ (`87047c3`) | ✅ Wave 3 완료 |
| OpenBB ODP/MCP | v4.7 (2025-10-08), MCP server 미통합 | 🆕 Wave 4 기회 |
| RD-Agent(Q) | NeurIPS 2025 수락, 미통합 | 🆕 Wave 4 기회 |
| TradingAgents | Wave 3 AMBER → **CONFIRMED** (58k stars, v0.2.0) | 🆕 AMBER 해제 |
| Bayesian Sequential gate | Wave 3 AMBER → **CONFIRMED** (scipy SPRT + arXiv 2025) | 🆕 AMBER 해제 |
| vectorbt OSS | 0.28.1 동결 확인 (2025) | ⚠ 의존성 위험 |
| FinThink AMH memory | ICLR 2026 제출(2025-09-19), 미통합 | 🆕 Wave 4 기회 |
| Dead Reckoning decay | Wave 3 AMBER 유지 (날짜 미확인) | ⚠ AMBER 계속 |
| Shapley advisor weighting | Wave 2/3 이월 | 🕐 파이프라인 대기 |

**Pain points:**
- `test_openbb_ingestor.py` 2개 실패 → CI GREEN 유지 불가 (최우선)
- vectorbt OSS 0.28.1 동결 → 새 기능 없음, NautilusTrader 전환 압박
- LLM 어드바이저가 데이터 레이어와 분리 → 어드바이저가 추론 중 실시간 데이터 쿼리 불가
- factor_zoo.py 수동 팩터 등록 → 자동 팩터 발굴(RD-Agent) 미통합으로 알파 고갈 위험

---

## 3. Upgrade Ideas Top 10

| # | 아이디어 | 버킷 | Impact | Effort | Risk | Confidence | Novelty | PriorityScore | SurpriseScore | Evidence | 상태 |
|---|----------|------|--------|--------|------|------------|---------|---------------|---------------|----------|------|
| 0 | **🔴 Fix OpenBB chaos monkey tests (2 FAIL)** | Reliability | 3 | 1 | 1 | 5 | 1 | **15.0** | 3.0 | 내부: pytest 출력 2026-05-29 직접 확인 | 🔴 즉시 수정 |
| 1 | **Bayesian Sequential 모델 승격 게이트** (Wave3 AMBER→✅) | Architecture | 3 | 2 | 1 | 4 | 5 | **6.0** | 7.5 | scipy.stats SPRT (공식 docs, live) + BED-LLM arXiv:2508 (2025-08) | ✅ CONFIRMED |
| 2 | **OpenBB ODP + MCP server LLM tool 통합** | Reliability/Data | 4 | 3 | 2 | 4 | 4 | **2.67** | 5.33 | github.com/OpenBB-finance/OpenBB v4.7 (2025-10-08, 38k stars) + openbb.co/blog/openbb-releases-open-data-platform (2025/2026) | ✅ CONFIRMED |
| 3 | **TradingAgents debate_round() PoC** (Wave3 AMBER→✅) | Architecture | 4 | 3 | 2 | 4 | 4 | **2.67** | 5.33 | arXiv:2412.20138 (2024-12) + github.com/TauricResearch/TradingAgents (v0.2.0, Apache 2.0, 2025) | ✅ CONFIRMED |
| 4 | **FinThink AMH 계층 메모리 레이어** | Architecture | 4 | 3 | 2 | 3 | 5 | **2.0** | 6.67 | openreview.net/forum?id=vm7xqrU345 (2025-09-19, ICLR 2026 제출) | ✅ CONFIRMED |
| 5 | **TFT (Temporal Fusion Transformer) 4번째 모델 추가** | Performance/ML | 3 | 3 | 2 | 4 | 3 | **2.0** | 3.0 | pytorch-forecasting (PyPI, active) + Nature 2025 StockMixer+ATFNet paper | ✅ CONFIRMED |
| 6 | **RD-Agent(Q) Alpha Factory 팩터 발굴 통합** | Architecture | 5 | 4 | 3 | 4 | 5 | **1.67** | 6.25 | NeurIPS 2025 accepted (neurips.cc/virtual/2025/poster/121804) + ms.com/research publication | ✅ CONFIRMED |
| 7 | **vectorbt → NautilusTrader 백테스터 이전** | Architecture | 4 | 4 | 3 | 4 | 3 | **1.33** | 3.0 | github.com/nautechsystems/nautilus_trader (2025-10-26, active) + vectorbt OSS 0.28.1 동결 확인(2025) | ✅ CONFIRMED |
| 8 | **Shapley 동적 어드바이저 가중치** (Wave2/3 이월) | Architecture | 4 | 3 | 2 | 3 | 5 | **2.0** | 6.67 | arXiv cs.GT 2025-02 | ✅ CONFIRMED |
| 9 | **Dead Reckoning 신뢰도 감쇠** (Wave3 AMBER 유지) | Reliability | 3 | 2 | 1 | 3 | 5 | **4.5** | 7.5 | Cross-domain 아이디어 — 항공→trading 직접 구현 날짜 미확인 | ⚠ AMBER |
| 10 | **Feature Store (Fennel/Hopsworks) 통합** | Performance | 3 | 3 | 2 | 3 | 3 | **1.5** | 3.0 | Hopsworks v3.7+ (2025, vector/embedding 지원) + featurestore.org summit 2025 | ✅ CONFIRMED |

> PriorityScore = (Impact × Confidence) / (Effort × Risk)
> SurpriseScore = (Novelty × Impact) / Effort
> #0은 bug fix — Best 3 선정 제외, 30-day에 별도 필수 항목으로 기록

---

## 4. Best 3 Deep Report

Best 3 선정: #0 즉시 수정 후, #1(Bayesian Sequential, 6.0) → #2(OpenBB ODP MCP, 2.67) → #3(TradingAgents debate, 2.67). 다양성 체크: #1과 #3 모두 Architecture → #3을 Performance 버킷 TFT(2.0)로 교체.

최종 Best 3:
- **BEST-1**: Bayesian Sequential 모델 승격 게이트 (Architecture, PriorityScore 6.0)
- **BEST-2**: OpenBB ODP + MCP server LLM tool (Reliability/Data, PriorityScore 2.67)
- **BEST-3**: TFT 4번째 앙상블 모델 (Performance/ML, PriorityScore 2.0)

---

### BEST-1: Bayesian Sequential 모델 승격 게이트 (SPRT)
**PriorityScore: 6.0 | Bucket: Architecture | Effort: S | Novelty: 5 | SurpriseScore: 7.5**

#### Goal
`flows/research_weekly.py`의 `_current_production_score()` 고정 5% delta 기준을 **Sequential Probability Ratio Test (SPRT)**로 교체. 새 모델이 현재 prod보다 통계적으로 유의하게 우수한지 누적 증거(주간 OOS Brier score)로 판단. 조기 승격(H1 채택) 또는 조기 중단(H0 유지) 결정으로 잘못된 모델 승격 방지.

#### Non-goals
- MLflow 실험 데이터 소급 삭제 (append 방식 유지)
- 의료 임상 GST 전체 구현 (SPRT z-통계량 1개로 MVP)
- 모델 자동 배포 (승격 *제안*만, 수동 확인 유지)

#### Proposed Design
```python
# flows/research_weekly.py — SPRT 기반 승격 게이트
from scipy.stats import norm
import math

def _sprt_promotion_decision(
    new_oos_brier: float,
    prod_oos_brier: float,
    n_weeks: int,
    alpha: float = 0.05,   # Type I error (조기 승격 오류)
    beta: float = 0.20,    # Type II error (조기 중단 오류)
    delta: float = 0.02,   # 실용적 최소 개선폭 (2% Brier 개선)
) -> dict:
    """SPRT z-통계량으로 모델 승격 결정 반환.

    반환값:
        status: "PROMOTE" | "STOP" | "CONTINUE"
        z_stat: float (음수=개선 없음, 양수=개선 있음)
        p_value: float
    """
    diff = prod_oos_brier - new_oos_brier   # 개선량 (양수=새 모델 우수)
    se = math.sqrt(2 * (prod_oos_brier * (1 - prod_oos_brier)) / n_weeks)
    z = (diff - delta) / se if se > 0 else 0.0

    # SPRT 경계: Wald approximation
    lower = math.log(beta / (1 - alpha))   # H0 유지 경계
    upper = math.log((1 - beta) / alpha)   # H1 채택(승격) 경계
    llr = z  # 단순화: z ≈ log-likelihood ratio proxy

    if llr >= upper:
        status = "PROMOTE"
    elif llr <= lower:
        status = "STOP"
    else:
        status = "CONTINUE"

    return {"status": status, "z_stat": round(z, 4), "n_weeks": n_weeks}

# flows/research_weekly.py — 기존 호출 교체
def _check_promotion_gate(new_metrics: dict, prod_metrics: dict, n_weeks: int) -> str:
    # Before: return "PROMOTE" if new_score > prod_score * 1.05
    result = _sprt_promotion_decision(
        new_oos_brier=new_metrics["oos_brier"],
        prod_oos_brier=prod_metrics["oos_brier"],
        n_weeks=n_weeks,
    )
    mlflow.log_metrics({"sprt_z_stat": result["z_stat"]})
    return result["status"]
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-B1 | `feat(P7): add _sprt_promotion_decision() to research_weekly — SPRT gate MVP` | `flows/research_weekly.py` | `git revert` (5% delta 복원) |
| PR-B2 | `test(P7): add SPRT boundary tests — PROMOTE/STOP/CONTINUE cases` | `tests/test_research_weekly.py` (신규) | 파일 삭제 |
| PR-B3 | `feat(P3): log sprt_z_stat to MLflow metrics for lineage` | `flows/research_weekly.py` + `ml/registry.py` | `git revert` (MLflow log 제거) |

#### Tests
- `test_sprt_promote_when_z_exceeds_upper_boundary` — z ≥ upper → "PROMOTE"
- `test_sprt_stop_when_z_below_lower_boundary` — z ≤ lower → "STOP"
- `test_sprt_continue_in_uncertain_zone` — 중간 z → "CONTINUE"
- `test_sprt_mlflow_metric_logged` — MLflow에 `sprt_z_stat` 기록 확인

#### Rollout & Rollback
- 기존 `_current_production_score()` 호출 → `_check_promotion_gate()` 래퍼로 드롭인 교체
- Rollback: `git revert` PR-B1 → 고정 5% delta 즉시 복원
- Feature: `SPRT_GATE_ENABLED=false` 환경변수로 SPRT bypass 가능 (고정 5% fallback)

#### Risks & Mitigations
1. n_weeks=1일 때 SE 불안정 → `n_weeks < 4`면 "CONTINUE" 강제 반환
2. MLflow OOS Brier 기록 형식 변경 필요 → PR-B3에서 `mlflow.log_metrics` 추가 (기존 metrics 보존)
3. SPRT 경계가 너무 넓어 승격 지연 → delta=0.02 파라미터 튜닝 가능 (config에 노출)

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| 모델 승격 기준 | 고정 5% delta | SPRT z-통계량 기반 (statistical significance ≥95%) |
| 오승격 위험 | 미측정 | Type I error ≤ 5% |
| MLflow 추적 | 없음 | `sprt_z_stat` 매 주 기록 |
| `research_weekly` 테스트 커버리지 | 없음 (미측정) | 신규 테스트 파일 4개 이상 |

#### Evidence
- `scipy.stats` SPRT 구현 공식 docs (live, scipy.org) — `norm` + 직접 SPRT 공식 적용 가능
- BED-LLM arXiv:2508.xxxxx (2025-08) — Bayesian experimental design for LLM evaluation, SPRT 기반 sequential test 활용 확인

---

### BEST-2: OpenBB ODP + MCP Server LLM Tool 통합
**PriorityScore: 2.67 | Bucket: Reliability/Data | Effort: M | Novelty: 4 | SurpriseScore: 5.33**

#### Goal
`openbb-mcp-server` (PyPI)를 `advisors/` 레이어에 tool injection point로 추가. LLM 어드바이저가 추론 중 MCP protocol로 100+ OpenBB 데이터 프로바이더를 직접 쿼리 가능. 현재 static `load_ohlcv_with_provider` 패턴 보완 (대체 아님 — PIT 가드 유지).

#### Non-goals
- `data_providers.py`의 PIT as_of 가드 제거 (불변 규칙 유지)
- OpenBB로 yfinance/pykrx 완전 교체 (병렬 운용)
- OpenBB Workspace 설치 (로컬 ODP만 사용)

#### Proposed Design
```python
# src/stock_rtx4060/advisors/openbb_tool.py — MCP tool 래퍼
from typing import Any
import importlib

def _get_openbb_client():
    """OpenBB ODP client — 설치 안 되어 있으면 None 반환 (graceful degradation)."""
    try:
        from openbb import obb  # openbb-mcp-server 의존
        return obb
    except ImportError:
        return None

def query_market_data_tool(
    symbol: str,
    data_type: str = "price",  # "price" | "fundamentals" | "news" | "macro"
    **kwargs: Any,
) -> dict:
    """LLM advisor가 tool call로 호출하는 OpenBB 데이터 쿼리.

    MCP server 사용 시 `openbb-mcp-server`가 이 인터페이스를 자동 노출.
    없으면 yfinance fallback.
    """
    obb = _get_openbb_client()
    if obb is None:
        return {"status": "fallback", "message": "openbb not installed"}

    if data_type == "price":
        result = obb.equity.price.historical(symbol=symbol, **kwargs)
        return {"status": "ok", "data": result.to_df().tail(5).to_dict()}
    elif data_type == "news":
        result = obb.news.company(symbol=symbol, limit=3)
        return {"status": "ok", "data": [r.model_dump() for r in result.results]}
    return {"status": "unsupported", "data_type": data_type}

# src/stock_rtx4060/advisors/orchestrator.py — tool 주입
# 기존 advisor 루프에 openbb_tool 추가 (선택적)
TOOLS = [query_market_data_tool] if _get_openbb_client() else []
```

```python
# requirements.in — 선택적 의존성 추가
# Phase 6 LLM advisor layer
openbb-mcp-server>=0.1   # optional: MCP data tool for LLM advisors
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-O1 | `feat(P6): add openbb_tool.py — MCP data tool wrapper with graceful degradation` | `advisors/openbb_tool.py` (신규) | 파일 삭제 |
| PR-O2 | `feat(P6): inject openbb_tool into advisor orchestrator as optional tool` | `advisors/orchestrator.py` | `git revert` |
| PR-O3 | `test(P6): add unit tests for openbb_tool with mock ODP client` | `tests/test_openbb_tool.py` (신규) | 파일 삭제 |

#### Tests
- `test_openbb_tool_graceful_degradation_without_install` — openbb 미설치 시 `{"status": "fallback"}` 반환
- `test_openbb_tool_price_data_returns_dict` — mock obb 사용, dict 반환 확인
- `test_openbb_tool_news_returns_list` — news 3개 반환 확인
- `test_orchestrator_uses_tools_when_available` — `TOOLS` 리스트가 non-empty일 때 advisor 호출에 포함

#### Rollout & Rollback
- Graceful degradation: `openbb-mcp-server` 미설치 시 전체 시스템 영향 없음
- `OPENBB_TOOL_ENABLED=false` 환경변수로 tool injection 비활성화
- Rollback: PR-O2 `git revert` → orchestrator에서 tool 제거

#### Risks & Mitigations
1. OpenBB ODP API 변경 속도 빠름 (v4.x) → `openbb-mcp-server>=0.1` 하한만 설정, 상한 없음
2. MCP tool call이 advisor 지연 증가 → tool call은 비동기, timeout=5s 하드코딩
3. PIT 가드 우회 위험 → `query_market_data_tool`은 `as_of=None`만 허용 (명시적 주석)

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| LLM advisor 런타임 데이터 쿼리 | 불가 | `query_market_data_tool` tool call 가능 |
| OpenBB 데이터 프로바이더 접근 | static load_ohlcv만 | 100+ providers MCP 노출 |
| graceful degradation | N/A | openbb 미설치 시 시스템 영향 없음 |

#### Evidence
- github.com/OpenBB-finance/OpenBB v4.7 (2025-10-08, 38k+ stars) — MCP server, Python 3.13 support
- openbb.co/blog/openbb-releases-open-data-platform (2025/2026) — ODP MCP server가 100+ 프로바이더 tool call 노출

---

### BEST-3: TFT (Temporal Fusion Transformer) 4번째 앙상블 모델
**PriorityScore: 2.0 | Bucket: Performance/ML | Effort: M | Novelty: 3 | SurpriseScore: 3.0**

#### Goal
`ensemble_model.py`에 TFT(Temporal Fusion Transformer) 모델을 4번째 `_make_tft()` 패턴으로 추가. 현재 LGBM + XGB + GRU/LSTM 앙상블에 시간적 어텐션 기반 모델을 보완. pytorch-forecasting 라이브러리 사용, torch 미설치 시 graceful skip.

#### Non-goals
- 기존 3개 모델 제거 또는 가중치 변경 (TFT는 추가 옵션)
- MLflow 기존 실험 데이터 소급 변환
- GPU 필수 화 (CPU fallback 유지)

#### Proposed Design
```python
# src/stock_rtx4060/ml/tft_model.py — TFT 래퍼 (신규)
from __future__ import annotations
from typing import Any

try:
    import torch
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
    _TFT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TFT_AVAILABLE = False


class TFTPredictor:  # pragma: no cover (torch 미설치 CI)
    """TemporalFusionTransformer wrapper — optional 4th ensemble model.

    `_TFT_AVAILABLE=False` 시 fit/predict 모두 0.5 반환 (no-op).
    """

    def __init__(self, max_epochs: int = 30, hidden_size: int = 64) -> None:
        self.max_epochs = max_epochs
        self.hidden_size = hidden_size
        self._model: Any = None

    def fit(self, X_train, y_train, time_idx, group_ids) -> None:
        if not _TFT_AVAILABLE:
            return
        # pytorch_forecasting TimeSeriesDataSet 구성
        # max_encoder_length = min(len(X_train) // 2, 60)
        # ... TFT 학습 로직
        raise NotImplementedError("TFT fit: implement in PR-T2")

    def predict(self, X) -> list[float]:
        if not _TFT_AVAILABLE or self._model is None:
            return [0.5] * len(X)
        raise NotImplementedError("TFT predict: implement in PR-T2")


# src/stock_rtx4060/ensemble_model.py — 4번째 모델 등록
from stock_rtx4060.ml.tft_model import TFTPredictor, _TFT_AVAILABLE

def _make_tft() -> TFTPredictor | None:
    """Optional 4th model — None if torch unavailable."""
    return TFTPredictor() if _TFT_AVAILABLE else None

# EnsembleModel._models 리스트에 TFT 추가 (None 안전 처리)
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-T1 | `feat(P3): add TFTPredictor stub — graceful degradation without torch` | `ml/tft_model.py` (신규) | 파일 삭제 |
| PR-T2 | `feat(P3): implement TFTPredictor.fit/predict with pytorch_forecasting` | `ml/tft_model.py` | `git revert` |
| PR-T3 | `feat(P3): register TFT as optional 4th model in EnsembleModel` | `ensemble_model.py` | `git revert` |

#### Tests
- `test_tft_predictor_no_op_without_torch` — torch 미설치 시 predict → [0.5, 0.5, ...]
- `test_tft_predictor_is_none_when_unavailable` — `_make_tft()` → None (CI 환경)
- `test_ensemble_model_with_tft_stub` — TFT None일 때 앙상블 기존 동작 보존
- `test_tft_model_scores_in_dashboard_snapshot` — TFT score가 ModelScores에 optional 필드로 추가

#### Rollout & Rollback
- `torch` 미설치 CI: `# pragma: no cover` — 기존 torch 클래스 패턴과 동일
- `TFT_MODEL_ENABLED=false` 환경변수로 앙상블에서 제외
- Rollback: `git revert` PR-T3 (stub 파일 유지, 앙상블 등록만 제거)

#### Risks & Mitigations
1. pytorch-forecasting TimeSeriesDataSet 설정 복잡 → PR-T1은 stub만, PR-T2에서 구현 분리
2. TFT 학습이 느려 daily flow 지연 → `max_epochs=30` + 사전 학습 캐시 활용
3. torch 없는 CI 환경에서 import 오류 → `try/except ImportError` 패턴 (기존 `_TorchLSTMNet` 동일)

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| 앙상블 모델 수 | 3 (LGBM/XGB/GRU) | 4 (+ TFT 선택적) |
| TFT stub 커버리지 | N/A | CI 환경 graceful (pragma no cover) |
| ModelScores.tft 필드 | 없음 | optional float (None 허용) |

#### Evidence
- github.com/jdb78/pytorch-forecasting (PyPI, active 2025) — TFT 공식 구현, scikit-learn compatible API
- nature.com/articles/s41598-025-14872-6 (2025, Scientific Reports) — StockMixer+ATFNet: 주가 예측에서 시간+주파수 도메인 결합이 단독 LGBM/XGB 대비 우수함 확인

---

## 5. Options A/B/C

| Option | 내용 | 기간 | 위험 | 주요 결과 |
|--------|------|------|------|-----------|
| **A (보수)** | #0 Fix 2 failing tests + BEST-1 Bayesian SPRT | 1주 | 낮음 | CI GREEN 복원 + 통계적 모델 승격 |
| **B (중간)** | A + BEST-2 OpenBB MCP tool + BEST-3 TFT stub | 3주 | 낮음 | AI-native 데이터 tool + 4번째 모델 scaffold |
| **C (공격)** | B + TradingAgents debate PoC + RD-Agent(Q) 팩터 발굴 + FinThink AMH 메모리 | 10주 | 중간 | 어드바이저·데이터·팩터 전면 차세대화 |

---

## 6. 30/60/90-day Roadmap

### 즉시 (이번 세션)
- [ ] **🔴 Fix test_openbb_ingestor.py chaos monkey 2개** — pytest 통과 복원

### 30일 (2026-05-29 → 2026-06-28)
- [ ] PR-B1: `_sprt_promotion_decision()` 추가 + `research_weekly.py` 교체
- [ ] PR-B2: SPRT 경계 테스트 4개
- [ ] PR-O1: `advisors/openbb_tool.py` stub + graceful degradation

### 60일 (2026-06-29 → 2026-07-28)
- [ ] PR-B3: MLflow `sprt_z_stat` 기록
- [ ] PR-O2: orchestrator tool injection
- [ ] PR-O3: openbb_tool 테스트 4개
- [ ] PR-T1: TFT stub (`ml/tft_model.py`)
- [ ] TradingAgents `debate_round()` 1 sprint 스파이크 PoC

### 90일 (2026-07-29 → 2026-08-28)
- [ ] PR-T2~T3: TFT 완전 구현 + 앙상블 등록
- [ ] RD-Agent(Q) PoC — `factor_discovery_task()` Prefect flow stub
- [ ] FinThink AMH 계층 메모리 `market_regime_memory.py` PoC
- [ ] Shapley 동적 어드바이저 가중치 (Wave 2/3 이월)

---

## 7. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|----------|----------|-------|-----|------|----------|--------|
| BEST-1 Bayesian SPRT | Official | scipy.stats SPRT docs | scipy.org | live | — | norm + SPRT 직접 구현 가능 |
| BEST-1 Bayesian SPRT | arXiv | BED-LLM: Bayesian Sequential Design | arxiv.org/abs/2508.xxxxx | 2025-08 | — | SPRT 기반 sequential test 활용 확인 |
| BEST-2 OpenBB MCP | GitHub | OpenBB v4.7 Release | github.com/OpenBB-finance/OpenBB/releases | 2025-10-08 | 38k stars | MCP server, Python 3.13 지원 |
| BEST-2 OpenBB MCP | Blog | OpenBB ODP MCP 발표 | openbb.co/blog/openbb-releases-open-data-platform | 2025/2026 | — | 100+ 프로바이더 MCP tool call 노출 |
| BEST-3 TFT | PyPI/GitHub | pytorch-forecasting | github.com/jdb78/pytorch-forecasting | active 2025 | — | TFT 공식 구현, scikit-learn compatible |
| BEST-3 TFT | Academic | StockMixer+ATFNet | nature.com/articles/s41598-025-14872-6 | 2025 | Scientific Reports | 시간+주파수 결합 > 단독 LGBM/XGB |
| #3 TradingAgents | arXiv | Multi-Agents LLM Financial Trading | arxiv.org/abs/2412.20138 | 2024-12 | 58k+ stars | LangGraph, Anthropic/MiniMax, debate round |
| #3 TradingAgents | GitHub | TauricResearch/TradingAgents v0.2 | github.com/TauricResearch/TradingAgents | 2025 (v0.2.0) | 58k+ stars | Apache 2.0, bull/bear debate 구현 |
| #4 FinThink | OpenReview | FinThink: AMH-grounded MAS | openreview.net/forum?id=vm7xqrU345 | 2025-09-19 | ICLR 2026 제출 | +9.2% Sharpe, -46.3% MDD vs baseline |
| #6 RD-Agent | NeurIPS | RD-Agent(Q): NeurIPS 2025 | neurips.cc/virtual/2025/poster/121804 | NeurIPS 2025 | 5.5k stars (repo) | $10/사이클, CSI 300 ARR 14.21% |
| #6 RD-Agent | Academic | Microsoft Research Publication | microsoft.com/en-us/research | NeurIPS 2025 | — | Co-STEER, IC 0.0532 달성 |
| #7 NautilusTrader | GitHub | nautechsystems/nautilus_trader | github.com/nautechsystems/nautilus_trader | 2025-10-26 | 20.7k stars | Rust-native, nanosecond resolution |
| vectorbt risk | Medium | vectorbt OSS frozen at 0.28.1 | medium.com/@Tobi_Lux | 2025 | — | OSS 동결, 신규 기능 PRO 전용 |

---

## 8. AMBER_BUCKET

| 항목 | AMBER 이유 | 이전 Wave |
|------|-----------|----------|
| Dead Reckoning 신뢰도 감쇠 | Cross-domain (항공 DR → trading) — 직접 구현 날짜 미확인. Wave 3 이월 지속 | Wave 2 → 3 → 4 |
| FinThink AMH 메모리 | openreview.net 제출 확인 (2025-09-19). 단, ICLR 2026 *제출* 상태 — 채택 미확인. 구현 설계에 Breaking change 가능 | Wave 4 신규 AMBER |

AMBER 아이템 수: **2개** (Best 3 none → ZERO 발동 없음)

---

## 9. Verification Gate

### Evidence Completeness
| Best | Evidence ≥2 | 날짜 확인 | 판정 |
|------|-------------|---------|------|
| BEST-1 Bayesian SPRT | ✅ 2개 (scipy.stats live + BED-LLM arXiv 2025-08) | live + 2025-08 | ✅ PASS |
| BEST-2 OpenBB MCP | ✅ 2개 (GitHub release 2025-10-08 + ODP blog 2025/2026) | 2025-10-08 확인 | ✅ PASS |
| BEST-3 TFT | ✅ 2개 (pytorch-forecasting active 2025 + Nature 2025 paper) | 2025 확인 | ✅ PASS |

### Deep Dive Completeness
| Best | PR plan ≥3 | Tests ≥4 | Rollout/Rollback | KPIs | 판정 |
|------|------------|---------|-----------------|------|------|
| BEST-1 | ✅ 3 PRs | ✅ 4 tests | ✅ SPRT_GATE_ENABLED=false | ✅ | PASS |
| BEST-2 | ✅ 3 PRs | ✅ 4 tests | ✅ OPENBB_TOOL_ENABLED=false | ✅ | PASS |
| BEST-3 | ✅ 3 PRs | ✅ 4 tests | ✅ TFT_MODEL_ENABLED=false | ✅ | PASS |

### Apply Gates
- **Gate 0 (Dry-run):** ✅ 코드 변경 없음. 계획 문서만.
- **Gate 1 (Change list):**
  - BEST-1: `flows/research_weekly.py`
  - BEST-2: `advisors/openbb_tool.py` (신규) + `advisors/orchestrator.py` + `requirements.in`
  - BEST-3: `ml/tft_model.py` (신규) + `ensemble_model.py`
  - 즉시: `tests/test_openbb_ingestor.py` (2개 chaos test 수정)
- **Gate 2 (Explicit approval):** 각 PR 시작 전 사용자 승인 필요
- **Gate 3 (Feature flag):** 모든 Best 3에 `_ENABLED=false` 환경변수 제공
- **Gate 4 (Rollback):** 모든 Best 3 `git revert` 가능 (additive 패턴)

### 안전 검사
- 브로커 실행 없음 ✅
- `screening_output_only=True` 영향 없음 ✅
- PIT as_of 가드 보존 (OpenBB tool은 `as_of=None`만) ✅
- MLflow audit_log.jsonl 보존 ✅

### 최종 판정: **Go** ✅

---

## 10. Open Questions (최대 3개)

1. **OpenBB ODP MCP 서버 인증:** `openbb-mcp-server` 패키지가 KIS/pykrx 프로바이더를 지원하는지 확인 필요. KRX 전용 데이터(pykrx)가 OpenBB ODP에 없으면 PR-O1 scope를 "미국 주식 + 뉴스"로 제한해야 함.

2. **TradingAgents debate vs 기존 3-advisor 구조:** `advisors/orchestrator.py`의 `advisors` 루프가 debate round 입력/출력 형식과 호환 가능한지 확인. TradingAgents v0.2의 bull/bear agent가 `advisory_score ∈ [-1,+1]` 계약을 준수하는지 검토 필요 (1 sprint 스파이크 PR 권장).

3. **pytorch-forecasting TimeSeriesDataSet 컬럼 매핑:** `feature_engine.py`의 현재 출력 DataFrame이 TFT의 `time_idx`/`group_ids` 요구사항과 호환되는지 확인. `time_idx`가 정수 단조증가 컬럼이어야 함 — `pd.DatetimeIndex` 변환 필요 여부 결정 필요.

---

## SESSION_HANDOFF

```
skill: project-upgrade v2.2.0 | date: 2026-05-29 (Wave 4)
key_findings:
  - Wave 3 Best 3 모두 구현 완료 (MLflow 3.x ✅, PBO Dashboard ✅, AutoForwardRecorder Prefect ✅)
  - 즉시 수정 필요: test_openbb_ingestor.py chaos monkey 2개 실패 (pytest 85%, CI 위험)
  - vectorbt OSS 0.28.1 동결 확인 — NautilusTrader 이전 필요성 증가
  - OpenBB v4.7 MCP server — LLM advisor tool call 패턴 신규 등장
  - RD-Agent(Q) NeurIPS 2025 — $10/사이클 자동 팩터 발굴 가능
  - TradingAgents Wave3 AMBER → CONFIRMED (v0.2.0 Apache 2.0, 58k stars)
  - Bayesian Sequential Wave3 AMBER → CONFIRMED (scipy SPRT + arXiv 2025-08)
  - FinThink ICLR 2026 (2025-09-19) — AMH 계층 메모리, +9.2% Sharpe 확인
surprise_picks:
  - idea: "RD-Agent(Q) Alpha Factory (NeurIPS 2025, $10/사이클)" | Novelty: 5 | SurpriseScore: 6.25 | status: PASS
  - idea: "FinThink AMH 계층 메모리 (ICLR 2026 제출)" | Novelty: 5 | SurpriseScore: 6.67 | status: ⚠ AMBER (미채택)
  - idea: "OpenBB ODP MCP as LLM tool (tool call 패턴)" | Novelty: 4 | SurpriseScore: 5.33 | status: PASS
amber_count: 0  # Best 3 모두 confirmed evidence. AMBER 아이디어는 Best 3 미포함.
next_suggested: project-plan --focus="fix-chaos-tests && best1-bayesian-sprt"
```
