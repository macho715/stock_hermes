# PLAN_DOC — Dashboard Wave 4 UI: TFT Score + Regime Badge + Model Scores
**v1.0 | 2026-05-29 | skill: project-plan v2.2 | project: stock_1901 / stock_rtx4060**

---

## A. Executive Summary

### 목표
Wave 4에서 백엔드에만 존재하는 3개 새 신호(`tft_prob`, `advisor_regime`, `model_kind_used`)를 추천 카드에 표시한다. 모든 변경은 **additive** — 기존 카드 레이아웃/스키마를 변경하지 않고 조건부 렌더링으로 새 요소를 추가한다.

### 데이터 흐름 갭 (현황 진단)

```
EnsemblePredictor.predict()
  → { direction_prob, tft_prob ✅, main_prob ✅, model_kind ✅ }
        ↓
recommendation_engine.py — RecommendationResult
  → direction_prob ✅ | advisor_score ✅ | tft_prob ❌ | advisor_regime ❌
        ↓
dashboard_bridge.py — _build_candidate()
  → advisor_score ✅ | tft_prob ❌ | advisor_regime ❌ | market_regime_score ❌
        ↓
dashboard_snapshot.json
        ↓
RecommendationCard.jsx
  → LLM Advisor bar ✅ | RegimeBadge ❌ | ModelScoresStrip ❌
```

**3개 갭 모두 수정 필요:**
1. `RecommendationResult`에 `tft_prob`, `advisor_regime`, `model_kind_used` 필드 추가
2. `dashboard_bridge.py`에 3개 필드 통과
3. `RecommendationCard.jsx`에 `RegimeBadge` + `ModelScoresStrip` 컴포넌트 추가

### KPI

| Metric | 현재 | 목표 |
|--------|------|------|
| 카드에 표시되는 모델 점수 | direction_prob 1개 | main_prob + tft_prob 2개 (TFT_MODEL_ENABLED 시) |
| 시장 체제 시각화 | 없음 | RegimeBadge (risk_on/neutral/risk_off) |
| 기존 카드 레이아웃 변경 | N/A | 변경 없음 — additive only |
| 기존 테스트 통과율 | 1643/1643 | 동일 유지 |

### 범위
- **In-scope**: `RecommendationResult` additive 필드, `dashboard_bridge.py` passthrough, `RecommendationCard.jsx` 2개 신규 컴포넌트
- **Out-of-scope**: OpenBB tool call 이력 표시, SPRT 결과 per-card 표시(SPRT는 모델 레벨, 후속 작업), AMH 메모리 세부 내역

### 마일스톤

| 마일스톤 | 기간 | 완료 기준 |
|----------|------|-----------|
| M1: 백엔드 파이프라인 연결 | Day 1~2 | `tft_prob` + `advisor_regime` → snapshot JSON 확인 |
| M2: React 컴포넌트 추가 | Day 2~3 | 카드에 RegimeBadge + ModelScoresStrip 렌더링 |
| M3: 테스트 + CI | Day 3~4 | 신규 테스트 통과, 기존 1643 유지 |

---

## B. Context & Requirements

### B1. 문제 정의

**백엔드 신호가 화면에 없음:**

```
Wave 4 구현 결과:
  TFT stub → EnsemblePredictor.predict()['tft_prob'] = 0.5 (stub)
  AMH Memory → MacroRegimeAgent → AdvisoryOutput.regime_label = 'risk_off'

사용자가 보는 것:
  LLM ADVISOR: +0.31  ← advisor_score만 보임
  regime_label = 'risk_off' ← 완전히 숨겨져 있음
  tft_prob = 0.5 ← 완전히 숨겨져 있음
```

### B2. 기능 요구사항

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-1 | `RecommendationResult`에 `tft_prob: float | None = None` 추가 (additive) | P0 |
| FR-2 | `RecommendationResult`에 `advisor_regime: str | None = None` 추가 (additive) | P0 |
| FR-3 | `RecommendationResult`에 `model_kind_used: str | None = None` 추가 (P3 출처) | P1 |
| FR-4 | `dashboard_bridge.py` → 3개 신규 필드 passthrough | P0 |
| FR-5 | `RegimeBadge` 컴포넌트: risk_on(초록)/neutral(회색)/risk_off(빨강) | P0 |
| FR-6 | `ModelScoresStrip` 컴포넌트: main_prob + tft_prob 2열 표시 (TFT 0.5면 회색) | P1 |
| FR-7 | 필드 없을 때 컴포넌트 미표시 (graceful null handling) | P0 |
| FR-8 | 기존 `advisor_score` LLM 바 레이아웃 변경 없음 | P0 |

