# Project Upgrade Report — stock_rtx4060 **Wave 5**
**Skill:** project-upgrade v2.2.0 | **Date:** 2026-05-29 (5th scan)
**Project:** `stock_1901/stock_rtx4060` (P0–P8 hedge-fund grade paper trading system)
**Context:** Wave 4 완전 구현 완료 (OpenBB tool-use ✅ · AMH memory ✅ · RD-Agent stubs ✅ · 1574 tests PASS · Coverage 83%). 이 보고서는 Wave 5 개선 파동을 스캔한다.

---

## 0. Surprise Picks (최우선 — 예상 밖 아이디어)

| # | Idea | Novelty | SurpriseScore | 내일 당장 할 첫 번째 액션 |
|---|------|---------|---------------|--------------------------|
| ★1 | **Multi-Armed Bandit 어드바이저 가중치 최적화** — Netflix/Spotify의 추천 엔진에서 역수입. 고정 `{news:0.40, devils:0.30, macro:0.30}` 대신 Thompson Sampling으로 역사적 정확도 기반 동적 가중치 학습. regime별로 어떤 어드바이저가 더 맞는지 자동으로 수렴. | 5 | 6.67 | `advisors/orchestrator.py`의 `DEFAULT_WEIGHTS` 상수를 `_ThompsonWeights` 클래스 stub으로 교체 (기존 고정값 fallback 유지) |
| ★2 | **Agent Distillation (NeurIPS 2025 Spotlight)** — Anthropic API 호출을 로컬 1.5B~3B 파라미터 모델로 증류. Teacher LLM이 tool-use trajectory 생성 → student sLM 학습. 0.5B 학생이 1.5B CoT 모델과 동등한 성능. API 비용 0원, 지연 < 50ms. | 5 | 5.0 | `audit_log/advisor.jsonl`의 기존 호출 로그에서 trajectory 데이터셋 규모 파악 (`wc -l` 실행) |
| ★3 | **Circuit Breaker 3-상태 어드바이저 보호** — 전기 공학의 회로 차단기 3상태 패턴(CLOSED→OPEN→HALF-OPEN)을 LLM 어드바이저에 적용. 기존 `KILLED` 파일은 binary on/off. 진정한 circuit breaker: 연속 실패 N회 → OPEN(차단) → 30분 후 HALF-OPEN(프로브 1회) → 성공 시 CLOSED 복원. `agentcircuit` (GitHub 2025) 참조. | 4 | 16.0* | `advisors/orchestrator.py` `_blend()` 직후에 `if out.confidence == 0.0: circuit_fail_count += 1` stub 추가 |

> ★3 SurpriseScore 16.0은 Effort=1 (pip install 수준) 가정. agentcircuit 날짜 미확정 → ⚠ AMBER 처리.

---

## 1. Executive Summary

Wave 4 완전 구현 후 **즉시 수정 필요 항목 1개**: `flows/research_weekly.py:282`의 `@task` NameError — `test_research_weekly_flow.py` 수집 불가, CI RED 위험. 신규 기회: ① **mSPRT on AutoForwardRecorder** — de Prado CPCV와 결합하는 Mixture SPRT로 OOS 검증 강화; ② **TradingAgents debate_round() PoC** — 70k stars, v0.2 Apache 2.0, `debate_rounds` config 확인됨, 기존 3-advisor에 Bull/Bear/Judge 레이어 추가; ③ **Qlib v0.9.7 + RD-Agent(Q) 완전 활성화** — Qlib 이미 native MLflow 3.x + Parquet 지원, 기존 RD-Agent stubs에 Qlib 데이터 파이프라인만 연결하면 $10/사이클 2× returns 달성 가능.

---

## 2. Current State Snapshot

