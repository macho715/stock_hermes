# PLAN_DOC — E2: PBO 지표 Dashboard 통합 (수정판)
**Skill:** project-plan v2.2.0 | **Date:** 2026-05-29
**Source:** Wave 3 Plan E2 + 코드베이스 재진단 (심층 스캔)
**Branch:** `claude/upgrade-investment-system-2Mc7x`

---

## ⚡ 재진단 요약 (Wave 3 플랜과 차이점)

Wave 3 플랜에서 "3 PRs, 5일" 예상했으나 구현이 80% 완료된 상태입니다.

| 항목 | Wave 3 플랜 예상 | 실제 상태 (2026-05-29 코드 스캔) |
|------|----------------|-------------------------------|
| `_compute_pbo_status()` 구현 | 신규 필요 | **이미 구현됨** (`backtest_honesty.py:342`) ✅ |
| `evaluate_backtest_honesty()` pbo 노출 | 신규 필요 | **이미 구현됨** (`backtest_honesty.py:86-89`) ✅ |
| `readiness/classifier.py` PBO 강등 | 신규 필요 | **이미 구현됨** (`classify_readiness()`, AMBER/RED 분기) ✅ |
| `RecommendationCard.jsx` PBO badge | 신규 필요 | **이미 구현됨** (`PboBadge` 컴포넌트, WCAG AA 포함) ✅ |
| `test_backtest_honesty.py` E2 테스트 | 신규 필요 | **이미 존재** (`:127-163`, E2 주석 포함) ✅ |
| `test_investment_readiness_benchmark.py` | 신규 필요 | **이미 존재** (`:339-367`, `classify_readiness` 테스트) ✅ |
| **`summarize_honesty()` pbo 필드 추가** | 신규 필요 | **미구현** — `pbo`/`pbo_status` 반환 안 함 ❌ |
| **JSX 필드명 불일치 수정** | 미파악 | **`candidate.backtest_honesty_summary` vs `backtest_honesty`** — 명칭 불일치 ❌ |

### 핵심 갭 2가지

**갭 1 — `summarize_honesty()` 미완성:**
```python
# backtest_honesty.py:93-106 (현재)
def summarize_honesty(items):
    return {
        "status": ...,
        "result_count": ...,
        "passed": ...,
        "amber": ...,
        "failed": ...,
        "generated_at_utc": ...,
        # ← "pbo", "pbo_status" 없음!
    }
```
→ `recommendation_engine.py:1109`에서 `summarize_honesty()` 결과가 `backtest_honesty_summary`로 저장됨
→ `RecommendationCard.jsx`가 `candidate.backtest_honesty_summary.pbo_status` 읽으려 하지만 해당 필드 없음

**갭 2 — JSX 필드명 불일치:**
```
snapshot["results"][i]["backtest_honesty"]     ← 실제 per-candidate 데이터 (pbo_status 있음)
candidate.backtest_honesty_summary             ← 카드가 읽는 경로 (undefined!)
```
`dashboard_bridge.py:466`이 per-candidate에 `"backtest_honesty"` 키로 저장하지만,
`RecommendationCard.jsx`는 `backtest_honesty_summary`를 기대함.

---

## A. Executive Summary

### A1. 목표

2가지 갭을 수정해 REC 탭 카드에 PBO badge가 실제로 표시되도록 한다:
1. `summarize_honesty()`에 `pbo` / `pbo_status` 필드 추가 (run-level 집계)
2. `dashboard_bridge.py`가 per-candidate 결과에 `backtest_honesty_summary`를 포함하도록 수정 (JSX 필드명 기대 충족)

### A2. 실제 KPI

| 지표 | 현재 | 목표 |
|------|------|------|
| `backtest_honesty_summary.pbo_status` in run-level | 없음 | 있음 (worst-case aggregation) |
| per-candidate `backtest_honesty_summary` 키 | 없음 (`backtest_honesty`만) | 있음 |
| REC 카드 PBO badge 표시 (CPCV 실행 시) | 미표시 | 표시 |
| `classify_readiness()` 정상 동작 | 이미 정상 (fallback 있음) | 유지 |
| 기존 테스트 통과 | 346 passed | 346+ passed |

