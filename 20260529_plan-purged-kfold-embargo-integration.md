# Plan: PurgedKFold Embargo Integration Missing-Items Patch

## Overview

`docs/purged_kfold_embargo.py`의 검증된 누수 방지 아이디어를 운영 코드에 반영하되, 현재 운영 API와 대시보드 안전 정책을 깨지 않도록 수정한다.

## Goals

- 기존 운영 API `PurgedKFold(n_splits, embargo_pct).split(X, y=None, groups=...)`를 유지한다.
- `groups` 기반 label horizon purge와 post-test embargo 검증을 강화한다.
- OOF probability만 backtest 입력으로 허용한다는 규칙을 테스트로 고정한다.
- `walk-forward`, `TimeSeriesSplit(gap=...)`, `cv_gap` 표현 혼선을 문서와 CLI에서 정리한다.
- readiness 정책은 유지한다: live 투자 후보는 HARD BLOCK, research 후보는 AMBER WATCHLIST.

## Scope

### In Scope

- 새 계획 파일 저장 대상: `C:\Users\jichu\Downloads\주식\stock_1901\20260529_plan-purged-kfold-embargo-integration.md`
- 운영 splitter 수정 대상: `src/stock_rtx4060/ml/cv.py`
- 추천 파이프라인 검증 대상: `src/stock_rtx4060/recommendation_engine.py`
- 관련 테스트 보강 대상: `tests/test_purged_kfold.py`, `tests/test_walk_forward_purged.py`, `tests/test_ml_hpo.py`
- 문구 정리 대상: CLI help, contributor/docs 문서 중 `walk-forward`, `TimeSeriesSplit(gap=...)`, `cv_gap` 표현

### Out of Scope

- 브로커 주문 실행
- 계좌 연동
- 자동매매
- 투자 수익 보장 문구
- 모델 구조 전면 교체
- PurgedKFold를 Combinatorial Purged CV로 확장
- 실시간 live 투자 승인 로직 완화

## Constraints

- `docs/AGENTS.md` 규칙을 따른다: 금융 CV 호출은 `cv.split(X, groups=_groups)` 형태를 유지한다.
- `docs/purged_kfold_embargo.py`는 참고 구현이다. 운영에 직접 복사하지 않고 현재 운영 API에 맞게 포팅한다.
- `embargo_pct`는 `0 <= embargo_pct < 1`만 허용한다.
- `groups`는 label end index 또는 horizon end 위치를 의미한다.
- `backtest_honesty=PASS`가 아니면 live 투자 후보로 올리지 않는다.
- `new_capital_allowed=false` 기본 정책은 유지한다.
- Assumption: 문서용 `DatetimeIndex/t1` 방식은 이번 운영 통합의 기본 API로 채택하지 않는다. 필요하면 후속 옵션으로 둔다.

## Phases

### Phase 1: Plan File Save

- 이 수정 계획을 `20260529_plan-purged-kfold-embargo-integration.md`로 저장한다.
- 기존 `20260529_plan-investment-readiness-benchmark.md`는 다른 목적의 계획이므로 덮어쓰지 않는다.

### Phase 2: Splitter Hardening

- `src/stock_rtx4060/ml/cv.py`의 `PurgedKFold` public API를 유지한다.
- purge 판정은 test span과 train label window overlap을 기준으로 고정한다.
- post-test purge가 test label horizon에 걸리는 train row를 제거하는지 보장한다.
- `embargo_pct >= 1`, groups length mismatch, invalid split size를 명시적으로 거부한다.
- datetime/t1 전환은 하지 않는다. 다만 현재 코드가 datetime groups를 안전하게 처리하지 못한다면 명확히 거부하거나 별도 helper로 분리한다.

### Phase 3: Pipeline Contract

- `recommendation_engine.py`에서 fold 내부 fit만 허용한다.
- scaler/model fit은 train fold 안에서만 수행한다.
- backtest 입력은 `oof_probs.fillna(0.5)`만 허용한다.
- latest/in-sample probability는 backtest 성과 계산에 사용하지 않는다.
- `cv_gap`은 embargo 샘플 수인지 horizon 검증값인지 문서와 payload에서 의미를 분리한다.