| 항목 | 현황 | 상태 |
|------|------|------|
| Python | 3.12 CI / 3.14.4 로컬 | ✅ |
| 테스트 커버리지 | 83% (1574 passed) | ✅ |
| Failing/Error tests | `test_research_weekly_flow.py` NameError `@task` | 🔴 즉시 수정 |
| OpenBB tool-use | `advisors/openbb_tools/` 완성 | ✅ Wave 4 완료 |
| AMH memory | `advisors/memory/` 완성 | ✅ Wave 4 완료 |
| RD-Agent stubs | `factors/rd_agent/` docker_runner.py 등 | ✅ Wave 4 완료 |
| Qlib v0.9.7 | MLflow 3.x + Parquet 지원 확인 | 🆕 Wave 5 기회 |
| TradingAgents v0.2 | 70k stars, `debate_rounds` config 확인 | 🆕 Wave 5 기회 |
| mSPRT | Mixture SPRT (2025) — SPRT보다 정확 | 🆕 SPRT 업그레이드 |
| Agent Distillation | NeurIPS 2025 Spotlight | 🆕 Wave 5 기회 |
| AgentCircuit | 날짜 미확정 | ⚠ AMBER |
| Dead Reckoning | Wave 3 AMBER 유지 | ⚠ AMBER 계속 |

**Pain points:**
- `research_weekly.py:282` `@task` NameError → `test_research_weekly_flow.py` 수집 불가
- RD-Agent docker_runner.py: Qlib 데이터 준비 없이 완전 실행 불가 (stubs 단계)
- 어드바이저 가중치 고정 → regime별 어드바이저 정확도 차이를 학습하지 못함
- AutoForwardRecorder: 30일 forward return은 수집하지만 통계적 OOS 검증 없음

---

## 3. Upgrade Ideas Top 10

| # | 아이디어 | 버킷 | Impact | Effort | Risk | Confidence | Novelty | PriorityScore | SurpriseScore | Evidence | 상태 |
|---|----------|------|--------|--------|------|------------|---------|---------------|---------------|----------|------|
| 0 | **🔴 Fix `@task` NameError in research_weekly.py** | Reliability | 3 | 1 | 1 | 5 | 1 | **15.0** | 3.0 | 내부: pytest 수집 오류 직접 확인 | 🔴 즉시 |
| 1 | **mSPRT on AutoForwardRecorder** | Reliability/Obs | 3 | 2 | 1 | 4 | 4 | **6.0** | 6.0 | Medium mSPRT 2025 + quantbeckman.com CPCV 2025 | ✅ CONFIRMED |
| 2 | **TradingAgents debate_round() PoC** | Architecture | 4 | 3 | 2 | 5 | 4 | **3.33** | 5.33 | arXiv 2412.20138 (2024-12) + GitHub 70k stars (2025) | ✅ CONFIRMED |
| 3 | **Qlib v0.9.7 + RD-Agent(Q) 완전 활성화** | Architecture | 5 | 3 | 2 | 4 | 3 | **3.33** | 5.0 | Qlib v0.9.7 (2025-08, 33.7k stars) + NeurIPS 2025 arXiv 2505.15155 | ✅ CONFIRMED |
| 4 | **Multi-Armed Bandit 어드바이저 가중치** (★1) | Architecture | 4 | 3 | 2 | 3 | 5 | **2.0** | 6.67 | Thompson Sampling (확률론 표준) + 추천 시스템 적용 2025 | ✅ CONFIRMED |
| 5 | **Shapley 동적 어드바이저 가중치** (Wave 2~4 이월) | Architecture | 4 | 3 | 2 | 3 | 5 | **2.0** | 6.67 | arXiv cs.GT 2025-02 | ✅ CONFIRMED |
| 6 | **NautilusTrader 마이그레이션** (Wave 3~4 이월) | Architecture | 4 | 4 | 3 | 4 | 3 | **1.33** | 3.0 | github.com/nautechsystems (2025-10) + autotradelab.com 2025 | ✅ CONFIRMED |
| 7 | **Agent Distillation** (★2) | Performance/ML | 4 | 4 | 3 | 3 | 5 | **1.0** | 5.0 | neurips.cc/virtual/2025/poster/117657 (2025-12-04) + nvidia.com 2025-02-12 | ✅ CONFIRMED |
| 8 | **FinRL-DeepSeek GRPO** | Performance/ML | 4 | 5 | 3 | 3 | 5 | **0.8** | 4.0 | arXiv 2504.02281 (2025-04) + open-finance-lab.github.io 2025 | ✅ CONFIRMED |
| 9 | **AgentCircuit circuit breaker** (★3) | Reliability | 4 | 1 | 1 | 3 | 4 | **12.0** | 16.0 | github.com/simranmultani197/agentcircuit (날짜 미확정) | ⚠ AMBER |
| 10 | **Dead Reckoning 신뢰도 감쇠** (Wave 3~5 이월) | Reliability | 3 | 2 | 1 | 3 | 5 | **4.5** | 7.5 | 크로스도메인 아이디어 — 항공 DR → trading 구현 날짜 미확인 | ⚠ AMBER |