### A3. 마일스톤

| # | 작업 | PR | 예상 |
|---|------|----|----|
| 1 | `summarize_honesty()` pbo/pbo_status 필드 추가 | PR-P1 | 1일 |
| 2 | `dashboard_bridge.py` per-candidate `backtest_honesty_summary` 추가 | PR-P2 | 0.5일 |
| 3 | `test_dashboard_bridge.py` PBO end-to-end 확인 테스트 | PR-P2 포함 | 포함 |

---

## B. Context & Requirements

### B1. 데이터 흐름 현재 상태 (갭 포함)

```
[1] recommend 실행
    → backtester.run_cpcv() → {"pbo": 0.15, ...}
    → evaluate_backtest_honesty(cpcv_result=...)
       → result["pbo"] = 0.15               ✅ per-result에 pbo 있음
       → result["pbo_status"] = "PASS"       ✅ per-result에 pbo_status 있음

[2] recommendation_engine.py:1109
    → honesty_summary = summarize_honesty([r.backtest_honesty for r in results])
       → {"status": "PASS", "result_count": 1, ...}
       → ← "pbo", "pbo_status" 없음!!        ❌ GAP-1

[3] recommendation_engine.py:1117
    → rec_json["backtest_honesty_summary"] = honesty_summary
       (pbo_status 없는 채로 저장)

[4] dashboard_bridge.py:90
    → snapshot["backtest_honesty_summary"] = payload.get("backtest_honesty_summary")
       (pbo_status 없는 채로 전달)

[5] dashboard_bridge.py:466
    → result_item["backtest_honesty"] = result.get("backtest_honesty")
       (per-result에 pbo_status 있음, but 키가 "backtest_honesty")

[6] RecommendationCard.jsx:82-87
    → candidate.backtest_honesty_summary.pbo_status  ← undefined!  ❌ GAP-2
       (카드는 "backtest_honesty_summary"를 찾지만 candidate에는 "backtest_honesty"만)
```

### B2. 요구사항

- R1: `summarize_honesty(items)` → `pbo` (worst = max across items) + `pbo_status` 반환
- R2: `dashboard_bridge.py` → per-candidate result에 `backtest_honesty_summary` 키로 `backtest_honesty` 포함 (additive)
- R3: 기존 `classify_readiness()` 동작 유지 (이미 fallback 있음)
- R4: 기존 스냅샷 스키마 `dashboard_snapshot.v1` additive 유지
- R5: CPCV 미실행 시 `pbo=None, pbo_status="NO_DATA"` → badge 숨김 (기존 JSX 조건 유지)

---

## C. UI/UX Plan

### C1. PBO Badge 표시 조건 (변경 없음)

```javascript
// RecommendationCard.jsx:86-87 (기존 조건 유지, 변경 불필요)
const hasPbo =
  backtest_honesty_summary != null &&
  backtest_honesty_summary.pbo_status != null;
```

갭-2 수정 후 `candidate.backtest_honesty_summary`가 채워지면 이 조건이 자동으로 작동.

### C2. Screens (변경 없음)

| 화면 | 변경 | 파일 |
|------|------|------|
| REC 카드 | 변경 없음 (JSX 이미 구현됨) | `RecommendationCard.jsx` |
| SIGNAL 탭 | 변경 없음 | — |
| MLflow UI | 변경 없음 | — |

### C3. Accessibility
PboBadge 컴포넌트 이미 WCAG AA 준수:
- `role="img"` + `aria-label` = "PBO 12.3 % PASS"
- 색상 + 아이콘 + 텍스트 동시 표시 (색맹 대응)
- 변경 불필요 ✅

---

## D. System Architecture

### D1. 수정 흐름 (갭 해결 후)