### Phase 4: Test Coverage Patch

- `tests/test_purged_kfold.py`에 partition 완전성, 결정성, post-test purge, variable horizon no-leakage, `embargo_pct >= 1` 거부 테스트를 추가한다.
- `tests/test_walk_forward_purged.py`에 OOF probability만 backtest로 전달되는지 검증하는 테스트를 추가한다.
- `tests/test_ml_hpo.py`에 HPO가 `groups=np.arange(len(X)) + horizon` 형태의 label end groups를 전달하는지 확인한다.
- 기존 27개 docs 테스트의 핵심 property를 운영 테스트로 이동하거나 중복 검증한다.

### Phase 5: Documentation And CLI Wording

- `walk-forward`라고 표시된 곳이 실제로 PurgedKFold라면 `purged k-fold OOF CV`로 바꾼다.
- `TimeSeriesSplit(gap=...)` 문구는 운영 구현과 다르면 제거하거나 legacy 설명으로 낮춘다.
- CLI help의 `--cv-gap` 설명을 실제 의미에 맞게 정리한다.
- dashboard/readiness 문구는 유지한다: AMBER WATCHLIST, New capital not allowed, Paper trading only.

### Phase 6: Verification

- targeted tests를 먼저 실행한다.
- 이후 가능하면 전체 회귀를 실행한다.
- dashboard-export를 최신 `recommendations_algo_v2_*.json`으로 다시 실행해 readiness field가 snapshot에 유지되는지 확인한다.

## Tasks

1. 새 계획 파일을 저장한다.
2. `PurgedKFold` API 유지 조건을 코드와 테스트에 고정한다.
3. purge/embargo overlap 테스트를 운영 테스트로 이관한다.
4. OOF-only backtest 계약 테스트를 추가한다.
5. HPO groups 전달 테스트를 추가한다.
6. `cv_gap` 의미를 payload와 문서에서 정리한다.
7. CLI와 문서의 `walk-forward` 표현을 실제 구현과 맞춘다.
8. `py -3.12 -m pytest tests\test_purged_kfold.py tests\test_walk_forward_purged.py tests\test_ml_hpo.py -q`를 실행한다.
9. `py -3.12 -m pytest tests\test_dashboard_bridge.py -q`를 실행한다.
10. 최신 dashboard-export snapshot을 재검증한다.

## Risks

- `groups` 의미를 바꾸면 기존 추천 파이프라인 성능 지표가 달라질 수 있다.
- `cv_gap` 표현을 정리하지 않으면 honesty gate가 실제보다 강하게 또는 약하게 보일 수 있다.
- docs 구현을 그대로 복사하면 현재 운영 API와 충돌한다.
- PurgedKFold는 연구용 OOF 성능 추정에는 적합하지만, live 투자 승인 근거로는 chronological holdout이 별도로 필요하다.

## Review Criteria

- `PurgedKFold(...).split(X, groups=...)` 호출이 유지되어야 한다.
- test block과 train label window가 겹치는 train row가 없어야 한다.
- test 직후 embargo 구간이 제거되어야 한다.
- OOF probability 외 값이 backtest 성과 계산에 들어가면 테스트가 실패해야 한다.
- `backtest_honesty`가 없거나 AMBER/FAIL이면 live 투자 후보가 되면 안 된다.
- dashboard snapshot에 readiness fields가 남아야 한다.
- 문서와 CLI가 실제 구현 방식을 다르게 설명하면 안 된다.

## Deliverables

- `C:\Users\jichu\Downloads\주식\stock_1901\20260529_plan-purged-kfold-embargo-integration.md`
- 강화된 `PurgedKFold` 운영 테스트
- OOF-only backtest 계약 테스트
- HPO groups 전달 테스트
- 정리된 CV 관련 문서/CLI 문구
- targeted pytest 결과
- 최신 dashboard-export readiness snapshot 검증 결과
