# PLAN — Wave 5 Close · Wave 6 Design
**Skill:** plan-studio | **Date:** 2026-05-30
**Project:** `stock_1901 / stock_rtx4060`
**Branch:** `claude/upgrade-investment-system-2Mc7x`

---

## Overview

Wave 5의 PARTIAL 항목(RD-Agent live 실행)을 Windows 네이티브 `rdagent 0.8.0` 경로로 완료하고,
worktree를 정리하여 Wave 5 PR을 닫은 뒤, Wave 6 우선순위 3종(MAB 어드바이저 가중치 · Shapley 동적 가중치 · Agent Distillation)을 설계 수준까지 정의한다.

환경 검증 결과:

- `rdagent 0.8.0` Windows Python 3.12에 설치 완료 (`rdagent.exe` 확인)
- `fin_factor` 서브커맨드 CLI에서 존재 확인
- Docker Desktop 29.2.1 정상 작동 (코드 sandbox용)
- WSL2 Ubuntu + `~/.rdagent-env` venv 준비 완료 (fallback)

---

## Goals

1. `rdagent fin_factor` 1-cycle이 Windows에서 hypothesis 생성 로그를 출력한다 (Wave 5 Done 기준).
2. `docker_runner.py`의 잘못된 `microsoft/rdagent:latest` 가정을 제거하고 네이티브 CLI 경로를 추가한다.
3. Wave 5 worktree의 미추적 파일을 분류하고, 불필요 파일을 정리한다.
4. Wave 5 최종 커밋과 PR을 생성한다.
5. Wave 6 BEST-1(MAB), BEST-2(Shapley), BEST-3(Agent Distillation)의 설계를 plan 수준에서 확정한다.

---

## Scope

### In Scope

- `rdagent health_check --no-check-env` 실행 및 통과 확인
- `.env` LiteLLM 설정: `CHAT_MODEL`, `EMBEDDING_MODEL`, API 키 연결
- `rdagent fin_factor` Windows 네이티브 실행 (1-cycle, 예산 $2.0)
- `runner.py` `RDAGENT_MODE=native` 경로 추가 (Docker fallback 유지)
- `docker_runner.py` 기본값 `microsoft/rdagent:latest` 수정
- Wave 5 worktree 정리: `git status` → 보존/삭제 분류 → 커밋
- Wave 5 PR 생성 (`claude/upgrade-investment-system-2Mc7x` → `main`)
- Wave 6 설계 문서 작성 (BEST-1, BEST-2, BEST-3)

### Out of Scope

- `rdagent fin_factor` 전체 사이클 완료 (hypothesis 로그 출력이면 Done)
- WSL2 경로 본격 구축 (환경 fallback으로만 보존)
- Wave 6 구현 코드 작성
- 브로커 실행 활성화
- CI 파이프라인 변경

---

## Constraints

| 제약 | 근거 |
|------|------|
| `screening_output_only=True` 유지 | CLAUDE.md 불변 조건 4 |
| `pytest --cov-fail-under=75` 통과 필수 | CLAUDE.md 불변 조건 8, 현재 83% |
| 커밋 전 `ruff check` 경고 0 | MACHO-GPT A5 품질 게이트 |
| LLM 예산 $2.0/cycle 상한 | Wave 5 목표 문서 기준 |
| 기존 `docker_runner.py` Docker 경로 삭제 금지 | 하위 호환성 — fallback 유지 |

---

## Phases

### Phase 1 — RD-Agent Windows 네이티브 완료

**목표:** `rdagent fin_factor`가 Windows에서 hypothesis 로그를 출력한다.

#### Tasks