### B3. 비기능 요구사항

| ID | 요구사항 |
|----|----------|
| NFR-1 | `RecommendationResult`는 additive — `to_dict()` 자동 포함 |
| NFR-2 | `dashboard_snapshot.v1` schema_version 유지 (additive fields) |
| NFR-3 | `screening_output_only=True` 불변 |
| NFR-4 | 카드 높이 증가 최소화 (RegimeBadge: 1행, ModelScoresStrip: 1행) |

---

## C. UI/UX Plan

### C1. 변경 후 카드 레이아웃

```
┌──────────────────────────────────────────────────┐
│ 005930  [GREEN] [PBO: ✅]              87  SCORE  │
│ Track-S                                           │
│ Prob: 0.73   EV: +3.2%                           │  ← 기존
│ ┌────────┬────────┬────────┐                      │
│ │ ENTRY  │  STOP  │  TP2   │                      │  ← 기존
│ │ 74,800 │ 71,800 │ 82,300 │                      │
│ └────────┴────────┴────────┘                      │
│ R/R: 2.5   Max Pos: 8.0%   Qty: 13              │  ← 기존
│ ──────────────────────────────────────────────── │
│ REGIME  [risk_off 🔴]                             │  ← 신규 RegimeBadge
│ ──────────────────────────────────────────────── │
│ ▌▌▌▌▌▌▌▌▌▌▌│▌▌▌▌ LLM ADVISOR  +0.31            │  ← 기존 (변경 없음)
│ "긍정적 뉴스 흐름..."                             │
│ MAIN 0.73  TFT  0.71                              │  ← 신규 ModelScoresStrip
└──────────────────────────────────────────────────┘
```

### C2. RegimeBadge 디자인

```jsx
// 3가지 상태
risk_on  → 배경 #00FF8833, 텍스트 #00FF88, 라벨 "RISK ON ↑"
neutral  → 배경 #3F506088, 텍스트 #8899AA, 라벨 "NEUTRAL —"
risk_off → 배경 #FF336633, 텍스트 #FF3366, 라벨 "RISK OFF ↓"
```

### C3. ModelScoresStrip 디자인

```jsx
// TFT = 0.5 (stub) → 회색으로 표시 ("stub" 표기)
// TFT ≠ 0.5 → main_prob과 동일한 색상 규칙 (0.5 기준 초록/빨강)
MAIN 0.73  TFT  0.71   ← TFT trained (미래)
MAIN 0.73  TFT  0.50*  ← TFT stub (* = 미학습)
```

### C4. Screens (필수 테이블)

| Screen | 조건 | 표시 내용 |
|--------|------|----------|
| `advisor_regime = 'risk_off'` | OPENBB_TOOLS_ENABLED 여부 무관 | RegimeBadge 빨강 |
| `advisor_regime = 'risk_on'` | — | RegimeBadge 초록 |
| `advisor_regime = 'neutral'` | — | RegimeBadge 회색 |
| `advisor_regime = null` | — | RegimeBadge 미표시 |
| `tft_prob != null` | — | ModelScoresStrip 표시 |
| `tft_prob = null` | — | ModelScoresStrip 미표시 |

---

## D. System Architecture

### D1. 데이터 흐름 (변경 후)

```
EnsemblePredictor.predict()
  → { direction_prob, tft_prob, main_prob, model_kind }
        ↓
recommendation_engine.py — _run_single_ticker()
  → model_stats["tft_prob"] → RecommendationResult.tft_prob
  → model_stats["model_kind"] → RecommendationResult.model_kind_used

Orchestrator.aanalyze()
  → OrchestratorResult.outputs[macro_regime].regime_label
        ↓
recommendation_engine.py — _apply_advisor_blend()
  → extract regime_label from MacroRegimeAgent output
  → RecommendationResult.advisor_regime

dashboard_bridge.py — _build_candidate()
  → + tft_prob, advisor_regime, model_kind_used

RecommendationCard.jsx
  → RegimeBadge(advisor_regime)
  → ModelScoresStrip(main_prob, tft_prob)
```

### D2. 컴포넌트 경계

