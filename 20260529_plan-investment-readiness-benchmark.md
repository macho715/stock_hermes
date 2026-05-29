# Plan: investment_readiness_benchmark.py

## Overview

`investment_readiness_benchmark.py`를 추가해 추천 결과가 실제 투자 검토 후보로 올라갈 수 있는지 `backtest_honesty=PASS`, `3x cost survival`, `embargo stress`, `advisor audit consistency` 기준으로 검증한다.

## Goals

- 기존 추천 결과 JSON 또는 새 추천 실행 결과를 입력으로 받아 투자 준비도 벤치마크를 생성한다.
- `backtest_honesty=PASS`가 아닌 후보를 자동으로 탈락 또는 수동 검토 대상으로 분리한다.
- 비용과 슬리피지 3배 스트레스에서도 후보가 살아남는지 검증한다.
- embargo stress를 통해 `cv_gap` 또는 purged walk-forward 검증이 약한 후보를 표시한다.
- `advisor_run=1` 결과에서 advisor score와 advisor audit evidence가 서로 맞는지 확인한다.

## Scope

### In Scope

- 새 파일: `tools/investment_readiness_benchmark.py`
- 새 테스트: `tests/test_investment_readiness_benchmark.py`
- 입력 대상: `recommendations_algo_v2_*.json`
- 출력 대상: Markdown 또는 JSON 벤치마크 보고서
- 기존 모듈 재사용:
  - `src/stock_rtx4060/backtest_honesty.py`
  - `src/stock_rtx4060/backtester.py`
  - `src/stock_rtx4060/advisors/audit.py`
  - `src/stock_rtx4060/recommendation_engine.py`
- 검증 기준:
  - `backtest_honesty.status == "PASS"`
  - 1x, 2x, 3x 비용 스트레스 생존 여부
  - embargo stress 결과의 PASS/AMBER/FAIL
  - advisor score가 존재할 때 audit evidence 존재 여부

### Out of Scope

- 브로커 로그인
- 계좌 조회
- 실제 주문 실행
- 자동 매수/매도
- 시크릿 또는 API 키 처리
- 투자 조언 문구 생성
- 추천 엔진의 모델 구조 변경
- 대시보드 UI 변경

## Constraints

- 모든 작업은 `C:\Users\jichu\Downloads\주식\stock_1901` 안에서만 수행한다.
- STOP 파일이 있으면 실행하지 않는다.
- 결과는 정보 제공과 수동 검토용으로만 사용한다.
- 기존 `screening_output_only` 경계를 유지한다.
- 벤치마크는 후보를 승격시키지 않고, 탈락 또는 위험 표시만 수행한다.
- Assumption: 비용 스트레스는 기존 `BacktestConfig.transaction_cost`와 `BacktestConfig.slippage` 값을 기준으로 1x, 2x, 3x를 적용한다.
- Assumption: embargo stress는 기존 추천 결과에 저장된 `cv_gap`과 horizon을 우선 사용하고, 원자료 재실행이 없으면 “metadata-only” 판정으로 제한한다.

## Phases

### Phase 1: Input Contract

- 추천 JSON 파일을 읽는다.
- `results`, `config`, `backtest_honesty_summary`, `audit_log_path`, `disclaimer` 필드를 확인한다.
- 필수 필드가 없으면 `FAIL`이 아니라 `INVALID_INPUT`으로 분리한다.

### Phase 2: Backtest Honesty Gate

- 각 후보의 `backtest_honesty.status`를 확인한다.
- `PASS`만 투자 검토 후보로 유지한다.
- `AMBER`와 `FAIL`은 이유와 함께 별도 섹션에 기록한다.

### Phase 3: 3x Cost Survival

- 후보별 기존 백테스트 수익률과 비용 버퍼를 비교한다.
- 1x, 2x, 3x 비용 기준에서 생존 여부를 기록한다.
- 3x 기준을 통과하지 못하면 `COST_STRESS_FAIL`로 표시한다.

### Phase 4: Embargo Stress

- `cv_gap >= horizon` 여부를 기본 기준으로 확인한다.
- 추가 stress 기준으로 `cv_gap >= 1.5 * horizon` 또는 `cv_gap >= 2 * horizon`를 별도 표시한다.
- Assumption: 실제 재학습 없이 metadata만 있는 경우, “재실행 필요” 상태를 포함한다.

### Phase 5: Advisor Audit Consistency

- `advisor_score`가 `None`이 아니면 advisor audit evidence가 있는지 확인한다.
- advisor score가 추천 점수에 반영됐는데 audit evidence가 없으면 `ADVISOR_AUDIT_FAIL`로 표시한다.
- advisor score가 음수이면 추천 후보 점수와 리스크 설명을 함께 표시한다.

### Phase 6: Report Output

- 후보별 PASS/AMBER/FAIL 표를 생성한다.
- 전체 run verdict를 생성한다.
- 출력에는 “manual approval required”와 “no broker order execution”을 포함한다.

## Tasks

1. `tools/investment_readiness_benchmark.py` CLI 초안을 만든다.
2. 추천 JSON 로더와 입력 검증 함수를 만든다.
3. `backtest_honesty` 판정 함수를 만든다.
4. 비용 스트레스 판정 함수를 만든다.
5. embargo stress 판정 함수를 만든다.
6. advisor audit consistency 판정 함수를 만든다.
7. Markdown/JSON 출력 함수를 만든다.
8. `tests/test_investment_readiness_benchmark.py`에 단위 테스트를 추가한다.
9. 샘플 추천 JSON fixture를 테스트 안에서 최소 구조로 생성한다.
10. `ruff`와 targeted `pytest`를 실행한다.
11. 필요하면 `main.py self-test`를 실행한다.

## Risks

- 기존 추천 JSON에는 실제 재학습에 필요한 원자료가 없을 수 있다.
- 비용 3배 stress는 기존 백테스트를 재실행하지 않으면 보수적 추정으로만 계산될 수 있다.
- advisor audit 위치가 output_dir별로 다르면 audit consistency 확인이 누락될 수 있다.
- `backtest_honesty=PASS` 기준을 엄격히 적용하면 현재 추천 후보 대부분이 탈락할 수 있다.

## Review Criteria

- STOP 파일이 없는 상태에서만 실행한다.
- 브로커, 계좌, 주문, 시크릿 작업이 없어야 한다.
- `backtest_honesty=AMBER` 후보는 최종 투자 검토 후보로 올라가지 않아야 한다.
- 3x 비용 stress 실패 후보는 `COST_STRESS_FAIL`로 표시되어야 한다.
- weak embargo 후보는 `EMBARGO_STRESS_AMBER` 또는 `EMBARGO_STRESS_FAIL`로 표시되어야 한다.
- advisor score가 있는데 audit evidence가 없으면 `ADVISOR_AUDIT_FAIL`로 표시되어야 한다.
- targeted tests가 통과해야 한다.

## Deliverables

- `tools/investment_readiness_benchmark.py`
- `tests/test_investment_readiness_benchmark.py`
- 벤치마크 실행 예시 명령
- 벤치마크 Markdown 또는 JSON 샘플 출력
- 검증 결과 요약