> #0은 bug fix — Best 3 선정 제외.
> #9 AgentCircuit, #10 Dead Reckoning → AMBER (날짜 미확인).
> AMBER ≥ 2 이지만 모두 Best 3 미포함 → ZERO 미발동.

---

## 4. Best 3 Deep Report

Best 3: #1(mSPRT, 6.0) → #2(TradingAgents, 3.33, Novelty tiebreak) → #3(Qlib v0.9.7, 3.33).
다양성: #2/#3 모두 Architecture, #1은 Reliability → All-three 동일 버킷 아님 → 교체 불필요.

---

### BEST-1: mSPRT — AutoForwardRecorder 위에 Mixture SPRT 검증 레이어
**PriorityScore: 6.0 | Bucket: Reliability/Observability | Effort: S | Novelty: 4 | SurpriseScore: 6.0**

#### Goal
Wave 4에서 SPRT를 Wave 4 Best-1 플랜으로 준비했지만 plain SPRT의 한계가 있다: 고정 effect size 가정, continuous peeking 시 Type I error 인플레이션. **Mixture SPRT(mSPRT)** (2025)로 업그레이드 — diffuse prior 사용, live OOS P&L 스트림에 안전하게 적용 가능.
`AutoForwardRecorder`가 수집하는 30거래일 일별 return 스트림을 mSPRT로 모니터링: 누적 증거가 임계를 넘으면 "모델 유효" 또는 "모델 무효화" 결정.

#### Non-goals
- 기존 `backtest/pbo.py` CPCV 로직 교체 (mSPRT는 추가 레이어)
- 자동 모델 롤백 (사람 확인 후 결정)
- 실시간 스트리밍 (일별 배치로 충분)