| 컴포넌트 | 책임 |
|----------|------|
| `RecommendationResult` (dataclass) | `tft_prob`, `advisor_regime`, `model_kind_used` 저장 |
| `_apply_advisor_blend()` | `regime_label` 추출 추가 |
| `dashboard_bridge._build_candidate()` | 3개 필드 passthrough |
| `RegimeBadge` (신규 React) | regime_on/neutral/off 시각화 |
| `ModelScoresStrip` (신규 React) | main + tft 확률 2열 표시 |

---

## E. Data Model & API Contract

### E1. RecommendationResult 확장 (additive)

```python
# src/stock_rtx4060/recommendation_engine.py
@dataclass
class RecommendationResult:
    # ... 기존 필드 변경 없음 ...
    advisor_score: float | None = None
    advisor_rationale: str | None = None
    # [Wave 4 Dashboard] 신규 optional 필드 — None = 미사용/미계산
    tft_prob: float | None = None          # TFT 4th model probability
    advisor_regime: str | None = None      # MacroRegime 출력 (risk_on/neutral/risk_off)
    model_kind_used: str | None = None     # 실제 사용된 모델 종류
```

`to_dict()` → `asdict(self)` 자동 포함 (기존 동작 그대로).

### E2. dashboard_bridge passthrough

```python
# src/stock_rtx4060/dashboard_bridge.py — _build_candidate()에 추가
"tft_prob": result.get("tft_prob"),
"advisor_regime": result.get("advisor_regime"),
"model_kind_used": result.get("model_kind_used"),
```

### E3. React Props

```typescript
// RecommendationCard.jsx — result 객체 신규 필드
result.tft_prob:      number | null   // 0.0 ~ 1.0
result.advisor_regime: string | null  // "risk_on" | "neutral" | "risk_off"
result.model_kind_used: string | null // "lightgbm" | "xgb" | "logistic"
```

---

## F. Repo/Package Structure

```
src/stock_rtx4060/
  recommendation_engine.py       ← RecommendationResult additive 필드 + 추출 로직
  dashboard_bridge.py            ← _build_candidate() 3개 필드 추가

root_folder_snapshot/stock-pred-v5/src/components/
  RecommendationCard.jsx         ← RegimeBadge + ModelScoresStrip 컴포넌트 추가

tests/
  test_dashboard_bridge.py       ← tft_prob/advisor_regime passthrough 테스트
  test_recommendation_result.py  ← 신규 필드 additive 호환 테스트
```

---

## G. Implementation Plan

### G0. Why This Works (Cross-Domain: 의료 모니터링 대시보드 → 금융 카드)

ICU 모니터링 화면은 "vital signs strip" 패턴을 쓴다: 중요 지표를 주 화면에 방해하지 않는 작은 배지로 표시하고, 정상 범위면 회색, 이상이면 빨강으로 색을 바꾼다. `RegimeBadge`와 `ModelScoresStrip`은 정확히 이 패턴이다 — 시장 체제(regime)를 배경색으로 표현하고, 모델 점수를 작은 strip으로 추가한다. 기존 추천 카드의 주요 정보(진입가/손절가/Target)를 방해하지 않으면서 맥락 신호를 제공한다.

### G1. Epics

| Epic | 제목 | 기간 |
|------|------|------|
| E1 | RecommendationResult 필드 추가 + 추출 로직 | Day 1 |
| E2 | dashboard_bridge passthrough | Day 1 |
| E3 | RegimeBadge React 컴포넌트 | Day 2 |
| E4 | ModelScoresStrip React 컴포넌트 | Day 2 |
| E5 | 테스트 + CI | Day 3~4 |

### G2. Stories

**E1: 백엔드 필드 추가**
- S1.1: `RecommendationResult` dataclass에 3개 optional 필드 추가 (끝에, default=None)
- S1.2: `_apply_advisor_blend()` — `OrchestratorResult.outputs`에서 MacroRegime의 `regime_label` 추출
- S1.3: `_run_single_ticker()` — `model_stats.get("tft_prob")` + `model_stats.get("model_kind")` 저장

**E2: Bridge passthrough**
- S2.1: `_build_candidate()` 끝 부분에 3개 필드 추가 (4줄)

**E3: RegimeBadge**
- S3.1: `RegimeBadge` 함수 컴포넌트 작성 (PboBadge 패턴 참조)
- S3.2: LLM Advisor 섹션 *위에* RegimeBadge 배치 (결과 => 해석의 맥락 → 판단 순서)