| ID | 작업 | 파일 | 완료 기준 |
|----|------|------|----------|
| T1.1 | `.env` 파일 생성: `CHAT_MODEL`, `EMBEDDING_MODEL`, API 키 설정 | `.env` (git-ignored) | `rdagent health_check --no-check-env` exit 0 |
| T1.2 | `runner.py`에 `RDAGENT_MODE=native` 분기 추가 — `subprocess rdagent fin_factor ...` 호출 | `factors/rd_agent/runner.py` | 기존 테스트 통과 + 신규 smoke 테스트 1개 |
| T1.3 | `docker_runner.py` `_DOCKER_IMAGE` 기본값 수정 — `microsoft/rdagent:latest` → 주석 처리 후 경고 로그 | `factors/rd_agent/docker_runner.py` | ruff clean, 테스트 통과 |
| T1.4 | `rdagent fin_factor --cycles 1 --budget-usd 2.0` 실행 | — | hypothesis 생성 로그 1줄 이상 출력 |
| T1.5 | 실행 결과 `audit_log/rd_agent.jsonl`에 provenance 기록 확인 | `factors/rd_agent/provenance.py` | JSONL 엔트리 1개 이상 |

Assumption: `CHAT_MODEL=claude-opus-4-7`을 litellm `anthropic/` prefix로 라우팅하면 embedding 모델도 별도 설정이 필요하다. embedding이 없으면 `text-embedding-3-small` OpenAI fallback 사용.

### Phase 2 — Worktree 정리 · Wave 5 PR

**목표:** 미추적 파일 정리 후 Wave 5 완료 커밋과 PR을 생성한다.

#### Tasks

| ID | 작업 | 완료 기준 |
|----|------|----------|
| T2.1 | `git status` — untracked 파일 목록 확인 | 목록 출력 |
| T2.2 | 보존 파일: 코드·테스트·문서 → `git add` | 스테이지 완료 |
| T2.3 | 삭제 대상: 임시 파일·중복 report → `.gitignore` 추가 또는 삭제 | `git status` clean |
| T2.4 | `behavioral(P2): rdagent native CLI path + Wave 5 close` 커밋 | `git log` 확인 |
| T2.5 | PR 생성 — 제목: `feat(Wave5): mSPRT · TradingAgents debate · Qlib/RD-Agent E2E` | PR URL 확인 |

### Phase 3 — Wave 6 설계

**목표:** BEST-1·2·3 각각에 대해 인터페이스·데이터 흐름·테스트 기준을 정의한다. 구현 코드는 작성하지 않는다.

#### BEST-1: Multi-Armed Bandit 어드바이저 가중치 (Thompson Sampling)

| 항목 | 내용 |
|------|------|
| 변경 범위 | `advisors/orchestrator.py` — `DEFAULT_WEIGHTS` → `ThompsonWeights` 클래스 |
| 인터페이스 | `ThompsonWeights.sample() -> dict[str, float]` · `ThompsonWeights.update(advisor_id, reward)` |
| 데이터 저장 | `audit_log/advisor.jsonl` — 기존 `score` 필드를 reward로 활용 |
| 테스트 기준 | 100 업데이트 후 높은 reward 어드바이저의 평균 가중치 > 낮은 어드바이저 가중치 |
| Fallback | `ADVISOR_WEIGHTS_MODE=fixed` 환경변수로 기존 `DEFAULT_WEIGHTS` 상수 복귀 |
| PriorityScore | 2.0 / SurpriseScore 6.67 |

#### BEST-2: Shapley 동적 어드바이저 가중치

| 항목 | 내용 |
|------|------|
| 변경 범위 | `advisors/orchestrator.py` — MAB와 병렬 경로, A/B 선택 가능 |
| 인터페이스 | `ShapleyWeights.compute(advisor_contributions: list[float]) -> dict[str, float]` |
| 데이터 요건 | 최소 30일 어드바이저별 accuracy 이력 필요 |
| 테스트 기준 | 동일 contribution 어드바이저 → 균등 가중치 수렴 |
| Assumption | Shapley 계산은 주당 1회 배치 — 실시간 계산 아님 |
| PriorityScore | 2.0 / SurpriseScore 6.67 |

