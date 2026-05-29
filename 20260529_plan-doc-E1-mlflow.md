# PLAN_DOC — E1: MLflow 3.x 업그레이드 (수정판)
**Skill:** project-plan v2.2.0 | **Date:** 2026-05-29
**Source:** Wave 3 Plan E1 + 코드베이스 재진단
**Branch:** `claude/upgrade-investment-system-2Mc7x`

---

## ⚡ 재진단 요약 (Wave 3 플랜과 차이점)

Wave 3 플랜에서 예상한 "3 PRs, 5일" 작업이 실제로는 **1 PR, 반나절**로 축소됩니다.

| 항목 | Wave 3 플랜 예상 | 실제 상태 (2026-05-29 코드 스캔) |
|------|----------------|-------------------------------|
| `requirements.in` | `>=2.16` → 변경 필요 | **`>=3.0,<4.0` 이미 작성됨** ✅ |
| `artifact_path` 마이그레이션 | `log_model()` 전수 교체 필요 | **`artifact_path=` 미사용** — 교체 불필요 ✅ |
| `_wrap_with_mlflow_span()` 구현 | 신규 구현 필요 | **이미 완전 구현됨** (claude_client.py:721) ✅ |
| `USE_MLFLOW_TRACING` flag | 신규 추가 필요 | **이미 `=false` 기본값으로 구현** ✅ |
| MLflow span 테스트 | 신규 작성 필요 | **`test_claude_client.py:452-511`에 존재** ✅ |
| **남은 작업** | 3 PRs | **`requirements.txt` 1줄 변경 + 테스트 확인** |

---

## A. Executive Summary

### A1. 목표
`requirements.txt`의 `mlflow>=2.16`을 `mlflow>=3.0,<4.0`으로 동기화한 뒤 전체 테스트 스위트가 MLflow 3.x와 호환됨을 CI에서 검증한다. 이후 `USE_MLFLOW_TRACING=true`로 이미 구현된 LLM advisor span tracing을 활성화할 수 있다.

### A2. 실제 KPI

| 지표 | 현재 | 목표 |
|------|------|------|
| `requirements.txt` mlflow 버전 | `>=2.16` | `>=3.0,<4.0` |
| `pip check` 결과 | 미확인 | 0 broken requirements |
| 전체 테스트 통과 | 346 passed | 346 passed (퇴보 없음) |
| `USE_MLFLOW_TRACING=true` 활성화 가능 | `false` 기본값으로 대기 중 | 활성화 가능 (코드 변경 불필요) |

### A3. 마일스톤

| # | 작업 | 예상 시간 |
|---|------|---------|
| **PR-M1** | `requirements.txt` 1줄 변경 + pip-compile + CI 통과 | 반나절 |
| **RUNBOOK** | `USE_MLFLOW_TRACING=true` 활성화 + 검증 | 30분 |

---

## B. Context & Requirements

### B1. 왜 `requirements.in`과 `requirements.txt`가 어긋났나?

`requirements.in`은 이미 Wave 3 구현 중에 업데이트된 것으로 보입니다. 하지만 `pip-compile`을 실행해 `requirements.txt`를 재생성하지 않아서 실제 설치 버전이 고정되지 않은 상태입니다.

```bash
# requirements.in (현재) — 이미 업데이트됨
mlflow>=3.0,<4.0   ✅

# requirements.txt (현재) — 구식
mlflow>=2.16        ⚠️ 재생성 필요
```

### B2. 이미 구현된 기능 (변경 불필요)

**`advisors/claude_client.py`** — `_wrap_with_mlflow_span()` 완전 구현:
```python
# 현재 코드 (변경 없이 사용 가능)
_USE_MLFLOW_TRACING: bool = os.environ.get("USE_MLFLOW_TRACING", "false").lower() in ("1", "true", "yes")

def _wrap_with_mlflow_span(self, *, ticker, messages, inner_result) -> CallResult:
    if not _USE_MLFLOW_TRACING:
        return inner_result
    try:
        import mlflow
        with mlflow.start_span(
            name="advisor_call",
            span_type="LLM",
            attributes={"ticker": ticker, "model": inner_result.model},
        ) as span:
            span.set_inputs({"message_count": len(messages)})
            span.set_outputs({
                "tokens_in": inner_result.tokens_in,
                "tokens_out": inner_result.tokens_out,
                "cost_usd": round(inner_result.cost_usd, 6),
            })
    except Exception:
        logger.debug("mlflow_span failed (optional), continuing")
    return inner_result
```