**E4: ModelScoresStrip**
- S4.1: `ModelScoresStrip` 함수 컴포넌트 작성
- S4.2: LLM Advisor 섹션 *아래에* ModelScoresStrip 배치 (어드바이저 = TFT 포함 종합 의견)
- S4.3: `tft_prob == 0.5` 이면 `*` 표시로 stub 상태 명시

**E5: 테스트**
- S5.1: `test_dashboard_bridge.py` — `tft_prob=0.71`, `advisor_regime='risk_off'` → snapshot 포함 확인
- S5.2: `test_recommendation_result.py` — 기존 10개 필드만으로 생성 시 새 필드 `None` 확인

### G3. PR Plan

| PR | 번호 | 제목 | 파일 | 롤백 |
|----|------|------|------|------|
| PR-1 | `feat(P6): extend RecommendationResult — tft_prob + advisor_regime + model_kind_used` | `recommendation_engine.py` | `git revert` (additive) |
| PR-2 | `feat(P6): extract advisor_regime from MacroRegime output in _apply_advisor_blend` | `recommendation_engine.py` | `git revert` |
| PR-3 | `feat(P3): populate tft_prob + model_kind_used from model_stats in _run_single_ticker` | `recommendation_engine.py` | `git revert` |
| PR-4 | `feat(P0): add tft_prob + advisor_regime + model_kind_used to dashboard_bridge` | `dashboard_bridge.py` | `git revert` (4줄) |
| PR-5 | `feat(dashboard): add RegimeBadge + ModelScoresStrip to RecommendationCard` | `RecommendationCard.jsx` | `git revert` |
| PR-6 | `test: dashboard_bridge + RecommendationResult additive field tests` | `tests/test_dashboard_bridge.py`, `tests/test_recommendation_result.py` | 파일 삭제 |

### G4. Feature Flags

| 플래그 | 효과 |
|--------|------|
| `TFT_MODEL_ENABLED=false` (기본) | `tft_prob=None` → ModelScoresStrip 미표시 |
| `OPENBB_TOOLS_ENABLED=false` (기본) | `advisor_regime` 여전히 채워짐 (MacroRegime은 tools 없이도 동작) |
| `ADVISOR_MEMORY_ENABLED=false` (기본) | `advisor_regime` 여전히 채워짐 (regime_label은 AMH 메모리와 독립) |

### G5. 타임라인

```
Day 1:  PR-1 → PR-2 → PR-3 → PR-4 (백엔드 파이프라인)
Day 2:  PR-5 (React 컴포넌트)
Day 3:  PR-6 (테스트)
Day 4:  전체 스위트 검증 + push
```

---

## H. Testing Strategy

### H1. Test Pyramid

```
E2E (1개)
  └─ test_dashboard_bridge_wave4_fields.py::test_snapshot_includes_new_fields
       └─ mock recommendation → snapshot → tft_prob + advisor_regime 존재 확인

Unit (4개)
  ├─ test_recommendation_result_additive.py (기존 생성자 호환)
  ├─ test_apply_advisor_blend_regime_extraction.py
  ├─ test_dashboard_bridge_tft_passthrough.py
  └─ test_dashboard_bridge_regime_passthrough.py
```

### H2. 핵심 테스트 케이스

| 테스트 | 검증 |
|--------|------|
| `test_recommendation_result_no_new_fields` | 기존 필드만으로 생성 → `tft_prob=None`, `advisor_regime=None` |
| `test_recommendation_result_tft_prob_set` | `tft_prob=0.71` 설정 후 `to_dict()['tft_prob'] == 0.71` |
| `test_bridge_tft_prob_in_snapshot` | bridge → `result.get('tft_prob') == 0.71` |
| `test_bridge_advisor_regime_in_snapshot` | bridge → `result.get('advisor_regime') == 'risk_off'` |
| `test_bridge_none_fields_safe` | `tft_prob=None` → snapshot에 `null` (KeyError 없음) |
| `test_advisor_blend_extracts_regime_label` | MacroRegime output `regime_label='risk_off'` → result.`advisor_regime='risk_off'` |

### H3. CI Gates

```
기존 1643 tests PASS ✅
test_dashboard_bridge_wave4_fields PASS ✅
test_recommendation_result_additive PASS ✅
```

---

## I. Observability & Operations

### I1. 로그

```python
# recommendation_engine.py
logger.debug("advisor_regime=%s tft_prob=%s", advisor_regime, tft_prob)
```