Assumption: BEST-1(MAB)과 BEST-2(Shapley)는 동일 `orchestrator.py`에서 `ADVISOR_WEIGHTS_MODE=mab|shapley|fixed` 환경변수로 전환한다. 두 방식을 동시에 활성화하지 않는다.

#### BEST-3: Agent Distillation (NeurIPS 2025)

| 항목 | 내용 |
|------|------|
| 선결 조건 | `audit_log/advisor.jsonl` 엔트리 수 ≥ 500 (trajectory 데이터셋 규모 확인 필요) |
| 변경 범위 | `advisors/` 신규 `distilled_advisor.py` — 로컬 sLM 추론 |
| 인터페이스 | `DistilledAdvisor.score(ticker, features) -> float` — 기존 `Advisor` 프로토콜 구현 |
| 데이터 파이프라인 | `advisor.jsonl` → trajectory 파싱 → 학습 데이터 포맷 변환 |
| 테스트 기준 | `distilled_advisor` IC ≥ 0.03 on held-out 20% of trajectory data |
| Assumption | 로컬 sLM은 Ollama 또는 Hugging Face Transformers 사용 — 외부 API 의존 없음 |
| PriorityScore | 1.0 / SurpriseScore 5.0 |

선결 조건 미충족 시 (엔트리 < 500) → BEST-3는 Wave 7로 이월하고 Wave 6은 BEST-1·2만 진행한다.

---

## Risks

| 위험 | 확률 | 영향 | 대응 |
|------|------|------|------|
| `rdagent fin_factor` Windows에서 Linux syscall 실패 | 중 | 중 | WSL2 venv fallback 즉시 전환 |
| embedding 모델 미설정으로 `health_check` 실패 | 중 | 낮음 | `--no-check-env` flag 사용 → embedding 없이 진행 |
| `typing-extensions` 버전 충돌 (mitmproxy 경고 발생) | 낮음 | 낮음 | mitmproxy는 rdagent 미사용 — 무시 |
| Wave 6 BEST-2 Shapley 30일 이력 부족 | 중 | 중 | MAB 먼저 구현 후 이력 쌓고 BEST-2 진행 |
| Agent Distillation 데이터셋 < 500 엔트리 | 중 | 높음 | Wave 6에서 데이터 확인 후 Wave 7 이월 결정 |

---

## Review Criteria

Phase 1 완료 조건:
- [ ] `rdagent health_check --no-check-env` exit 0
- [ ] `rdagent fin_factor` hypothesis 로그 1줄 이상 출력
- [ ] `pytest --cov-fail-under=75` 통과 (커버리지 ≥ 75%)
- [ ] `ruff check` 경고 0

Phase 2 완료 조건:
- [ ] `git status` — untracked 파일 0 또는 `.gitignore` 처리
- [ ] Wave 5 PR URL 생성

Phase 3 완료 조건:
- [ ] Wave 6 BEST-1 인터페이스 문서 확정
- [ ] Wave 6 BEST-2 선결 조건 충족 여부 판단
- [ ] Wave 6 BEST-3 `audit_log/advisor.jsonl` 엔트리 수 확인

---

## Deliverables

| 산출물 | 위치 |
|--------|------|
| 이 Plan 문서 | `docs/superpowers/specs/20260530-wave5-close-wave6-design-plan.md` |
| `runner.py` native CLI 경로 | `src/stock_rtx4060/factors/rd_agent/runner.py` |
| `docker_runner.py` image 수정 | `src/stock_rtx4060/factors/rd_agent/docker_runner.py` |
| Wave 5 완료 커밋 | `behavioral(P2): rdagent native CLI path + Wave 5 close` |
| Wave 5 PR | `claude/upgrade-investment-system-2Mc7x` → `main` |
| Wave 6 설계 확정 문서 | 이 Plan의 Phase 3 섹션 |