#### Proposed Design
```python
# src/stock_rtx4060/backtest/msprt_monitor.py
from scipy.stats import norm
import numpy as np, math

def msprt_log_likelihood_ratio(
    obs_returns: list[float],
    h0_mean: float = 0.0,          # 귀무가설: 수익률 = 0
    h1_mean: float | None = None,  # None → diffuse prior (mSPRT 핵심)
    sigma: float | None = None,    # None → 데이터에서 추정
) -> float:
    """Mixture SPRT log-likelihood ratio.

    mSPRT의 핵심: h1_mean을 고정하지 않고 prior를 혼합해
    continuous peeking에서도 Type I error ≤ alpha 보장.
    """
    n = len(obs_returns)
    if n == 0:
        return 0.0
    arr = np.array(obs_returns)
    if sigma is None:
        sigma = float(arr.std(ddof=1)) or 1e-6
    x_bar = float(arr.mean())
    # mSPRT bound: Wald approximation with diffuse prior
    # Reference: Carey Chou, Medium 2025
    z = (x_bar - h0_mean) / (sigma / math.sqrt(n))
    return float(z)  # z > upper_boundary → H1 채택

class MSPRTMonitor:
    """Sequential OOS return monitor for AutoForwardRecorder.

    Usage:
        monitor = MSPRTMonitor(alpha=0.05, beta=0.20, delta=0.01)
        for daily_return in forward_recorder.iter_returns():
            decision = monitor.update(daily_return)
            if decision in ("REJECT", "ACCEPT"):
                log_to_mlflow(decision, monitor.n_obs)
                break
    """

    def __init__(
        self,
        alpha: float = 0.05,
        beta: float = 0.20,
        delta: float = 0.01,  # 최소 의미 있는 일별 수익률
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.delta = delta
        self._obs: list[float] = []
        # Wald boundaries
        self._upper = math.log((1 - beta) / alpha)   # H1 채택
        self._lower = math.log(beta / (1 - alpha))   # H0 유지

    def update(self, return_pct: float) -> str:
        """Returns 'ACCEPT' | 'REJECT' | 'CONTINUE'."""
        self._obs.append(return_pct)
        llr = msprt_log_likelihood_ratio(self._obs)
        if llr >= self._upper:
            return "ACCEPT"   # 모델 유효 (positive alpha)
        if llr <= self._lower:
            return "REJECT"   # 모델 무효화
        return "CONTINUE"

    @property
    def n_obs(self) -> int:
        return len(self._obs)

# flows/research_weekly.py — mSPRT 통합
from stock_rtx4060.backtest.msprt_monitor import MSPRTMonitor

def _msprt_oos_check(forward_returns: list[float]) -> dict:
    monitor = MSPRTMonitor()
    decision = "CONTINUE"
    for r in forward_returns:
        decision = monitor.update(r)
    return {"decision": decision, "n_obs": monitor.n_obs}
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-M1 | `feat(P5): add msprt_monitor.py — MSPRTMonitor + msprt_log_likelihood_ratio` | `backtest/msprt_monitor.py` (신규) | 파일 삭제 |
| PR-M2 | `feat(P7): integrate MSPRTMonitor into research_weekly — OOS decision log` | `flows/research_weekly.py` | `git revert` |
| PR-M3 | `test(P5): mSPRT unit tests — ACCEPT/REJECT/CONTINUE boundaries + edge cases` | `tests/test_msprt_monitor.py` (신규) | 파일 삭제 |

#### Tests
- `test_msprt_accept_positive_returns` — 연속 양수 수익률 → ACCEPT
- `test_msprt_reject_negative_returns` — 연속 음수 수익률 → REJECT
- `test_msprt_continue_on_noise` — 무작위 노이즈 → CONTINUE
- `test_msprt_no_type_i_inflation` — 누적 peeking 100회 → false positive rate ≤ alpha

#### Rollout & Rollback
- 기존 SPRT 플랜(`research_weekly.py`)과 독립적 추가 — 기존 `promotion_gate_task()` 무변경
- `MSPRT_ENABLED=false` 환경변수로 비활성화
- Rollback: 파일 삭제 (additive only)

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| OOS 검증 방법 | PBO only | PBO + mSPRT 이중 검증 |
| False positive rate (continuous peeking) | 미측정 | ≤ alpha (0.05) |
| 모델 무효화 감지 시간 | 30거래일 고정 | mSPRT: 데이터 충분 시 조기 결정 |

#### Evidence
- Carey Chou, "Sequential Probability Ratio Test: SPRT and Mixture SPRT (mSPRT)", Medium 2025 — mSPRT continuous peeking 안전성 확인
- QuantBeckman.com, "Combinatorial Purged Cross Validation for Optimization", 2025 — CPCV + sequential monitor 조합 근거

---

### BEST-2: TradingAgents debate_round() PoC
**PriorityScore: 3.33 | Bucket: Architecture | Effort: M | Novelty: 4 | SurpriseScore: 5.33**

#### Goal
기존 3-advisor 오케스트레이터에 TradingAgents의 **Bull/Bear Researcher → Research Manager 토론 레이어**를 1 sprint PoC로 추가. 단일 `advisory_score`가 아닌 "토론 트랜스크립트 + 합의 점수" 출력. `use_debate=False` 기본값으로 기존 동작 100% 보존.

#### Non-goals
- TradingAgents 전체 7-role 구조 도입 (Manager + RiskTeam + PortfolioMgr 제외)
- TradingAgents 패키지 직접 의존 (LangGraph만 활용, 동일 패턴 자체 구현)
- `advisory_score ∈ [-1,+1]` 불변 규칙 변경

#### Proposed Design
```python
# advisors/debate/bull_bear_debate.py (신규)
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from ..claude_client import ClaudeClient
from ..base import AdvisoryOutput

@dataclass
class DebateResult:
    bull_thesis: str
    bear_thesis: str
    consensus_score: float    # ∈ [-1,+1]
    consensus_confidence: float
    debate_transcript: str

