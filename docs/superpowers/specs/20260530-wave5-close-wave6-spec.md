# Spec.md — Wave 5 Close · Wave 6 Design
**Skill:** spec-studio | **Date:** 2026-05-30
**Plan reference:** `docs/superpowers/specs/20260530-wave5-close-wave6-design-plan.md`
**Project:** `stock_1901 / stock_rtx4060`
**Branch:** `claude/upgrade-investment-system-2Mc7x`
**Status:** DRAFT — 승인 대기

---

## Summary

Wave 5의 PARTIAL 항목인 RD-Agent live 실행을 Windows 네이티브 `rdagent 0.8.0` 경로로 완료(Phase 1),
worktree를 정리하고 Wave 5 PR을 생성(Phase 2)하며,
Wave 6 우선순위 3종(MAB · Shapley · Agent Distillation)의 인터페이스 계약을 확정(Phase 3)한다.

이 문서는 구현 코드 작성 전에 체결하는 테스트 가능한 계약이다.
각 FR은 독립적으로 검증 가능해야 하며, 미확인 사항은 `Open Questions`에 기록한다.

---

## User Scenarios & Testing

### Scenario S-001 — RD-Agent health check 통과

**Given** `rdagent 0.8.0`이 Windows Python 3.12에 설치되어 있고 `.env`에 `CHAT_MODEL`이 설정되어 있다  
**When** `rdagent health_check --no-check-env` 를 실행한다  
**Then** exit code 0이 반환되고, Docker port 점검 결과가 로그에 출력된다

---

### Scenario S-002 — fin_factor Windows 네이티브 1-cycle 시작

**Given** S-001이 통과했고 `RDAGENT_MODE=native` 환경변수가 설정되어 있다  
**When** `runner.py`의 `run_factor_mining(universe=["AAPL"], cycles=1, budget_usd=2.0)`을 호출한다  
**Then** `rdagent fin_factor` subprocess가 시작되고, stdout에 hypothesis 생성 로그가 1줄 이상 출력된다

---

### Scenario S-003 — Docker fallback 보존 확인

**Given** `RDAGENT_MODE=docker` 환경변수가 설정되어 있다  
**When** `run_factor_mining()`을 호출한다  
**Then** `docker_runner.run_docker_factor_mining()`이 호출되고, Docker 비가용 시 빈 리스트를 반환한다  
**And** `microsoft/rdagent:latest` pull 시도가 발생하지 않는다 (경고 로그만 출력)

---

### Scenario S-004 — Provenance 기록 확인

**Given** S-002가 완료됐다  
**When** `audit_log/rd_agent.jsonl`을 읽는다  
**Then** 타임스탬프, mode=native, cycles=1, budget_usd=2.0을 포함한 JSONL 엔트리가 1개 이상 존재한다

---

### Scenario S-005 — Worktree 정리 후 커밋

**Given** `git status`가 untracked 파일을 포함하고 있다  
**When** 보존 파일을 `git add`하고 삭제 대상을 `.gitignore`에 추가한 뒤 커밋한다  
**Then** `git status`가 "working tree clean"을 출력한다

---

### Scenario S-006 — ThompsonWeights 수렴 검증 (Phase 3 설계 계약)

**Given** 3개 어드바이저 A, B, C가 있고 A의 reward가 B·C보다 2배 높다  
**When** `ThompsonWeights.update()`를 100회 반복한다  
**Then** `ThompsonWeights.sample()`에서 A의 평균 가중치 > B·C의 평균 가중치이다

---

### Scenario S-007 — ShapleyWeights 균등 분배 검증 (Phase 3 설계 계약)

**Given** 3개 어드바이저의 contributions가 동일하다  
**When** `ShapleyWeights.compute(contributions=[0.5, 0.5, 0.5])`를 호출한다  
**Then** 반환된 가중치 dict의 모든 값이 `1/3 ± 0.01` 범위에 있다

---

### Scenario S-008 — Agent Distillation 선결 조건 게이트

**Given** `audit_log/advisor.jsonl`의 엔트리 수를 확인한다  
**When** 엔트리 수 < 500이다  
**Then** BEST-3은 Wave 7로 이월되고, Wave 6은 BEST-1·2만 진행한다는 결정이 기록된다  
**When** 엔트리 수 ≥ 500이다  
**Then** BEST-3 구현 단계로 진행한다

---

## Requirements

### Functional Requirements

| ID | 요구사항 | 검증 방법 | Phase |
|----|----------|----------|-------|
| FR-001 | `rdagent health_check --no-check-env` exit 0 | S-001 실행 | P1 |
| FR-002 | `runner.py`에 `RDAGENT_MODE=native` 분기 추가 — `rdagent fin_factor` subprocess 호출 | S-002 실행 | P1 |
| FR-003 | `docker_runner.py`에서 `microsoft/rdagent:latest` 기본값 제거 — 경고 로그로 대체 | S-003 실행 | P1 |
| FR-004 | `RDAGENT_MODE=docker` 시 기존 Docker 경로 유지 | S-003 실행 | P1 |
| FR-005 | `fin_factor` 1-cycle 시작 시 `audit_log/rd_agent.jsonl`에 JSONL 엔트리 기록 | S-004 실행 | P1 |
| FR-006 | `git status` working tree clean 달성 | S-005 실행 | P2 |
| FR-007 | Wave 5 PR 생성 (`claude/upgrade-investment-system-2Mc7x` → `main`) | PR URL 확인 | P2 |
| FR-008 | `ThompsonWeights` 클래스 인터페이스 확정: `.sample()`, `.update(advisor_id, reward)` | S-006 단위 테스트 | P3 |
| FR-009 | `ShapleyWeights` 클래스 인터페이스 확정: `.compute(contributions)` | S-007 단위 테스트 | P3 |
| FR-010 | `ADVISOR_WEIGHTS_MODE=mab|shapley|fixed` 환경변수 전환 계약 정의 | 문서 확정 | P3 |
| FR-011 | `advisor.jsonl` 엔트리 수 측정 및 BEST-3 이월 여부 결정 | S-008 | P3 |