```
[1] evaluate_backtest_honesty(cpcv_result)
    → result = {..., "pbo": 0.15, "pbo_status": "PASS"}   ✅ (변경 없음)

[2] summarize_honesty([result, ...])  ← PR-P1 수정
    → {
        "status": "PASS",
        "result_count": 1,
        "pbo": 0.15,              ← 신규 (worst = max across items)
        "pbo_status": "PASS",     ← 신규 (_compute_pbo_status(max_pbo))
        ...
      }

[3] recommendation_engine.py:1117
    → rec_json["backtest_honesty_summary"] = honesty_summary
      (이제 pbo_status 포함)

[4] dashboard_bridge.py:466  ← PR-P2 수정
    → result_item["backtest_honesty_summary"] = {   ← 신규 키
        "pbo": result.get("backtest_honesty", {}).get("pbo"),
        "pbo_status": result.get("backtest_honesty", {}).get("pbo_status", "NO_DATA"),
      }
    → result_item["backtest_honesty"] = result.get("backtest_honesty")  ← 기존 유지

[5] RecommendationCard.jsx:82-87
    → candidate.backtest_honesty_summary.pbo_status  ← 이제 채워짐! ✅
```

### D2. 변경 컴포넌트

```
src/stock_rtx4060/
└── backtest_honesty.py      [PR-P1] summarize_honesty() pbo 필드 추가

src/stock_rtx4060/
└── dashboard_bridge.py      [PR-P2] per-candidate backtest_honesty_summary 추가

tests/
├── test_backtest_honesty.py [PR-P1] summarize_honesty pbo 테스트 추가
└── test_dashboard_bridge.py [PR-P2] per-candidate pbo_status 테스트 추가
                              또는 test_dashboard_bridge_extra.py 신규
```

---

## E. Data Model & API Contract

### E1. `summarize_honesty()` 반환값 (additive 변경)

```python
# Before
{
    "status": "PASS",
    "result_count": 1,
    "passed": 5,
    "amber": 2,
    "failed": 0,
    "generated_at_utc": "2026-05-29T...",
}

# After (PR-P1, additive)
{
    "status": "PASS",
    "result_count": 1,
    "passed": 5,
    "amber": 2,
    "failed": 0,
    "generated_at_utc": "2026-05-29T...",
    "pbo": 0.15,           # float | None — worst (max) PBO across items; None if all None
    "pbo_status": "PASS",  # "PASS" | "AMBER" | "RED" | "NO_DATA"
}
```

### E2. per-candidate snapshot result (additive 변경)

```json
// Before (snapshot.results[i])
{
  "ticker": "005930",
  "backtest_honesty": { "pbo": 0.15, "pbo_status": "PASS", ... }
}

// After (PR-P2, additive — backtest_honesty 보존 + backtest_honesty_summary 추가)
{
  "ticker": "005930",
  "backtest_honesty": { "pbo": 0.15, "pbo_status": "PASS", ... },
  "backtest_honesty_summary": {
    "pbo": 0.15,
    "pbo_status": "PASS"
  }
}
```

### E3. API 변경

| 엔드포인트 | 변경 | 영향 |
|-----------|------|------|
| `GET /api/recommend` | `results[i].backtest_honesty_summary` 신규 추가 | additive, 하위 호환 |
| `GET /api/snapshot` | 동일 (bridge 통과) | additive |

---

## F. Repo/Package Structure

**변경 파일: 2개**

```
stock_1901/
├── src/stock_rtx4060/
│   ├── backtest_honesty.py          [PR-P1] summarize_honesty() pbo/pbo_status 추가
│   └── dashboard_bridge.py          [PR-P2] per-candidate backtest_honesty_summary 추가
└── tests/
    ├── test_backtest_honesty.py      [PR-P1] 테스트 추가
    └── test_dashboard_bridge.py      [PR-P2] 테스트 추가
```