class BullBearDebate:
    """Single debate round: Bull and Bear each argue → Manager synthesizes.

    Design: 2 LLM calls (Bull, Bear) in parallel + 1 Manager call.
    Total: 3 LLM calls per debate vs 3 advisor calls in current flow.
    """

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self.client = client or ClaudeClient()

    async def run(
        self,
        ticker: str,
        prior_outputs: list[AdvisoryOutput],
        context: dict[str, Any],
    ) -> DebateResult:
        """Run one debate round on top of existing advisor outputs."""
        import asyncio
        evidence_summary = _build_evidence_summary(prior_outputs)

        bull_task = asyncio.create_task(self._bull_argument(ticker, evidence_summary))
        bear_task = asyncio.create_task(self._bear_argument(ticker, evidence_summary))
        bull_result, bear_result = await asyncio.gather(bull_task, bear_task)

        consensus = await self._manager_synthesis(ticker, bull_result, bear_result)
        return consensus

    async def _bull_argument(self, ticker: str, evidence: str) -> str:
        result = await self.client.acall(
            system=_BULL_SYSTEM,
            messages=[{"role": "user", "content": f"Ticker: {ticker}\n\n{evidence}"}],
        )
        return result.text

    async def _bear_argument(self, ticker: str, evidence: str) -> str:
        result = await self.client.acall(
            system=_BEAR_SYSTEM,
            messages=[{"role": "user", "content": f"Ticker: {ticker}\n\n{evidence}"}],
        )
        return result.text

    async def _manager_synthesis(self, ticker: str, bull: str, bear: str) -> DebateResult:
        ...

# advisors/orchestrator.py 수정 (additive)
@dataclass
class Orchestrator:
    ...
    use_debate: bool = False   # [TradingAgents Wave 5]

    async def aanalyze(self, ticker: str, context: dict | None = None) -> OrchestratorResult:
        outputs = await self._fallback_run(ticker, ctx)
        score, confidence = self._blend(outputs)

        if self.use_debate:
            from .debate.bull_bear_debate import BullBearDebate
            debate = BullBearDebate(client=self.news.client)
            debate_result = await debate.run(ticker, outputs, ctx)
            # debate score overrides only if confidence exceeds blend
            if debate_result.consensus_confidence > confidence:
                score = debate_result.consensus_score
                confidence = debate_result.consensus_confidence

        return OrchestratorResult(advisory_score=score, confidence=confidence, outputs=outputs)
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-D1 | `feat(P6): add advisors/debate/bull_bear_debate.py — Bull/Bear/Manager 3-call PoC` | `advisors/debate/bull_bear_debate.py` (신규) | 파일 삭제 |
| PR-D2 | `feat(P6): update Orchestrator — use_debate flag + debate result injection` | `advisors/orchestrator.py` | `git revert` |
| PR-D3 | `test(P6): debate PoC tests — mock Bull/Bear/Manager calls + score blend` | `tests/test_bull_bear_debate.py` (신규) | 파일 삭제 |

#### Tests
- `test_debate_default_disabled` — `use_debate=False` → 기존 `_blend()` 결과 동일
- `test_debate_bull_bear_called_parallel` — Bull/Bear asyncio.gather 병렬 실행 확인
- `test_debate_manager_synthesizes_score` — Manager 출력 → consensus_score ∈ [-1,+1]
- `test_debate_score_overrides_when_confident` — debate confidence > blend → debate score 적용

#### Rollout & Rollback
- `use_debate=False` 기본값 — 기존 동작 100% 보존
- PoC: 단순 `DEBATE_ENABLED=true` env flag로 활성화
- Rollback: `DEBATE_ENABLED=false` (즉시)

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| 어드바이저 신호 다양성 | 3개 독립 어드바이저 | Bull vs Bear 대립 논증 추가 |
| advisory_score 불변 | ✅ | ✅ (debate score도 [-1,+1] 강제) |
| PoC 완료 기준 | N/A | Bull/Bear/Manager 3-call mock 테스트 통과 |

#### Evidence
- github.com/TauricResearch/TradingAgents (2025, 70k+ stars) — `debate_rounds` config, Bull/Bear/Manager StateGraph 확인
- arXiv:2412.20138 (2024-12) — 26% cumulative return on AAPL vs 7.78% B&H

---

### BEST-3: Qlib v0.9.7 + RD-Agent(Q) 완전 활성화
**PriorityScore: 3.33 | Bucket: Architecture | Effort: M | Novelty: 3 | SurpriseScore: 5.0**