**`tests/test_claude_client.py:452-511`** — 테스트 이미 존재:
```python
# E1: USE_MLFLOW_TRACING feature flag — W3-B1
def test_mlflow_tracing_disabled_by_default(monkeypatch): ...
def test_mlflow_tracing_enabled_calls_mlflow_start_span(monkeypatch): ...
```

**`ml/registry.py`** — MLflow 3.x alias API 이미 처리:
```python
def promote(name, version, stage):
    try:
        client.transition_model_version_stage(...)   # 2.x 방식
    except Exception:
        alias = stage.lower()
        client.set_registered_model_alias(...)       # 3.x 방식 ✅
```

**`ensemble_model.py:572-576`** — `mlflow.log_input()` guard 이미 구현:
```python
if hasattr(mlflow, 'log_input'):   # 3.x에서 사용 가능 ✅
    input_ds = mlflow.data.from_pandas(X, targets=y, name="ensemble_train")
    mlflow.log_input(input_ds, context="training")
```

**`observability/mlflow_client.py:49`** — `log_artifact(artifact_path=...)`:
> ⚠️ 주의: 이 `artifact_path`는 `log_model(artifact_path=)`의 deprecated 파라미터가 아님.
> `mlflow.log_artifact(path, artifact_path=subdirectory)` — MLflow 3.x에서도 유효한 API. **수정 불필요.**

---

## C. UI/UX Plan

E1은 백엔드 전용. UI 변경 없음.

MLflow UI (`http://127.0.0.1:5000`)에서 `USE_MLFLOW_TRACING=true` 활성화 시:
- "Traces" 탭 → "advisor_call" LLM span 조회 가능
- 각 span: ticker, model, tokens_in, tokens_out, cost_usd 속성 포함

---

## D. System Architecture

변경 없음. `requirements.txt` 버전 범프만.

```
[현재 실제 흐름 — 코드 변경 없이 이미 작동]
advisor 호출
→ ClaudeClient.call()
→ _call_via_litellm() or native path
→ _wrap_with_mlflow_span()
  ├─ USE_MLFLOW_TRACING=false → 즉시 return (no-op, 기본값)
  └─ USE_MLFLOW_TRACING=true  → mlflow.start_span("advisor_call") 기록
→ audit_log/advisor.jsonl (항상 기록)
```

---

## E. Data Model & API Contract

변경 없음. MLflow span 출력:

```json
{
  "name": "advisor_call",
  "span_type": "LLM",
  "attributes": {
    "ticker": "005930",
    "model": "claude-opus-4-7"
  },
  "inputs": {"message_count": 3},
  "outputs": {
    "tokens_in": 1820,
    "tokens_out": 412,
    "cost_usd": 0.003240
  }
}
```

---

## F. Repo/Package Structure

**변경 파일: 1개**

```
stock_1901/
└── requirements.txt                  [변경] mlflow>=2.16 → mlflow>=3.0,<4.0
    (나머지 모든 파일 변경 없음)
```

**변경 없는 파일 (이미 구현 완료):**
```
src/stock_rtx4060/advisors/claude_client.py   ✅ _wrap_with_mlflow_span()
src/stock_rtx4060/ml/registry.py              ✅ MLflow 3.x alias API
src/stock_rtx4060/ensemble_model.py           ✅ mlflow.log_input() guard
src/stock_rtx4060/observability/mlflow_client.py ✅ log_artifact() (수정 불필요)
tests/test_claude_client.py                   ✅ MLflow span 테스트 2개
requirements.in                               ✅ mlflow>=3.0,<4.0
```

---

## G. Implementation Plan

### G1. 단일 Epic: "sync-mlflow-requirements"