**변경 없는 파일 (이미 구현 완료):**
```
backtest_honesty.py          — _compute_pbo_status(), evaluate_backtest_honesty() ✅
readiness/classifier.py      — classify_readiness(), PBO downgrade ✅
RecommendationCard.jsx        — PboBadge, hasPbo 조건부 렌더링 ✅
tests/test_backtest_honesty.py — E2 evaluate 테스트 ✅
tests/test_investment_readiness_benchmark.py — classify_readiness 테스트 ✅
```

---

## G. Implementation Plan

### G1. Epics & Stories

| Story | 파일 | 크기 |
|-------|------|------|
| S1: `summarize_honesty()` pbo/pbo_status aggregation | `backtest_honesty.py` | S |
| S2: `summarize_honesty()` 테스트 추가 | `test_backtest_honesty.py` | S |
| S3: `dashboard_bridge.py` per-candidate backtest_honesty_summary | `dashboard_bridge.py` | S |
| S4: `test_dashboard_bridge.py` pbo end-to-end 테스트 | `test_dashboard_bridge.py` | S |

### G2. PR Plan (2 PRs)

| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| **PR-P1** | `feat(P5): add pbo + pbo_status aggregate to summarize_honesty()` | `backtest_honesty.py`, `tests/test_backtest_honesty.py` | `git revert` (additive) |
| **PR-P2** | `feat(dashboard): expose per-candidate backtest_honesty_summary with pbo_status` | `dashboard_bridge.py`, `tests/test_dashboard_bridge.py` | `git revert` (additive) |

### G3. 구현 상세 — PR-P1

```python
# src/stock_rtx4060/backtest_honesty.py — summarize_honesty() 수정

def summarize_honesty(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate result-level honesty evidence into a run-level summary.

    [E2] Now includes pbo (worst = max across candidates) and pbo_status.
    """
    statuses = [str(item.get("status", "AMBER")) for item in items]
    checks = [
        check for item in items
        for check in item.get("checks", [])
        if isinstance(check, dict)
    ]

    # [E2] Aggregate PBO: worst case = maximum (highest overfitting risk)
    pbo_values = [
        float(item["pbo"])
        for item in items
        if item.get("pbo") is not None
    ]
    worst_pbo: float | None = max(pbo_values) if pbo_values else None

    return {
        "status": _worst_status(statuses),
        "result_count": len(items),
        "passed": sum(1 for check in checks if check.get("status") == "PASS"),
        "amber": sum(1 for check in checks if check.get("status") == "AMBER"),
        "failed": sum(1 for check in checks if check.get("status") == "FAIL"),
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        # [E2] additive: PBO aggregate
        "pbo": worst_pbo,
        "pbo_status": _compute_pbo_status(worst_pbo),
    }
```

### G4. 구현 상세 — PR-P2

```python
# src/stock_rtx4060/dashboard_bridge.py
# _build_result_item() 또는 per-candidate dict 생성 위치에 추가

# 현재 (dashboard_bridge.py:466):
# "backtest_honesty": result.get("backtest_honesty"),

# 수정 후 (additive — 기존 유지 + 신규 추가):
def _extract_pbo_summary(backtest_honesty: dict | None) -> dict | None:
    """Extract per-candidate PBO summary for the dashboard card."""
    if not isinstance(backtest_honesty, dict):
        return None
    pbo = backtest_honesty.get("pbo")
    pbo_status = backtest_honesty.get("pbo_status")
    if pbo is None and pbo_status is None:
        return None
    return {
        "pbo": pbo,
        "pbo_status": pbo_status or _compute_pbo_status(pbo),
    }

# per-candidate dict에 추가:
honesty = result.get("backtest_honesty")
candidate_dict = {
    ...,
    "backtest_honesty": honesty,                         # 기존 보존
    "backtest_honesty_summary": _extract_pbo_summary(honesty),  # [E2] 신규
}
```

> **주의:** `_compute_pbo_status`를 `dashboard_bridge.py`에서 import:
> ```python
> from .backtest_honesty import _compute_pbo_status  # type: ignore[import]
> ```
> 또는 `_extract_pbo_summary()`를 `backtest_honesty.py`에 공개 함수로 이전.

### G5. 타임라인