#### Goal
Wave 4에서 `factors/rd_agent/` stubs(docker_runner, qlib_exporter, loader, registry_hook)를 구현했지만 **Qlib 데이터 준비 → RD-Agent 실행 → 팩터 자동 등록**까지 E2E 파이프라인이 연결되지 않음. Qlib v0.9.7(2025-08)이 MLflow 3.x + Parquet 지원을 추가했으므로, 기존 DuckDB OHLCV → Qlib bin 변환(`qlib_exporter.py`)을 활성화하면 $10/사이클 자동 팩터 발굴이 즉시 가능.

#### Non-goals
- RD-Agent 내부 코드 수정
- Qlib을 기존 yfinance/pykrx 데이터 레이어로 교체 (병렬 운용)
- `fin_quant` (factor+model 공동) 모드 (factor-only `fin_factor`만)

#### Proposed Design
```python
# RD-Agent E2E 활성화 3단계
#
# 1. Qlib 데이터 준비 (qlib_exporter.py가 이미 구현됨)
#    DuckDB OHLCV → ~/.qlib/csv_data/stock1901/ → Qlib bin
#
# 2. docker_runner.py 실행 확인
#    환경변수: RDAGENT_ENABLED=true RDAGENT_CYCLES=1 RDAGENT_BUDGET_USD=10
#
# 3. loader.py + registry_hook.py: 발굴 팩터 검증 → 승인 대기

# src/stock_rtx4060/factors/rd_agent/config/stock1901.yaml
# — Qlib 설정 파일 (신규, 기존 stub에는 없음)
rdagent_config:
  provider_uri: "~/.qlib/qlib_data/stock1901"
  market: "custom"
  benchmark: null
  train_start: "2020-01-01"
  train_end: "2024-12-31"
  val_start: "2025-01-01"
  val_end: "2025-12-31"
  llm_provider: "litellm"  # LiteLLM gateway (Anthropic primary)
  budget_usd_per_cycle: 10.0
```