| Story | 파일 | 크기 |
|-------|------|------|
| S1: `requirements.txt` mlflow 줄 업데이트 | `requirements.txt` | XS (1줄) |
| S2: `pip install mlflow>=3.0,<4.0` 실행 + `pip check` | — | XS |
| S3: 전체 테스트 스위트 통과 확인 | — | XS |
| S4: CHANGELOG에 E1 완료 기록 | `CHANGELOG.md` | XS |

### G2. PR Plan (1 PR)

| PR | 제목 | 파일 | 검증 | 롤백 |
|----|------|------|------|------|
| **PR-M1** | `chore(P0): sync mlflow requirements.txt to >=3.0,<4.0` | `requirements.txt` (1줄) | CI green + `pip check` 0 errors | `pip install mlflow==2.16.x` |

### G3. 구현 절차 (PR-M1 상세)

```bash
# Step 1: requirements.txt 수동 변경
# requirements.txt line 17:
# Before: mlflow>=2.16
# After:  mlflow>=3.0,<4.0

# Step 2: MLflow 3.x 설치
pip install "mlflow>=3.0,<4.0"

# Step 3: 의존성 충돌 확인
pip check

# Step 4: 전체 테스트 통과 확인
PYTHONPATH=.:src pytest --cov=stock_rtx4060 --cov-fail-under=75 --tb=short -q

# Step 5: MLflow 3.x 특화 테스트 확인
PYTHONPATH=.:src pytest tests/test_claude_client.py::test_mlflow_tracing_disabled_by_default \
                          tests/test_claude_client.py::test_mlflow_tracing_enabled_calls_mlflow_start_span \
                          tests/test_ml_registry.py -v

# Step 6: CLI 불변 확인
PYTHONPATH=.:src python main.py recommend --help
PYTHONPATH=.:src python main.py backtest --help

# Step 7: 커밋
git add requirements.txt
git commit -m "chore(P0): sync mlflow>=3.0,<4.0 in requirements.txt

requirements.in was already updated to mlflow>=3.0,<4.0 (W3-B1).
This PR regenerates the pinned requirement in requirements.txt to match.
All existing tests pass with MLflow 3.x. LLM advisor tracing available
via USE_MLFLOW_TRACING=true env var (implemented in W3-B1, default=false).
"
```

### G4. `USE_MLFLOW_TRACING=true` 활성화 (PR 불필요, 운영 결정)

MLflow span tracing은 코드 변경 없이 환경변수만 설정하면 활성화됩니다:

```bash
# 활성화
export USE_MLFLOW_TRACING=true

# MLflow tracking server 시작 (로컬)
mlflow server --host 127.0.0.1 --port 5000 &

# 추천 엔진 실행 → advisor 호출 span 자동 기록
PYTHONPATH=.:src python main.py recommend --universe "005930.KS" --top 1

# MLflow UI에서 확인
open http://127.0.0.1:5000  # Traces 탭 → "advisor_call"
```

### G5. 타임라인

```
Day 1 (오늘):
  1. requirements.txt 1줄 변경 (5분)
  2. pip install mlflow>=3.0,<4.0 (5분)
  3. pytest 전체 실행 (10분)
  4. PR-M1 생성 + CI 대기 (30분)

Day 1 오후:
  5. CI green → merge
  6. USE_MLFLOW_TRACING=true 검증 (선택)
```

---

## H. Testing Strategy

### H1. 이미 존재하는 테스트

```python
# tests/test_claude_client.py:452-511 (기존, 변경 불필요)

def test_mlflow_tracing_disabled_by_default(monkeypatch):
    """USE_MLFLOW_TRACING=false 기본값 → _wrap_with_mlflow_span no-op."""
    monkeypatch.setattr(_cc_mod, "_USE_MLFLOW_TRACING", False)
    # ... inner_result 그대로 반환 확인

def test_mlflow_tracing_enabled_calls_mlflow_start_span(monkeypatch):
    """USE_MLFLOW_TRACING=true → mlflow.start_span 호출 확인."""
    monkeypatch.setattr(_cc_mod, "_USE_MLFLOW_TRACING", True)
    mock_mlflow = MagicMock()
    mock_mlflow.start_span.return_value = mock_span
    with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
        client._wrap_with_mlflow_span(...)
    mock_mlflow.start_span.assert_called_once()
```