```
Day 1 (2026-05-30):
  오전: PR-P1 (summarize_honesty pbo 추가 + 테스트) → push
  오후: PR-P2 (dashboard_bridge per-candidate + 테스트) → push

Day 2 (2026-05-31):
  CI green → merge PR-P1 → merge PR-P2
  smoke test: recommend --synthetic + dashboard_snapshot 확인
```

---

## H. Testing Strategy

### H1. 테스트 피라미드

```
E2E (playwright)    1개 (PBO badge 실제 표시 확인)
─────────────────────────────────────────────
Integration         2개 (dashboard_bridge + summarize end-to-end)
─────────────────────────────────────────────
Unit               8개 (summarize_honesty pbo 집계, bridge pbo_summary)
```

### H2. PR-P1 테스트

```python
# tests/test_backtest_honesty.py 추가

# --- summarize_honesty pbo aggregate ---

def test_summarize_honesty_includes_pbo_and_status():
    """summarize_honesty returns pbo + pbo_status (worst case)."""
    items = [
        {"status": "PASS", "pbo": 0.10, "checks": []},
        {"status": "AMBER", "pbo": 0.35, "checks": []},
    ]
    result = summarize_honesty(items)
    assert "pbo" in result
    assert "pbo_status" in result
    assert result["pbo"] == pytest.approx(0.35)   # worst = max
    assert result["pbo_status"] == "AMBER"


def test_summarize_honesty_pbo_none_when_all_none():
    """pbo=None → pbo_status=NO_DATA when no CPCV results."""
    items = [{"status": "AMBER", "checks": []}]  # no pbo key
    result = summarize_honesty(items)
    assert result["pbo"] is None
    assert result["pbo_status"] == "NO_DATA"


@pytest.mark.parametrize("pbos, expected_worst, expected_status", [
    ([0.05, 0.10], 0.10, "PASS"),
    ([0.10, 0.25], 0.25, "AMBER"),
    ([0.10, 0.60], 0.60, "RED"),
    ([], None, "NO_DATA"),
])
def test_summarize_honesty_pbo_worst_case(pbos, expected_worst, expected_status):
    items = [{"status": "PASS", "pbo": p, "checks": []} for p in pbos]
    result = summarize_honesty(items)
    if expected_worst is None:
        assert result["pbo"] is None
    else:
        assert result["pbo"] == pytest.approx(expected_worst)
    assert result["pbo_status"] == expected_status


def test_summarize_honesty_existing_fields_preserved():
    """기존 필드(status, result_count 등) 변경 없음 확인."""
    items = [{"status": "PASS", "pbo": 0.10, "checks": [{"status": "PASS"}]}]
    result = summarize_honesty(items)
    assert result["status"] == "PASS"
    assert result["result_count"] == 1
    assert result["passed"] == 1
```

### H3. PR-P2 테스트

```python
# tests/test_dashboard_bridge.py 추가

def test_dashboard_snapshot_candidate_has_backtest_honesty_summary_with_pbo(sample_payload):
    """Per-candidate backtest_honesty_summary.pbo_status present when CPCV run."""
    # sample_payload: backtest_honesty on result includes pbo + pbo_status
    sample_payload["results"][0]["backtest_honesty"]["pbo"] = 0.18
    sample_payload["results"][0]["backtest_honesty"]["pbo_status"] = "PASS"

    snapshot = build_dashboard_snapshot(sample_payload)
    candidate = snapshot["results"][0]

    assert "backtest_honesty_summary" in candidate
    assert candidate["backtest_honesty_summary"]["pbo"] == pytest.approx(0.18)
    assert candidate["backtest_honesty_summary"]["pbo_status"] == "PASS"


def test_dashboard_snapshot_backtest_honesty_key_preserved(sample_payload):
    """기존 backtest_honesty 키 보존 (additive 확인)."""
    snapshot = build_dashboard_snapshot(sample_payload)
    candidate = snapshot["results"][0]
    assert "backtest_honesty" in candidate   # 기존 키 보존


def test_dashboard_snapshot_candidate_pbo_summary_none_without_cpcv(sample_payload):
    """backtest_honesty에 pbo 없으면 backtest_honesty_summary=None."""
    del sample_payload["results"][0]["backtest_honesty"]["pbo"]
    sample_payload["results"][0]["backtest_honesty"].pop("pbo_status", None)
    snapshot = build_dashboard_snapshot(sample_payload)
    candidate = snapshot["results"][0]
    assert candidate.get("backtest_honesty_summary") is None
```