### Non-Functional Requirements

| ID | 요구사항 | 기준 |
|----|----------|------|
| NFR-001 | 테스트 커버리지 유지 | `pytest --cov-fail-under=75` 통과 (현재 83%) |
| NFR-002 | Lint 경고 없음 | `ruff check src/ tests/` 경고 0 |
| NFR-003 | LLM 예산 상한 | `rdagent fin_factor` 예산 $2.0/cycle 초과 금지 |
| NFR-004 | 안전 불변 조건 유지 | `screening_output_only=True` 모든 `RecommendationResult`에 보존 |
| NFR-005 | `runner.py` 신규 smoke 테스트 | `RDAGENT_MODE=native` 경로에 대한 단위 테스트 1개 이상 추가 |
| NFR-006 | Provenance 스키마 호환 | 기존 `rd_agent.jsonl` 이벤트명 변경 금지 — 새 필드는 additive-only |

---

## Assumptions & Dependencies

| ID | 항목 | 유형 |
|----|------|------|
| A-001 | `rdagent fin_factor` Windows에서 Linux syscall 없이 기동 가능 | Assumption — 검증 필요 (S-002) |
| A-002 | `CHAT_MODEL=claude-opus-4-7`은 litellm `anthropic/claude-opus-4-7` prefix로 라우팅 가능 | Assumption |
| A-003 | embedding이 없어도 `--no-check-env` flag로 health_check 통과 가능 | Assumption — 공식 README에서 확인 |
| A-004 | Docker Desktop WSL2 integration이 활성화되어 있어 Docker fallback 경로 유효 | 검증 완료 (`hello-world` 실행 확인) |
| A-005 | `audit_log/advisor.jsonl` 엔트리 수는 Phase 3 진입 시점에 측정 | Assumption — 현재 미확인 |
| A-006 | Shapley 계산은 주당 1회 배치로 충분 (실시간 불필요) | Assumption |
| D-001 | `rdagent 0.8.0` 설치 완료 | 충족 — 검증 완료 |
| D-002 | Docker Desktop 29.2.1 실행 중 | 충족 — 검증 완료 |
| D-003 | `advisors/orchestrator.py`의 `DEFAULT_WEIGHTS` 상수 존재 | [NEEDS CLARIFICATION: 현재 파일 내 상수명 확인 필요] |
| D-004 | `Advisor` 프로토콜 인터페이스가 `advisors/` 내에 존재 | [NEEDS CLARIFICATION: Protocol 파일 위치 확인 필요] |

---

## Success Criteria

| ID | 기준 | 측정 방법 |
|----|------|----------|
| SC-001 | `rdagent fin_factor` Windows 실행 — hypothesis 로그 1줄 이상 출력 | stdout 확인 |
| SC-002 | Wave 5 PR URL 생성 완료 | GitHub PR 링크 |
| SC-003 | `pytest --cov-fail-under=75` 통과 (커버리지 ≥ 75%) | CI 또는 로컬 실행 |
| SC-004 | `ruff check` 경고 0 | ruff 출력 |
| SC-005 | `ThompsonWeights` 인터페이스 계약 문서화 완료 | 이 Spec의 FR-008 |
| SC-006 | `ShapleyWeights` 인터페이스 계약 문서화 완료 | 이 Spec의 FR-009 |
| SC-007 | `advisor.jsonl` 엔트리 수 측정 + BEST-3 이월 여부 결정 기록 | FR-011 |

---

## Open Questions

| ID | 질문 | 우선순위 | 관련 ID |
|----|------|----------|---------|
| OQ-001 | `rdagent fin_factor`가 Windows에서 실행될 때 Linux-specific 경로(예: `/tmp`)를 어떻게 처리하는가? 실패 시 WSL2 fallback을 자동 전환할 것인가, 수동 전환할 것인가? | 높음 | A-001, FR-002 |
| OQ-002 | `audit_log/advisor.jsonl`의 현재 엔트리 수는 얼마인가? (BEST-3 이월 여부 결정에 필요) | 높음 | A-005, FR-011 |
| OQ-003 | `advisors/orchestrator.py`의 `DEFAULT_WEIGHTS` 정확한 상수명과 구조는? | 중간 | D-003, FR-008 |
| OQ-004 | Wave 5 PR 머지 전에 CI 파이프라인(GitHub Actions)을 별도로 확인해야 하는가? | 중간 | FR-007 |

---

## Clarifications Log

| 날짜 | 항목 | 결론 |
|------|------|------|
| 2026-05-30 | rdagent Linux-only 공식 문구 → Windows 실행 가능 여부 | 브레인스토밍 환경 검증: `rdagent.exe` 확인, `fin_factor` CLI 존재 확인. 실제 실행은 S-002에서 검증 |
| 2026-05-30 | `microsoft/rdagent:latest` Docker Hub 존재 여부 | 공식 README 확인: 해당 이미지 없음. rdagent는 내부 sandbox 컨테이너를 로컬 빌드함 |
| 2026-05-30 | WSL2 vs Windows native 경로 선택 | Windows native 우선 (A-001), WSL2 fallback 보존 |