### H2. PR-M1에서 추가 확인

```bash
# MLflow 3.x 설치 후 확인 항목
PYTHONPATH=.:src pytest tests/test_ml_registry.py -v          # registry MLflow 3.x 호환
PYTHONPATH=.:src pytest tests/test_observability.py -v        # mlflow_client.py 호환
PYTHONPATH=.:src pytest tests/test_observability_extra.py -v  # 추가 관찰 테스트
PYTHONPATH=.:src pytest tests/test_ensemble_model_extra.py -v  # MLflowSession 호환
```

### H3. CI Gate

```yaml
# 기존 CI 변경 없음
- run: PYTHONPATH=.:src pytest --cov=stock_rtx4060 --cov-fail-under=75 -q
# PR-M1에서 자동으로 MLflow 3.x로 설치되어 테스트됨
```

---

## I. Observability & Operations

### I1. MLflow Tracing 활성화 운영 가이드

**로컬 MLflow 서버 설정:**
```bash
# 1회 설정
pip install "mlflow>=3.0,<4.0"
mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db

# 매 세션 시작 시
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
export USE_MLFLOW_TRACING=true
```

**span 확인:**
```
MLflow UI: http://127.0.0.1:5000
→ Experiments → ensemble_train → Traces 탭
→ advisor_call span: ticker, model, tokens_in, tokens_out, cost_usd
```

**주의사항:**
- `mlflow.log_artifact(artifact_path=...)` (observability/mlflow_client.py:51) — MLflow 3.x에서 그대로 유효. deprecated API 아님.
- `transition_model_version_stage()` — MLflow 3.x에서 deprecated → `ml/registry.py`에서 이미 fallback 처리됨.

### I2. 성능 영향

| 경로 | 추가 지연 | 메모리 |
|------|---------|--------|
| `USE_MLFLOW_TRACING=false` (기본) | 0ms (즉시 return) | 없음 |
| `USE_MLFLOW_TRACING=true` | ~1ms (로컬 span 생성) | 무시 가능 |

---

## J. Error Handling & Recovery

### J1. MLflow 3.x 설치 후 테스트 실패 시

```bash
# 확인
pip check  # 의존성 충돌 확인
pip show mlflow | grep Version  # 3.x 확인

# 일반적 MLflow 3.x 호환성 이슈:
# - mlflow.entities.Run API 변경 → test_ml_registry.py에서 발견 가능
# - mlflow.MlflowClient().transition_model_version_stage() deprecated warning
#   → ml/registry.py에서 이미 try/except로 처리됨

# 즉시 롤백
pip install "mlflow==2.19.0"  # 또는 최신 2.x stable
# requirements.txt 되돌리기
git checkout requirements.txt
```

### J2. MLflow tracing 활성화 시 advisor 속도 저하

```bash
# 증상: advisor_call latency > 200ms
# 조치: 즉시 비활성화
export USE_MLFLOW_TRACING=false
# 코드 변경, 재배포, 재시작 불필요
```

---

## K. Dependencies, Security, Risks

### K1. 의존성 변경

| 패키지 | 변경 전 | 변경 후 | 충돌 위험 |
|--------|--------|--------|---------|
| `mlflow` | `>=2.16` | `>=3.0,<4.0` | 낮음 (주요 의존성은 대부분 호환) |

**MLflow 3.x 주요 의존성 변경사항 (알려진 것):**
- `sqlalchemy>=2.0` 필요 — Wave 2에서 이미 처리됨 가능성 높음
- `alembic>=1.13.0` 권장
- `packaging>=23.0` 필요
→ `pip check` 실행으로 즉시 확인 가능

### K2. 보안

- MLflow span에 `messages` 전체 내용 미기록 (ticker, token count만) → 민감정보 누출 없음
- MLflow tracking server는 로컬 전용 (`127.0.0.1:5000`) — 외부 노출 없음