### I2. 시각적 확인

```bash
# 스냅샷에 새 필드 확인
python main.py dashboard-export --recommendation-json reports/...json
cat reports/.../dashboard_snapshot.json | python -m json.tool | grep -E "tft_prob|advisor_regime"
```

### I3. 런북

```bash
# RegimeBadge 미표시 원인 확인
grep "advisor_regime" audit_log/advisor.jsonl | tail -5

# TFT_MODEL_ENABLED 확인
echo $TFT_MODEL_ENABLED  # false → tft_prob=null → ModelScoresStrip 미표시 (정상)
```

---

## J. Error Handling & Recovery

| 오류 | 처리 |
|------|------|
| `advisor_regime = None` (어드바이저 미실행) | RegimeBadge 미렌더링 (graceful null) |
| `tft_prob = None` (TFT 비활성) | ModelScoresStrip 미렌더링 |
| `tft_prob = 0.5` (stub) | `0.50*` 표시 (미학습 명시) |
| `OrchestratorResult.outputs` 빈 리스트 | `advisor_regime = None` safe |
| `model_stats.get("tft_prob")` KeyError | `.get()` 사용 → `None` safe |

---

## K. Dependencies, Security, Risks

### K1. 의존성

신규 외부 의존성 없음. 모두 기존 스택 내 변경.

### K2. Risk Register

| # | 위험 | 확률 | 영향 | 대응 |
|---|------|------|------|------|
| R1 | `RecommendationResult` additive 필드가 기존 테스트 깨짐 | 낮음 | 높음 | `default=None` + `test_recommendation_result_additive` CI 필수 |
| R2 | `dashboard_snapshot.v1` schema 오해 | 낮음 | 중간 | additive만 (schema_version 변경 없음) |
| R3 | React 렌더링 오류 (null 처리 누락) | 낮음 | 중간 | `result?.advisor_regime` optional chaining |
| R4 | `tft_prob = 0.5` stub을 실제 학습된 것으로 오해 | 중간 | 높음 | `0.50*` 표기 + tooltip "Stub — pytorch_forecasting not installed" |
| R5 | MacroRegime `regime_label` 추출 실패 | 낮음 | 낮음 | `advisor_regime = None` fallback |

### K3. Change Control

- `RecommendationResult`: additive only — `to_dict()` 자동 포함
- `dashboard_snapshot.v1`: additive only — schema_version 변경 없음
- `RecommendationCard.jsx`: additive only — 기존 요소 변경 없음

---

## ㅋ. Appendix

### ㅋ1. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|----------|----------|-------|-----|------|----------|--------|
| RegimeBadge 패턴 | Internal | 기존 PboBadge 컴포넌트 | RecommendationCard.jsx:6 | 2026 내부 | — | `{bg, color, label, icon}` config 패턴 동일 적용 |
| RegimeBadge 패턴 | Internal | 기존 KevpeBadge 컴포넌트 | KevpeBadge.jsx | 2026 내부 | — | regime 표시 선례 |
| ModelScoresStrip | Internal | SizingBadge 컴포넌트 | RecommendationCard.jsx:40 | 2026 내부 | — | 3열 grid 패턴 참조 |
| advisor_regime 출처 | Internal | MacroRegimeAgent.regime_label | macro_regime.py | 2026 내부 | — | Wave 4에서 추가된 필드 |
| tft_prob 출처 | Internal | EnsemblePredictor.predict()['tft_prob'] | ensemble_model.py | 2026 내부 | — | Wave 4 BEST-3에서 추가 |

### ㅋ2. AMBER_BUCKET

없음. 모두 내부 코드 근거.

### ㅋ3. 구현 코드 스케치

```python
# recommendation_engine.py — _apply_advisor_blend() 수정 (PR-2)
def _apply_advisor_blend(ticker, snap, cfg) -> tuple[float, str, float, str | None]:
    """Returns (advisor_score, rationale, blended_score, advisor_regime)."""
    # ... 기존 로직 ...
    advisor_regime: str | None = None
    if orch_result is not None:
        for out in orch_result.outputs:
            if out.agent == "macro_regime" and out.regime_label:
                advisor_regime = out.regime_label
                break
    return advisory_score, advisor_rationale, float(blended), advisor_regime
```