### H4. CI Gate

```bash
# 기존 CI 변경 없음
PYTHONPATH=.:src pytest --cov=stock_rtx4060 --cov-fail-under=75 -q

# PR-P1 후 확인
PYTHONPATH=.:src pytest tests/test_backtest_honesty.py -v -k "pbo"

# PR-P2 후 확인
PYTHONPATH=.:src pytest tests/test_dashboard_bridge.py -v -k "pbo"

# End-to-end smoke
PYTHONPATH=.:src python main.py recommend --synthetic \
    --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 \
    --output-dir reports/e2_pbo_smoke
# → reports/e2_pbo_smoke/recommendations_*.json 확인
# → grep "pbo_status" 확인
```

---

## I. Observability & Operations

### I1. PBO 확인 커맨드

```bash
# 스냅샷에서 pbo_status 확인
cat reports/e2_pbo_smoke/recommendations_*.json | \
  python -c "
import json, sys
d = json.load(sys.stdin)
print('Run-level pbo:', d.get('backtest_honesty_summary', {}).get('pbo_status'))
for r in d.get('results', []):
    print(r.get('ticker'), '→ per-candidate pbo_status:', r.get('backtest_honesty_summary', {}).get('pbo_status'))
"
```

### I2. 대시보드 확인

```bash
# Flask API + Vite 통합 실행
PYTHONPATH=.:src python preview_server.py
# → http://127.0.0.1:5173 REC 탭 → 각 카드 하단 "PBO XX.X% [PASS/AMBER/RED]" 확인
```

---

## J. Error Handling & Recovery

### J1. `backtest_honesty` 없는 per-candidate

```python
# dashboard_bridge.py — honesty가 None인 경우
honesty = result.get("backtest_honesty")  # None 가능
candidate["backtest_honesty_summary"] = _extract_pbo_summary(honesty)
# → _extract_pbo_summary(None) = None → card의 hasPbo=False → badge 숨김
```

### J2. `pbo`값이 비정상적인 경우 (NaN, 음수)

```python
# summarize_honesty() — float 변환 가드 추가
pbo_values = []
for item in items:
    raw = item.get("pbo")
    if raw is not None:
        try:
            v = float(raw)
            if 0.0 <= v <= 1.0:  # PBO는 확률값, 0~1 범위
                pbo_values.append(v)
        except (TypeError, ValueError):
            pass
worst_pbo = max(pbo_values) if pbo_values else None
```

### J3. 롤백

- PR-P1: `git revert` → `summarize_honesty()`에서 `pbo` 필드 제거 (card는 `hasPbo=False`로 badge 숨김)
- PR-P2: `git revert` → per-candidate에 `backtest_honesty_summary` 없음 → badge 숨김 (정상 graceful degradation)

---

## K. Dependencies, Security, Risks

### K1. 의존성 변경

없음.

### K2. 보안

PBO는 내부 메트릭 (0.0~1.0 숫자). 민감정보 없음.

### K3. 위험 레지스터

| # | 위험 | 확률 | 영향 | 완화 |
|---|------|------|------|------|
| R1 | `_compute_pbo_status` import 순환 | 낮음 | 낮음 | `backtest_honesty.py` 내에서만 사용, import 불필요 |
| R2 | `summarize_honesty()` 변경이 기존 `test_backtest_honesty.py` 실패 | 낮음 | 낮음 | additive 필드만 추가 → 기존 assert 영향 없음 |
| R3 | `dashboard_bridge.py` 변경이 `dashboard_snapshot.v1` 스키마 위반 | 낮음 | 높음 | additive 필드 추가만, `schema_version` 변경 없음 |
| R4 | CPCV 미실행 시 `backtest_honesty_summary=None` → badge 미표시 | — | — | 정상 동작 (graceful degradation) |