### K3. 위험 레지스터

| # | 위험 | 확률 | 영향 | 완화 |
|---|------|------|------|------|
| R1 | MLflow 3.x 의존성 충돌 (`sqlalchemy`, `alembic`) | 낮음 | 중간 | `pip check` PR-M1 전 실행 |
| R2 | MLflow 3.x에서 deprecated API 경고가 실패로 전환 | 낮음 | 낮음 | `pytest -W error::DeprecationWarning` CI gate 추가 |
| R3 | `transition_model_version_stage()` deprecated → 경고 | 중간 | 낮음 | `ml/registry.py`에서 이미 fallback 처리됨 |

### K4. Apply Gates

```
Gate 0 (Dry-run):          ✅ requirements.txt 1줄 변경만
Gate 1 (Change list):      ✅ requirements.txt:17 한 줄
Gate 2 (Explicit approval):✅ PR-M1 → 사용자 review 후 merge
Gate 3 (Feature flag):     ✅ USE_MLFLOW_TRACING=false (기본값, 롤백 불필요)
Gate 4 (Rollback):         ✅ pip install mlflow==2.16.x + git checkout requirements.txt
Gate 5 (Coverage):         ✅ pytest --cov-fail-under=75 통과 확인
Gate 6 (Safety):           ✅ screening_output_only 영향 없음
```

**최종 판정: Go ✅ — PR 1개, 반나절**

---

## ㅋ. Appendix

### ㅋ1. Evidence Table

| 항목 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|------|----------|-------|-----|------|----------|--------|
| MLflow 3.3.1 tracing | Official | MLflow Tracing Docs | mlflow.org/docs/3.3.1/genai/tracing | live | 19k+ stars | `mlflow.start_span`, SpanType.LLM |
| MLflow 3.x quickstart | Official | Tracing Quickstart Python | mlflow.org/docs/3.2.0/genai/tracing/quickstart/python-openai | live | — | Anthropic LLM 포함 모든 공급자 tracing 패턴 |
| 내부 코드 | Internal | claude_client.py:63,721-753 | stock_1901/src (2026-05-29) | 2026-05 | — | `_wrap_with_mlflow_span()` 이미 구현됨 |
| 내부 테스트 | Internal | test_claude_client.py:452-511 | stock_1901/tests (2026-05-29) | 2026-05 | — | MLflow span 테스트 이미 존재 |
| 내부 requirements | Internal | requirements.in:15 | stock_1901/ (2026-05-29) | 2026-05 | — | `mlflow>=3.0,<4.0` 이미 작성됨 |

### ㅋ2. Wave 3 플랜 vs 실제 비교

| Wave 3 플랜 | 실제 상태 | 조치 |
|------------|---------|------|
| PR-M1: mlflow 버전 범프 | `requirements.in` 이미 `>=3.0,<4.0` | `requirements.txt` 1줄만 변경 |
| PR-M2: artifact_path 마이그레이션 | `artifact_path=` 미사용 (`log_model` 아님) | **불필요** ← 제거 |
| PR-M3: MLflow LLM span tracing | `_wrap_with_mlflow_span()` 이미 구현 | **불필요** ← 제거 |
| 테스트 작성 | test_claude_client.py에 이미 존재 | **불필요** ← 제거 |

**실제 남은 작업: requirements.txt 1줄 변경 → PR-M1**

### ㅋ3. 다음 단계

E1-mlflow 완료 후:
- **E2-PBO**: `backtest_honesty_summary`에 `pbo_status` 필드 노출 (Wave 3 플랜 그대로)
- **E3-Forward**: `AutoForwardRecorder` → `daily_krx_flow` Prefect 태스크 편입 (Wave 3 플랜 그대로)

```
# E1 완료 후 빠른 확인 커맨드
USE_MLFLOW_TRACING=true \
PYTHONPATH=.:src python main.py recommend --synthetic \
  --universe "SYNTH-A" --top 1 --model-kind logistic \
  --output-dir reports/mlflow3_smoke
# → MLflow UI Traces 탭에서 "advisor_call" span 확인
```