```python
# recommendation_engine.py — _run_single_ticker() 수정 (PR-3)
# 기존: direction_prob=round(float(model_stats["latest_prob"]), 4)
# 추가:
tft_prob = model_stats.get("tft_prob")  # None when TFT_MODEL_ENABLED=false
model_kind_used = model_stats.get("model_kind")  # "lightgbm" | "xgb" | ...
```

```python
# dashboard_bridge.py — _build_candidate() 추가 (PR-4, 3줄)
"tft_prob": result.get("tft_prob"),
"advisor_regime": result.get("advisor_regime"),
"model_kind_used": result.get("model_kind_used"),
```

```jsx
// RecommendationCard.jsx — RegimeBadge 컴포넌트 (PR-5)
const REGIME_CFG = {
  risk_on:  { bg: "#00FF8833", color: "#00FF88", label: "RISK ON ↑"  },
  neutral:  { bg: "#3F506088", color: "#8899AA", label: "NEUTRAL —"  },
  risk_off: { bg: "#FF336633", color: "#FF3366", label: "RISK OFF ↓" },
};

function RegimeBadge({ regime }) {
  if (!regime || !REGIME_CFG[regime]) return null;
  const cfg = REGIME_CFG[regime];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
      <span style={{ fontSize: 8, color: C.textMuted, letterSpacing: 1 }}>REGIME</span>
      <span style={{
        background: cfg.bg, color: cfg.color, borderRadius: 3,
        padding: "1px 7px", fontSize: "0.65rem", fontWeight: 700,
      }}>{cfg.label}</span>
    </div>
  );
}

// ModelScoresStrip 컴포넌트 (PR-5)
function ModelScoresStrip({ mainProb, tftProb }) {
  if (mainProb == null && tftProb == null) return null;
  const isStub = tftProb != null && Math.abs(tftProb - 0.5) < 0.001;
  return (
    <div style={{ display: "flex", gap: 12, marginTop: 4, fontSize: 8, color: C.textDim }}>
      {mainProb != null && (
        <span>MAIN <b style={{ color: C.text }}>{Number(mainProb).toFixed(2)}</b></span>
      )}
      {tftProb != null && (
        <span>TFT <b style={{ color: isStub ? C.textMuted : C.text }}>
          {Number(tftProb).toFixed(2)}{isStub ? "*" : ""}
        </b></span>
      )}
    </div>
  );
}
```

### ㅋ4. 용어집

| 용어 | 설명 |
|------|------|
| `advisor_regime` | MacroRegimeAgent가 판정한 시장 체제 레이블 (risk_on/neutral/risk_off) |
| `tft_prob` | TFT 4번째 모델의 방향성 확률 (0.5 = stub) |
| `model_kind_used` | 실제 학습에 사용된 주 모델 종류 |
| `0.50*` | TFT stub 상태 (pytorch_forecasting 미설치) |
| RegimeBadge | 시장 체제를 색상 뱃지로 표시하는 React 컴포넌트 |
| ModelScoresStrip | main_prob + tft_prob를 한 줄에 표시하는 React 컴포넌트 |

---

## Verification Gate

| Gate | 항목 | 상태 |
|------|------|------|
| Gate 0 (Dry-run) | 코드 변경 없음 | ✅ |
| Gate 1 (Evidence) | 내부 코드 직접 확인 (PboBadge 패턴, EnsemblePredictor 출력) | ✅ |
| Gate 2 (PR plan ≥6) | PR 6개 | ✅ |
| Gate 3 (Tests) | 6개 테스트 케이스 명세 | ✅ |
| Gate 4 (Rollout/Rollback) | all additive + `git revert` | ✅ |
| Gate 5 (KPI 정의) | 기존 1643 tests 유지, tft_prob/advisor_regime → snapshot | ✅ |
| Gate 6 (Safety) | `screening_output_only=True` 무변경, `schema_version` 유지 | ✅ |
| AMBER check | 없음 | ✅ ZERO 없음 |

**최종 판정: Go ✅**

### Apply Gates

- **Gate 0**: 현재 플랜 문서. 코드 수정 없음.
- **Gate 1**: 변경 파일 — `recommendation_engine.py` (3 PR), `dashboard_bridge.py` (1 PR), `RecommendationCard.jsx` (1 PR), 테스트 2개
- **Gate 2**: PR-1 전 사용자 승인 필요
- **Gate 3**: 모든 신규 필드 `default=None` → feature flag 불필요
- **Gate 4**: Rollback = `git revert` (additive changes)