### K4. Apply Gates

```
Gate 0 (Dry-run):          ✅ 코드 변경만, 커밋/배포 없음
Gate 1 (Change list):      ✅ backtest_honesty.py + dashboard_bridge.py + 테스트 2파일
Gate 2 (Explicit approval):✅ PR-P1, PR-P2 각각 사용자 승인 후 merge
Gate 3 (Feature flag):     해당 없음 — additive 필드
Gate 4 (Rollback):         ✅ git revert (badge 숨김으로 graceful degradation)
Gate 5 (Coverage):         ✅ pytest --cov-fail-under=75 유지
Gate 6 (Safety):           ✅ screening_output_only 영향 없음
```

**최종 판정: Go ✅ — PR 2개, 1.5일**

---

## ㅋ. Appendix

### ㅋ1. Evidence Table

| 항목 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|------|----------|-------|-----|------|----------|--------|
| PBO 이론 | Academic | "The Probability of Backtest Overfitting" | SSRN 2326253 (Bailey et al.) | 2014 | 광범위 인용 | PBO 계산 방법론 |
| PBO Python 2025 | Medium | "The Probability of Backtest Overfitting (PBO)" | medium.com/balaena-quant-insights/pbo | 2025-07-19 | — | Python KDE 구현 + 시각화 |
| 내부 코드 (구현됨) | Internal | backtest_honesty.py:86-89, 342-357 | stock_1901/src (2026-05-29) | 2026-05 | — | `evaluate_backtest_honesty()` pbo 노출 확인 |
| 내부 코드 (구현됨) | Internal | readiness/classifier.py:classify_readiness() | stock_1901/src (2026-05-29) | 2026-05 | — | PBO 기반 readiness 강등 이미 구현 |
| 내부 코드 (구현됨) | Internal | RecommendationCard.jsx:PboBadge | stock_1901/stock-pred-v5 (2026-05-29) | 2026-05 | — | WCAG AA badge 구현 완료 |
| **갭 확인** | Internal | summarize_honesty():93-106 (미구현) | stock_1901/src (2026-05-29) | 2026-05 | — | pbo/pbo_status 필드 미반환 확인 |
| **갭 확인** | Internal | dashboard_bridge.py:466 (키 불일치) | stock_1901/src (2026-05-29) | 2026-05 | — | per-candidate "backtest_honesty" vs "backtest_honesty_summary" 불일치 |

### ㅋ2. Wave 3 플랜 vs 실제 비교

| Wave 3 플랜 PR | 실제 상태 | 조치 |
|--------------|---------|------|
| PR-P1: `pbo` + `pbo_status` 필드 추가 | `evaluate_backtest_honesty()` 이미 추가, `summarize_honesty()` 미완성 | PR-P1: `summarize_honesty()` 수정 |
| PR-P2: readiness PBO 강등 | `classify_readiness()` 이미 구현 | PR-P2 재활용: bridge 키 불일치 수정 |
| PR-P3: React PBO badge | `PboBadge` 이미 구현, 필드명 불일치로 미표시 | PR-P2에 포함 (bridge 수정으로 해결) |

### ㅋ3. 실제 E2 진행 순서

```
PR-P1 (summarize_honesty pbo 추가)
  → CI green
  → merge

PR-P2 (bridge per-candidate backtest_honesty_summary)
  → CI green
  → merge

smoke test:
  python main.py recommend --synthetic --universe "SYNTH-A" --top 1 --cv-gap 5 \
                --output-dir reports/e2_smoke
  → dashboard_snapshot.json 열어서 results[0].backtest_honesty_summary.pbo_status 확인
  → npm run dev → REC 탭 카드에 PBO badge 표시 확인
```