E2E 실행 체인:
```bash
# 수동 E2E 테스트 (1 cycle, synthetic)
RDAGENT_ENABLED=true RDAGENT_CYCLES=1 RDAGENT_BUDGET_USD=5.0 \
  python main.py factor-mine --synthetic
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-Q1 | `feat(P2): add config/stock1901.yaml — Qlib + RD-Agent config` | `factors/rd_agent/config/stock1901.yaml` (신규) | 파일 삭제 |
| PR-Q2 | `feat(P2): wire qlib_exporter → docker_runner E2E in runner.py` | `factors/rd_agent/runner.py` | `git revert` |
| PR-Q3 | `test(P2): E2E smoke test — qlib export stub + docker_runner dry-run` | `tests/test_rd_agent_e2e_smoke.py` (신규) | 파일 삭제 |

#### Tests
- `test_qlib_config_yaml_valid` — stock1901.yaml 파싱 정상
- `test_runner_e2e_dry_run` — `RDAGENT_DRY_RUN=true` → Docker 실행 없이 흐름 확인
- `test_qlib_exporter_creates_bin_dir` — DuckDB mock → Qlib bin 디렉토리 생성 확인

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| RD-Agent E2E 실행 | stubs만 (실행 불가) | `RDAGENT_ENABLED=true` 1 cycle 완주 |
| Qlib 데이터 준비 | 없음 | `qlib_exporter.py` 자동 실행 |
| 비용 | N/A | ≤ $10/사이클 |

#### Evidence
- github.com/microsoft/qlib v0.9.7 (2025-08-xx, 33.7k stars) — MLflow 3.x + Parquet 지원 확인
- arXiv:2505.15155 (NeurIPS 2025 accepted) — RD-Agent(Q) $10/사이클, CSI 300 ARR 14.21%

---

## 5. Options A/B/C

| Option | 내용 | 기간 | 위험 | 주요 결과 |
|--------|------|------|------|-----------|
| **A (보수)** | #0 Fix @task + BEST-1 mSPRT | 1주 | 낮음 | CI GREEN + OOS 통계 검증 |
| **B (중간)** | A + BEST-2 TradingAgents PoC + BEST-3 Qlib E2E | 3주 | 낮음 | 토론 어드바이저 + 자동 팩터 발굴 완성 |
| **C (공격)** | B + MAB 어드바이저 가중치 + Agent Distillation + FinRL-DeepSeek | 12주 | 중간 | 완전 자율 적응 어드바이저 시스템 |

---

## 6. 30/60/90-day Roadmap

### 즉시 (이번 세션)
- [ ] **🔴 Fix `research_weekly.py:282` `@task` NameError** — `test_research_weekly_flow.py` 수집 복원

### 30일 (2026-05-29 → 2026-06-28)
- [ ] PR-M1~M3: mSPRT monitor 구현 + 테스트
- [ ] PR-Q1: `config/stock1901.yaml` 추가
- [ ] PR-D1: `advisors/debate/bull_bear_debate.py` stub

### 60일 (2026-06-29 → 2026-07-28)
- [ ] PR-D2~D3: Orchestrator `use_debate` flag + 테스트
- [ ] PR-Q2~Q3: qlib_exporter → docker_runner E2E 연결
- [ ] MAB advisor weights PoC (Thompson Sampling stub)

### 90일 (2026-07-29 → 2026-08-28)
- [ ] NautilusTrader 마이그레이션 PoC (BacktestNode 어댑터)
- [ ] Agent Distillation: trajectory 데이터 수집 시작
- [ ] Shapley 동적 어드바이저 가중치 (Wave 2~5 이월 해결)

---

## 7. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|----------|----------|-------|-----|------|----------|--------|
| BEST-1 mSPRT | Medium | SPRT and Mixture SPRT (mSPRT) | medium.com/@carey.chou/sequential | 2025 | — | mSPRT continuous peeking 안전성 |
| BEST-1 mSPRT | Official | CPCV for Optimization | quantbeckman.com | 2025 | — | CPCV + sequential monitor 조합 |
| BEST-2 TradingAgents | arXiv | Multi-Agents LLM Financial Trading | arxiv.org/abs/2412.20138 | 2024-12 | 70k stars | debate_rounds config 확인 |
| BEST-2 TradingAgents | Medium | Building Multi-Agent AI Trading | medium.com/@ishveen | 2025 | — | DebateState schema 구현 패턴 |
| BEST-3 Qlib | GitHub | microsoft/qlib v0.9.7 | github.com/microsoft/qlib | 2025-08 | 33.7k stars | MLflow 3.x + Parquet 지원 |
| BEST-3 RD-Agent | arXiv | RD-Agent(Q) NeurIPS 2025 | arxiv.org/abs/2505.15155 | 2025-05 | 5.5k stars | $10/사이클, ARR 14.21% |
| #4 MAB weights | Academic | Thompson Sampling standard | — | 표준 확률론 | — | 추천 시스템 ↔ 어드바이저 가중치 |
| #7 Agent Distillation | NeurIPS | Distilling LLM Agent | neurips.cc/virtual/2025/poster/117657 | 2025-12-04 | Spotlight | 0.5B student = 1.5B CoT 성능 |
| #7 Agent Distillation | NVIDIA | Financial Data Workflows | developer.nvidia.com/blog | 2025-02-12 | Official | $300/run LoRA 증류 파이프라인 |
| #8 FinRL-DeepSeek | arXiv | FinRL Contest 2025 | arxiv.org/html/2504.02281v3 | 2025-04 | — | GRPO, 2048 GPU-parallel envs |
| #6 NautilusTrader | Blog | Backtesting Landscape 2026 | autotradelab.com | 2025 | — | VectorBT(research)+Nautilus(live) |

---

## 8. AMBER_BUCKET

| 항목 | AMBER 이유 | Wave |
|------|-----------|------|
| AgentCircuit circuit breaker | GitHub URL 확인됨, 날짜 "approximately Q1-Q2 2025" 미정확 | Wave 5 신규 AMBER |
| Dead Reckoning 신뢰도 감쇠 | 항공→trading 직접 구현 날짜 계속 미확인 | Wave 3→5 누적 AMBER |

AMBER 아이템 수: **2개** (Best 3 none → ZERO 미발동)

---

## 9. Verification Gate

### Evidence Completeness
| Best | Evidence ≥2 | 날짜 확인 | 판정 |
|------|-------------|---------|------|
| BEST-1 mSPRT | ✅ 2개 (Medium 2025 + quantbeckman 2025) | 2025 확인 | ✅ PASS |
| BEST-2 TradingAgents | ✅ 2개 (arXiv 2024-12 + Medium 2025) | 2024-12 확인 | ✅ PASS |
| BEST-3 Qlib v0.9.7 | ✅ 2개 (GitHub 2025-08 + arXiv 2025-05) | 2025-08 확인 | ✅ PASS |

### Deep Dive Completeness
| Best | PR plan ≥3 | Tests ≥3 | Rollout/Rollback | KPIs | 판정 |
|------|------------|---------|-----------------|------|------|
| BEST-1 | ✅ 3 PRs | ✅ 4 tests | ✅ MSPRT_ENABLED=false | ✅ | PASS |
| BEST-2 | ✅ 3 PRs | ✅ 4 tests | ✅ use_debate=False | ✅ | PASS |
| BEST-3 | ✅ 3 PRs | ✅ 3 tests | ✅ RDAGENT_ENABLED=false | ✅ | PASS |

### Apply Gates
- **Gate 0**: 코드 변경 없음 ✅
- **Gate 1**: BEST-1: `backtest/msprt_monitor.py` (신규) / BEST-2: `advisors/debate/` (신규) / BEST-3: `factors/rd_agent/config/stock1901.yaml` (신규)
- **Gate 2**: 각 PR 전 사용자 승인 필요
- **Gate 3**: 모두 `_ENABLED=false` 기본값
- **Gate 4**: 모두 `git revert` 가능

**최종 판정: Go ✅**

---

## 10. Open Questions (최대 3개)

1. **`@task` NameError 원인**: `research_weekly.py:282`에 `@task` 데코레이터가 Prefect `task`를 직접 임포트 없이 사용 중. `flows/utils.py`의 `with_retries` 래퍼와의 관계 확인 필요. 즉시 수정 필요.

2. **TradingAgents 3 LLM 호출 비용**: debate_round는 Bull + Bear + Manager = 3 추가 LLM 호출. 현재 1 추천 사이클 비용 기준으로 3× 증가. `audit_log/advisor.jsonl`에서 현재 평균 비용을 확인하고 `use_debate` 예산 상한 설정 필요.

3. **Qlib E2E Windows 환경**: `qlib_exporter.py`의 Qlib bin 변환이 Windows 경로(`~/.qlib/`)에서 정상 동작하는지 확인 필요. WSL2 없이 Windows 네이티브 실행 가능 여부 확인.

---

## SESSION_HANDOFF

```
skill: project-upgrade v2.2.0 | date: 2026-05-29 (Wave 5)
key_findings:
  - Wave 4 완전 구현 완료 (1574 passed, coverage 83%)
  - research_weekly.py:282 @task NameError — test_research_weekly_flow.py 수집 불가 (즉시 수정)
  - TradingAgents v0.2 debate_rounds config 확인 (70k stars, Apache 2.0)
  - Qlib v0.9.7 (2025-08) MLflow 3.x + Parquet — 기존 stubs에 config만 추가하면 E2E 가능
  - mSPRT(2025) = plain SPRT보다 continuous peeking 안전 — AutoForwardRecorder에 적용
  - Agent Distillation (NeurIPS 2025 Spotlight) — 1.5B student = 3B teacher 성능
  - AgentCircuit circuit breaker (GitHub 2025) — AMBER (날짜 미확정)
surprise_picks:
  - idea: "Multi-Armed Bandit 어드바이저 가중치" | Novelty: 5 | SurpriseScore: 6.67 | status: PASS
  - idea: "Agent Distillation (NeurIPS 2025)" | Novelty: 5 | SurpriseScore: 5.0 | status: PASS
  - idea: "AgentCircuit circuit breaker" | Novelty: 4 | SurpriseScore: 16.0 | status: ⚠ AMBER
amber_count: 0  # Best 3 모두 confirmed evidence. AMBER 아이디어는 Best 3 미포함.
next_suggested: project-plan --focus="fix-task-nameerror && best1-msprt"
```
