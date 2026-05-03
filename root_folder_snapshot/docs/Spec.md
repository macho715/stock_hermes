# Feature Specification: `stock_rtx4060` Investment Operation OS

Feature ID/Branch: `001-stock-rtx4060-investment-os`
Created: 2026-05-02
Status: Draft / Not Approval-Ready
Owner: Investor / Portfolio Operator
Input: `붙여넣은 텍스트 (1).txt`, `uiux.md`, `plan.md`, `SETUP.md`, Spec.md template/rules
Last Updated: 2026-05-02
Version: v0.2.0

> Scope note: 이 문서는 투자 실행을 위한 **운영·검증·리포트 계약**이다. 특정 종목 매수/매도 추천, 개인 맞춤 투자 자문, 세무·법률 자문, broker 주문 실행 지시는 포함하지 않는다.

---

## Source Review

### 확인한 내부 문서

| Source | Spec 반영 내용 |
|---|---|
| `붙여넣은 텍스트 (1).txt` | `stock_rtx4060` 투자 OS 목표, Phase 1~7, GPU 검증 Gate, Deliverables |
| `uiux.md` | Track-S / Track-L 분리, AMBER 판정, Risk Gate, Fail-safe Rules, Daily Brief, Journal, Monthly Scorecard |
| `plan.md` | 기존 단타·장기 운영 구조, 자금 배분, Score, Entry/Exit, Review 체계 |
| `SETUP.md` | Windows i5-13500HX + RTX 4060 Laptop, Python 3.11, TensorFlow, XGBoost, Ollama `--lite`, CLI 명령, 폴더 구조 |
| `01-spec-template-and-rules.md` | 필수 섹션, `FR-###`, `NFR-###`, `SC-###`, approval gate |
| `02-sample-specs.md` | clarify-first, approval-gate, traceability 패턴 |
| `03-review-checklists.md` | 독립 테스트, 측정 가능한 성공 기준, failure behavior, approval-ready 조건 |

### 확인한 외부 기준

| Source | Spec 반영 내용 |
|---|---|
| TensorFlow official install guide | TensorFlow `2.10` 이후 Windows Native GPU 지원이 중단되므로, TensorFlow GPU는 WSL2 검증 Gate를 둔다. |
| XGBoost official GPU docs | XGBoost GPU는 CUDA 12.0 및 Compute Capability 5.0 이상 조건과 `device=cuda:0` 경로를 검증한다. |
| FINRA intraday margin guidance | Margin은 초기 금지로 두며, broker/account 규칙 확정 전까지 자동 허용하지 않는다. |
| BlackRock / Vanguard 2026 market outlook | AI, 지정학, 에너지 충격, valuation risk는 후보 Universe와 Risk Context의 참고 입력으로만 사용한다. |

---

## Summary

### Problem

- 현재 문서들은 투자 운영 Rule, Windows/GPU 구축, 모델·백테스트, 리포트 출력이 각각 분리되어 있어 하나의 검증 가능한 계약으로 보기 어렵다.
- `uiux.md`와 `plan.md`의 핵심은 **Track-S 단타 + Track-L 장기 + 공통 Risk Gate**이나, `SETUP.md`의 GPU 실행환경과 모델 파이프라인이 기존 Spec에 충분히 통합되지 않았다.
- Track-S의 1개월 +10.00% 목표는 공격적이므로 수익 보장이 아니라 **익절 Gate**로 취급해야 한다.
- TensorFlow GPU 경로는 Windows Native와 WSL2 간 차이가 있어, 설치 명령만으로 GPU 사용 가능성을 승인하면 안 된다.
- 실제 총 투자금, 시장, broker/account type, 허용 상품, 데이터 공급원, 자동화 수준이 확정되지 않았다.

### Goals

- G1: Track-S, Track-L, Cash/Dry Powder를 별도 ledger로 운영한다.
- G2: Track-S는 Score, Liquidity, Market Regime, Catalyst, Risk/Reward, Stop 기준을 통과한 후보만 `ELIGIBLE`로 표시한다.
- G3: Track-L은 Bucket, Score, Valuation, Thesis, Concentration 기준을 통과한 후보만 `ACCUMULATE`로 표시한다.
- G4: Green / Amber / Red / ZERO Risk Gate를 모든 후보와 리포트에 적용한다.
- G5: Windows i5-13500HX + RTX 4060 Laptop 환경에서 `workspaces/stock_rtx4060/` 실행환경, GPU 검증, 모델·백테스트, report output을 계약화한다.
- G6: Daily Brief, Risk Dashboard, Track-S Journal, Track-L Thesis Report, Monthly Scorecard를 감사 가능한 출력물로 정의한다.
- G7: 자동매매는 v0.2.0 범위에서 제외하고, 예측값은 의사결정 보조·백테스트·리포트에만 사용한다.
- G8: 미확정 항목은 `[NEEDS CLARIFICATION: ...]`로 유지하고, `Approved` 상태 전환 조건을 명시한다.

### Non-Goals

- NG1: 특정 종목, ETF, 옵션, 선물, leveraged product에 대한 직접 매수/매도 추천은 하지 않는다.
- NG2: live broker 주문 실행, 자동매매, order routing은 v0.2.0 범위가 아니다.
- NG3: margin, options, 0DTE, leveraged ETF, penny stock, illiquid security는 기본 허용하지 않는다.
- NG4: 신규 웹앱, 모바일앱, 별도 dashboard UI 개발은 범위에 포함하지 않는다. 표 기반 report output을 우선한다.
- NG5: 세무, 법률, 규제, broker suitability 판단은 포함하지 않는다.
- NG6: Track-S +10.00%/월 또는 Track-L +20.00%/3년을 보장하지 않는다.
- NG7: GPU benchmark 수치를 확정 성능으로 보지 않는다. 실제 장비에서 재측정해야 한다.

---

## User Scenarios & Testing

### User Story 1 - Track 분리 및 자금 보호 (Priority: P1)

Operator는 단타 손실이 장기 포트폴리오를 침식하지 않도록 Track-S, Track-L, Cash/Dry Powder를 구조적으로 분리하고 싶다.

Why this priority: 자금 분리 실패는 전체 투자 OS의 최상위 실패 조건이다.

Independent Test: 총 투자금 100,000.00 AED를 입력했을 때 Track-S 20,000.00 AED, Track-L 75,000.00 AED, Cash 5,000.00 AED가 생성되고, Track-S 손실 발생 후 Track-L/Cash에서 자동 보전되지 않는지 검증한다.

Acceptance Scenarios:
1. Given total capital is 100,000.00 AED, When default allocation is applied, Then Track-S MUST equal 20,000.00 AED, Track-L MUST equal 75,000.00 AED, and Cash MUST equal 5,000.00 AED.
2. Given Track-S monthly loss reaches -5.00%, When a new Track-S candidate is evaluated, Then the verdict MUST be `BLOCKED_MONTHLY_LOSS_LIMIT`.
3. Given Track-S has realized losses, When the operator attempts to fund losses from Track-L or Cash, Then the system MUST require explicit override and log the event.

### User Story 2 - Track-S 단타 후보 평가 (Priority: P1)

Operator는 단타 후보가 진입 전 Score, 손절, 익절, Risk/Reward, 시장 조건을 모두 통과했는지 확인하고 싶다.

Why this priority: Track-S는 손실 속도가 가장 빠른 영역이다.

Independent Test: Score 82.00 + Stop/TP/RR complete 후보, Score 73.00 후보, Stop 누락 후보를 입력해 각각 `ELIGIBLE`, `AMBER`, `ZERO_NO_STOP`으로 분류되는지 검증한다.

Acceptance Scenarios:
1. Given Score ≥75.00, Risk/Reward ≥2.00, Liquidity Pass, Market Regime Pass, Catalyst Pass, and Stop defined, When Track-S Gate runs, Then verdict MAY be `ELIGIBLE`.
2. Given Score is 65.00~74.99, When Track-S Gate runs, Then verdict MUST be `AMBER` unless Red or ZERO applies.
3. Given Stop is missing, When Track-S Gate runs, Then verdict MUST be `ZERO_NO_STOP` regardless of score.
4. Given open risk exceeds configured limit, When candidate is evaluated, Then verdict MUST be `RED_OPEN_RISK_LIMIT`.

### User Story 3 - Track-L 장기 편입 평가 (Priority: P1)

Operator는 장기 후보를 Core, Quality, AI/Infra, Commodity/Energy, Bonds/Cash bucket에 맞춰 편입하고 싶다.

Why this priority: Track-L은 주요 자본 기반이며 thesis 훼손과 concentration risk를 관리해야 한다.

Independent Test: Score 84.00, thesis documented, bucket capacity available 후보는 `ACCUMULATE`가 가능해야 한다. 단일 종목 exposure가 12.00%를 초과하는 후보는 `REBALANCE_REVIEW_REQUIRED`가 되어야 한다.

Acceptance Scenarios:
1. Given Track-L Score ≥80.00, valuation acceptable, thesis documented, and bucket capacity available, When Track-L Gate runs, Then verdict MAY be `ACCUMULATE`.
2. Given Track-L Score is 70.00~79.99, When Track-L Gate runs, Then verdict MUST be `AMBER` unless Red or ZERO applies.
3. Given single-name exposure would exceed 12.00%, When candidate is evaluated, Then the system MUST return `REBALANCE_REVIEW_REQUIRED`.

### User Story 4 - Windows / GPU 환경 검증 (Priority: P1)

Operator는 Windows i5-13500HX + RTX 4060 Laptop에서 모델 학습과 백테스트가 실제로 GPU 경로를 사용하는지 확인하고 싶다.

Why this priority: `SETUP.md`의 설치 명령과 공식 TensorFlow Windows GPU 지원 정책 사이에 충돌 가능성이 있다.

Independent Test: `nvidia-smi`, TensorFlow GPU check, XGBoost version/GPU training smoke test, `python main.py self-test`를 실행하고 결과를 Environment Validation Log에 기록한다.

Acceptance Scenarios:
1. Given Windows Native environment is used, When TensorFlow `2.16.1` GPU check returns no GPU, Then system MUST mark TensorFlow GPU status as `TF_GPU_UNSUPPORTED_WINDOWS_NATIVE` and route GPU validation to WSL2 review.
2. Given WSL2 environment is used and TensorFlow detects GPU, When validation runs, Then status MAY be `TF_GPU_VALIDATED_WSL2`.
3. Given XGBoost is installed, When a GPU smoke test uses CUDA path, Then result MUST record `xgboost_version`, `device`, `training_status`, and failure reason if any.
4. Given Ollama is running, When `--lite` mode is used, Then VRAM profile MUST apply reduced TensorFlow/XGBoost/LSTM settings.

### User Story 5 - 모델·백테스트 파이프라인 검증 (Priority: P1)

Operator는 OHLCV 데이터, lagged feature generation, XGBoost-GPU, optional LSTM, leak-safe Walk-Forward CV, OOF probability backtest, ATR risk plan, Kelly sizing이 하나의 non-executing pipeline으로 작동하는지 확인하고 싶다.

Why this priority: 예측값이 거래 실행으로 오용되지 않도록, pipeline은 report-only/dry-run으로 제한되어야 한다.

Independent Test: AAPL, 005930.KS, NVDA, TSLA 샘플 명령을 실행해 pipeline status와 report output이 생성되는지 검증한다. live order는 생성되지 않아야 한다.

Acceptance Scenarios:
1. Given `python main.py self-test` is executed, When all core modules run, Then validation MUST return pass/fail per module.
2. Given a sample ticker command is executed, When pipeline completes, Then output MUST include prediction summary, backtest summary, risk gate status, and report path.
3. Given live broker credentials are absent, When pipeline runs, Then no broker order MAY be created.
4. Given required market data is missing or stale, When pipeline runs, Then candidate eligibility MUST be blocked and data failure MUST be reported.

### User Story 6 - 리포트 출력 및 감사 가능성 (Priority: P2)

Operator는 Daily Brief, Risk Dashboard, Journal, Thesis Report, Monthly Scorecard를 통해 매일·매주·매월 판단 근거를 검토하고 싶다.

Why this priority: 투자 OS는 예측기보다 reviewable decision system이어야 한다.

Independent Test: 샘플 데이터로 각 report를 생성하고 필수 필드, Gate status, rule violation, timestamp, source status가 포함되는지 검증한다.

Acceptance Scenarios:
1. Given candidate data is available, When Daily Brief is generated, Then it MUST include ticker, sector/bucket, score, entry, stop, TP1, TP2, risk, and verdict.
2. Given portfolio data is available, When Risk Dashboard is generated, Then it MUST include open risk, max drawdown, exposure, concentration, cash buffer, and blocked rules.
3. Given a trade or candidate decision occurs, When Journal is written, Then it MUST include reason, signal snapshot, risk rule, decision, result, and violation status.
4. Given month end occurs, When Monthly Scorecard is generated, Then Track-S and Track-L performance MUST be reported separately.

### User Story 7 - Approval Gate 및 범위 통제 (Priority: P1)

Reviewer는 Spec이 승인 가능한 상태인지 확인하고 싶다.

Why this priority: 실제 자금·broker·상품 범위가 미확정인 상태에서 Approved로 간주하면 운영 리스크가 커진다.

Independent Test: Spec 문서에서 critical `[NEEDS CLARIFICATION]` 항목이 0개인지, SC가 측정 가능한지, P1 scenario가 독립 테스트 가능한지 확인한다.

Acceptance Scenarios:
1. Given unresolved critical clarification exists, When approval review runs, Then status MUST remain `Draft` or `In Review`.
2. Given all critical questions are answered and SC tests pass, When reviewer signs off, Then status MAY move to `Approved`.
3. Given any ZERO rule can bypass logging, When review runs, Then approval MUST fail.

### Edge Cases

- EC1: OHLCV data missing -> 해당 후보는 `RED_DATA_MISSING` 또는 `AMBER_DATA_MISSING`으로 표시한다.
- EC2: stale price data -> data freshness threshold 통과 전까지 `ELIGIBLE` 금지.
- EC3: price gaps through stop -> Journal에 gap/slippage loss를 기록하고 `STOP_SLIPPAGE_REVIEW` 표시.
- EC4: market halt/closed -> 신규 진입 금지, 기존 position은 review-only 상태.
- EC5: FX conversion unavailable -> native currency 표시 후 AED 환산값은 `[NEEDS DATA]`.
- EC6: TensorFlow GPU not detected on Windows Native -> WSL2 validation required.
- EC7: XGBoost CUDA training failure -> CPU fallback 가능하나 GPU benchmark 성공으로 간주하지 않음.
- EC8: Ollama VRAM conflict -> `--lite` mode 또는 CPU fallback 적용.
- EC9: broker/account rule conflicts with spec -> broker rule wins; affected feature blocked.
- EC10: manual override requested -> reason, approver, timestamp, violated rule ID, affected candidate를 audit log에 기록.

---

## Requirements

### Functional Requirements

#### Portfolio / Track Control

- FR-001: System MUST maintain separate ledgers for `Track-S`, `Track-L`, and `Cash/Dry Powder`.
- FR-002: System MUST apply default allocation Track-S 20.00%, Track-L 75.00%, Cash/Dry Powder 5.00% unless explicitly configured otherwise.
- FR-003: System MUST require `TotalCapital`, `BaseCurrency`, `MarketScope`, `Broker`, `AccountType`, and `PermittedInstruments` before status can become `Approved`. `[NEEDS CLARIFICATION: actual values]`
- FR-004: System MUST prevent Track-S losses from being automatically funded by Track-L or Cash/Dry Powder.
- FR-005: System MUST block new Track-S entries when Track-S monthly drawdown reaches -5.00%.
- FR-006: System MUST treat Track-S +10.00% as a take-profit gate, not a guaranteed monthly target.
- FR-007: System MUST treat Track-L +20.00% over 3 years as an operating objective, not a guaranteed return.

#### Track-S Rule Contract

- FR-008: System MUST require every Track-S order plan to include `Entry`, `Stop`, `TP1`, `TP2`, `PositionSize`, `RiskAmount`, `RiskReward`, and `TimeStop`.
- FR-009: System MUST classify any Track-S candidate without a Stop as `ZERO_NO_STOP`.
- FR-010: System MUST support Track-S Initial Stop default of -4.00% and Hard Stop rule of no intentional loss beyond -5.00%, subject to gap/slippage logging.
- FR-011: System MUST support TP1 at +5.00% for 50.00% partial exit and TP2 at +10.00% for remaining exit.
- FR-012: System MUST support Time Stop: close or review if +3.00% is not reached within 20 trading days.
- FR-013: System MUST support Trailing Stop after +6.00% unrealized gain, using -3.00% from peak as default.
- FR-014: System MUST calculate Track-S Score with factors: Market Regime 20.00, Relative Strength 20.00, Volume Expansion 15.00, Breakout/Pullback 15.00, Catalyst 15.00, Risk/Reward 15.00.
- FR-015: System MUST mark Track-S as Green only when Score ≥75.00, Risk/Reward ≥2.00, Liquidity Pass, Market Regime Pass, Catalyst Pass, and Stop defined.
- FR-016: System MUST mark Track-S as Amber when Score is 65.00~74.99 unless Red or ZERO applies.
- FR-017: System MUST exclude penny stocks, illiquid instruments, opaque-disclosure securities, and collapsed-volume candidates.
- FR-018: System MUST calculate Track-S position sizing from account risk and stop distance, defaulting to 0.50%~1.00% risk per trade.
- FR-019: System MUST limit total Track-S open risk to 2.00% of Track-S capital unless explicitly overridden.

#### Track-L Rule Contract

- FR-020: System MUST support Track-L buckets: Core Global Equity ETF 40.00%, Quality/Dividend/Cashflow 20.00%, AI Infrastructure/Semiconductors/Power 15.00%, Commodity/Energy/Materials 10.00%, Bonds/T-bills/Money Market 10.00%, Opportunistic Cash 5.00%.
- FR-021: System MUST calculate Track-L Score with factors: Business Quality 25.00, Earnings/Cashflow 20.00, Balance Sheet 15.00, Valuation 15.00, Structural Theme 15.00, Governance/Risk 10.00.
- FR-022: System MUST mark Track-L as Green only when Score ≥80.00, valuation acceptable, bucket capacity available, and thesis documented.
- FR-023: System MUST mark Track-L as Amber when Score is 70.00~79.99 unless Red or ZERO applies.
- FR-024: System MUST support Initial Buy of 30.00% of target allocation.
- FR-025: System MUST support DCA cadence as monthly or quarterly. `[NEEDS CLARIFICATION: final cadence]`
- FR-026: System MUST support Drawdown Add at -10.00% and -20.00% only if thesis remains valid.
- FR-027: System MUST support rebalance review semiannually or when target bucket allocation deviates by ±5.00%.
- FR-028: System MUST flag any Track-L single-name exposure above 12.00% for rebalance review.
- FR-029: System MUST require Track-L exit rule before `ACCUMULATE` verdict.

#### Risk Gate / Fail-safe Contract

- FR-030: System MUST classify every candidate as Green, Amber, Red, or ZERO before final verdict.
- FR-031: System MUST block margin, options, 0DTE, leveraged ETFs, short-selling, and penny stocks by default in v0.2.0. `[NEEDS CLARIFICATION: whether any are permitted after separate approval]`
- FR-032: System MUST classify AI-only automatic buy/sell as `ZERO_AI_ONLY_AUTO_EXECUTION`.
- FR-033: System MUST classify internal/non-public information use as `ZERO_NON_PUBLIC_INFORMATION`.
- FR-034: System MUST record every candidate decision in Journal with timestamp, track, candidate, score, gate status, decision, reason, and violated rule IDs.
- FR-035: System MUST maintain immutable audit records for overrides, rule violations, blocked candidates, and failed data validation.
- FR-036: System MUST label all candidate outputs as screening outputs, not personalized investment recommendations.

#### Windows / GPU Environment Contract

- FR-037: System MUST define `workspaces/stock_rtx4060/` as the implementation folder contract unless a future spec revision changes it.
- FR-038: System MUST include these expected files: `hw_profile.py`, `feature_engine.py`, `ensemble_model.py`, `backtester.py`, `risk_rules.py`, `recommendation_engine.py`, `reports.py`, and `main.py`.
- FR-039: System MUST capture `nvidia-smi` output in Environment Validation Log before GPU mode can be considered validated.
- FR-040: System MUST validate Python 3.11 environment and virtual environment activation before package validation.
- FR-041: System MUST validate TensorFlow GPU detection using `tf.config.list_physical_devices('GPU')` and record environment type: `WindowsNative` or `WSL2`.
- FR-042: System MUST NOT mark TensorFlow GPU as approved on Windows Native for TensorFlow versions after 2.10 unless a documented supported compatibility path is confirmed.
- FR-043: System MUST route TensorFlow GPU failure on Windows Native to WSL2 validation or CPU-only mode.
- FR-044: System MUST validate XGBoost version and GPU training path separately from TensorFlow.
- FR-045: System MUST record whether XGBoost uses CUDA, CPU fallback, or failed execution.
- FR-046: System MUST support VRAM profiles: standalone, Ollama small-model `--lite`, and Ollama high-VRAM conflict mode.
- FR-047: System MUST treat `SETUP.md` benchmark numbers as baseline expectations only; actual benchmark must be measured on the target device.

#### Model / Backtest / CLI Contract

- FR-048: System MUST support `python main.py self-test` as the core validation command and `python main.py --test` as a legacy alias.
- FR-049: System MUST support sample ticker commands for AAPL, `005930.KS`, NVDA, and TSLA as dry-run/report-only validation cases.
- FR-050: System MUST support OHLCV loading, feature generation, model scoring, backtest summary, and report output without live order execution.
- FR-051: System MUST support leak-safe Walk-Forward CV reporting with an explicit train/test gap before model outputs are considered reviewable.
- FR-052: System MUST support Kelly sizing output for backtest analysis but MUST NOT use Kelly sizing to auto-place orders.
- FR-052A: System MUST prefer out-of-fold probabilities for dry-run backtest metrics when they are available.
- FR-052B: System MUST generate ATR-adjusted stop/target plan fields for recommendation reports when OHLCV data includes enough rows.
- FR-053: System MUST block candidate eligibility if required portfolio/risk data is missing.
- FR-053A: System MUST support a report-only `recommend` CLI command that ranks Track-S / Track-L candidates and labels outputs as `screening_output_only`.

#### Report Output Contract

- FR-054: System MUST generate Daily Brief with candidate, sector/bucket, score, entry, stop, TP1, TP2, risk, and verdict.
- FR-055: System MUST generate Risk Dashboard with open risk, max drawdown, exposure, cash buffer, single-name concentration, margin status, and blocked rules.
- FR-056: System MUST generate Track-S Journal with setup, signal, catalyst, size, stop, exit, P/L, and rule compliance.
- FR-057: System MUST generate Track-L Thesis Report with bucket, thesis, score, buy rule, exit rule, thesis-damage condition, and review date.
- FR-058: System MUST generate Monthly Scorecard with Track-S return, Track-S max monthly loss, Track-S rule violations, Track-L return, Track-L concentration, Cash buffer, and Journal completion rate.
- FR-059: System MUST surface `[NEEDS CLARIFICATION]` markers in reports when required configuration or data is missing.

### Non-Functional Requirements

- NFR-001 (Auditability): Every verdict MUST be traceable to input data, score factors, Risk Gate, rule IDs, and timestamp.
- NFR-002 (Determinism): Same input data and config MUST produce the same score and verdict.
- NFR-003 (Data Freshness): Daily Brief MUST show source timestamp for market, portfolio, and news data. `[NEEDS CLARIFICATION: market-specific freshness threshold]`
- NFR-004 (Security/Privacy): Broker credentials, API keys, and personal financial data MUST NOT appear in plaintext logs or reports.
- NFR-005 (Compliance): Reports MUST avoid guaranteed-return language and MUST block non-public information usage.
- NFR-006 (Performance): Candidate scan for configured universe SHOULD complete within 5 minutes after required data is available. `[NEEDS CLARIFICATION: expected universe size]`
- NFR-007 (GPU Validation): GPU mode MUST not be marked valid unless TensorFlow/XGBoost checks are explicitly logged.
- NFR-008 (Resilience): If a required data source fails, system MUST degrade to report-only or blocked-eligibility mode.
- NFR-009 (Explainability): Every Red or ZERO verdict MUST include a human-readable reason and violated rule ID.
- NFR-010 (Maintainability): Allocation, score weights, thresholds, exclusions, and VRAM profiles SHOULD be configurable without implementation code changes.
- NFR-011 (Usability): Green/Amber/Red/ZERO status MUST be visible in all candidate and report tables.
- NFR-012 (Portability): Windows Native, WSL2, CPU-only, and Lite Mode statuses MUST be distinguishable in validation logs.
- NFR-013 (No Silent Assumptions): Missing critical values MUST remain visible through `[NEEDS CLARIFICATION]`.
- NFR-014 (Reviewability): Approval review MUST be possible using only the Spec, validation logs, reports, and traceability table.

---

## Key Entities / Data

| Entity | Description | Required Attributes |
|---|---|---|
| `Portfolio` | 전체 운영 계정 view | `total_capital`, `base_currency`, `broker`, `account_type`, `tracks` |
| `Track` | Track-S, Track-L, Cash ledger | `track_id`, `allocation_pct`, `capital_value`, `current_pnl`, `max_loss_rule` |
| `CandidateAsset` | 평가 대상 종목/ETF | `symbol`, `market`, `sector_or_bucket`, `instrument_type`, `liquidity_status` |
| `MarketDataSnapshot` | OHLCV/volume snapshot | `symbol`, `timestamp`, `OHLCV`, `ATR`, `spread`, `volume_ratio` |
| `FundamentalSnapshot` | 장기 평가 데이터 | `symbol`, `timestamp`, `ROIC`, `margin`, `EPS`, `FCF`, `debt`, `valuation_metrics` |
| `Catalyst` | 실적, 뉴스, 정책, macro event | `catalyst_id`, `type`, `source`, `date`, `relevance_score` |
| `SignalScore` | Track-S/Track-L scoring result | `track`, `factor_scores`, `total_score`, `threshold_result` |
| `RiskGateResult` | Green/Amber/Red/ZERO 판정 | `status`, `violated_rules`, `reason`, `override_required` |
| `OrderPlan` | 비실행 주문 계획 | `entry`, `stop`, `TP1`, `TP2`, `position_size`, `risk_amount`, `approval_status` |
| `BacktestRun` | 모델/전략 검증 실행 | `ticker`, `period`, `horizon`, `walk_forward_result`, `metrics`, `device_mode` |
| `EnvironmentValidationLog` | 설치·GPU 검증 로그 | `os_mode`, `python_version`, `nvidia_smi`, `tensorflow_gpu`, `xgboost_gpu`, `vram_profile` |
| `JournalEntry` | 의사결정 감사 기록 | `timestamp`, `actor`, `decision`, `rationale`, `rule_ids`, `result` |
| `Report` | 산출물 | `report_type`, `period`, `generated_at`, `input_sources`, `summary_metrics` |
| `RuleViolation` | Rule breach | `rule_id`, `severity`, `action_taken`, `approver`, `timestamp` |

---

## Interfaces & Contracts

### Folder Contract

```text
workspaces/stock_rtx4060/
├── hw_profile.py
├── feature_engine.py
├── ensemble_model.py
├── backtester.py
├── risk_rules.py
├── recommendation_engine.py
├── reports.py
├── main.py
```

### CLI Contract

| Command | Purpose | Required Result |
|---|---|---|
| `python main.py self-test` | 모든 핵심 모듈 검증 | module별 pass/fail |
| `python main.py predict --ticker AAPL --horizon 5 --period 5y` | US sample validation | report-only output |
| `python main.py predict --ticker 005930.KS --horizon 5 --period 3y` | KRX sample validation | report-only output |
| `python main.py predict --ticker NVDA --period 3y --prefer-gpu` | GPU/backtest sample | report-only output |
| `python main.py predict --ticker TSLA --period 3y --prefer-gpu` | GPU/backtest sample | report-only output |
| `python main.py predict --ticker AAPL --lite` | Ollama 병행 VRAM profile | reduced VRAM output |
| `python main.py recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations` | Offline candidate ranking validation | `screening_output_only` Algorithm v2 Markdown/JSON output |

### Environment Validation Contract

| Check | Required Evidence | Failure Behavior |
|---|---|---|
| CUDA / GPU | `nvidia-smi` output | GPU mode not approved |
| Python | Python 3.11 version | environment blocked |
| TensorFlow | `tf.config.list_physical_devices('GPU')` | Windows Native failure -> WSL2 review or CPU-only |
| XGBoost | version + CUDA smoke test | CPU fallback allowed, GPU benchmark not approved |
| VRAM Profile | standalone / lite / conflict mode | reduce batch or switch CPU |
| Benchmark | actual measured time | SETUP baseline not accepted as real result |

### Data Input Contract

| Input | Track-S | Track-L | Failure Behavior |
|---|---:|---:|---|
| OHLCV | Required | Required | Block candidate if missing |
| Volume/Liquidity | Required | Supporting | Red or Amber depending on field |
| Fundamentals | Supporting | Required | Block Track-L candidate if missing |
| Earnings Calendar | Required | Required | Amber if unavailable |
| Macro/Rates/Oil | Required | Required | Amber if unavailable |
| News/Sentiment | Required | Supporting | Amber if unavailable |
| Portfolio/Risk | Required | Required | Block all eligibility decisions if missing |
| Trading Journal | Required | Required | Report compliance failure |

### Output Report Contract

| Report | Cadence | Minimum Fields |
|---|---|---|
| Daily Brief | Daily before trading window | `candidate`, `score`, `gate`, `entry`, `stop`, `TP1`, `TP2`, `position_size`, `verdict` |
| Risk Dashboard | Daily and on demand | `open_risk`, `max_drawdown`, `cash_buffer`, `concentration`, `margin_status`, `blocked_rules` |
| Track-S Journal | Per decision | `setup`, `signal`, `size`, `stop`, `exit`, `result`, `rule_compliance` |
| Track-L Thesis Report | On entry/review | `bucket`, `thesis`, `score`, `buy_rule`, `exit_rule`, `thesis_damage_condition` |
| Monthly Scorecard | Monthly | `Track-S_return`, `Track-L_return`, `rule_violations`, `journal_completion`, `concentration`, `cash_buffer` |

### Candidate Verdict Contract

| Verdict | Meaning | Execution Status |
|---|---|---|
| `ELIGIBLE` | Track-S gates passed | Manual approval still required |
| `ACCUMULATE` | Track-L gates passed | Manual approval still required |
| `AMBER` | Borderline or incomplete candidate | No execution without review |
| `RED_*` | Risk/data failure | Blocked |
| `ZERO_*` | Prohibited condition | Blocked and logged |
| `BLOCKED_MONTHLY_LOSS_LIMIT` | Track-S monthly loss limit reached | Blocked |
| `TF_GPU_UNSUPPORTED_WINDOWS_NATIVE` | TensorFlow GPU unsupported path | WSL2 or CPU-only review |
| `XGB_GPU_VALIDATED` | XGBoost CUDA path verified | GPU benchmark allowed |

---

## Assumptions & Dependencies

### Assumptions

- A1: Default total capital is 100,000.00 AED for example calculations only. `[NEEDS CLARIFICATION: actual total capital]`
- A2: Default allocation is Track-S 20.00%, Track-L 75.00%, Cash/Dry Powder 5.00% unless changed.
- A3: Track-S +10.00% is a take-profit gate, not a guaranteed monthly return.
- A4: Track-L +20.00% over 3 years is approximately 6.27% CAGR, not guaranteed.
- A5: Stocks and ETFs are default permitted instruments. `[NEEDS CLARIFICATION: final permitted instrument list]`
- A6: Margin, options, 0DTE, leveraged ETFs, penny stocks, and illiquid securities are disabled by default.
- A7: Operator approval is required for all real trades in v0.2.0.
- A8: AED is the default reporting currency. `[NEEDS CLARIFICATION: base currency and FX source]`
- A9: BlackRock/Vanguard outlook data is contextual risk input only, not a trading signal.
- A10: TensorFlow GPU validation on Windows Native may fail for version 2.16.1; WSL2 route is required for GPU approval.
- A11: SETUP benchmark numbers are baseline expectations and must be remeasured on target hardware.
- A12: Tax and regulatory constraints are not encoded. `[NEEDS CLARIFICATION: tax jurisdiction and relevant market rules]`

### Dependencies

- D1: Reliable OHLCV and volume/liquidity data provider.
- D2: Fundamentals and valuation data provider for Track-L.
- D3: Earnings calendar, macro/rates/oil, and news/sentiment sources.
- D4: Broker or manual portfolio ledger for holdings, cash, and realized/unrealized P/L.
- D5: Journal storage with immutable audit capability.
- D6: Windows environment, NVIDIA driver, CUDA visibility, Python 3.11, venv.
- D7: WSL2 + NVIDIA CUDA route if TensorFlow GPU is required.
- D8: XGBoost CUDA-compatible NVIDIA GPU path.
- D9: Operator approval workflow for overrides and execution.
- D10: Broker/account-specific margin and permitted product rules.

---

## Success Criteria

### Measurable Outcomes

- SC-001: Allocation calculation matches configured percentages within ±0.01% in 100% of allocation tests.
- SC-002: Track-S monthly loss block triggers in 100% of test cases when monthly loss ≤ -5.00%.
- SC-003: 0 candidates with missing Stop are marked `ELIGIBLE`.
- SC-004: 100% of Track-S `ELIGIBLE` candidates contain Entry, Stop, TP1, TP2, PositionSize, RiskAmount, Risk/Reward, and TimeStop.
- SC-005: 100% of ZERO violations are blocked and logged with rule ID, reason, timestamp, and actor.
- SC-006: Track-S scoring returns identical result for identical inputs in 100% of deterministic tests.
- SC-007: Track-L candidates that would push single-name exposure above 12.00% are flagged in 100% of test cases.
- SC-008: `python main.py self-test` returns explicit pass/fail for `hw_profile`, `feature_engine`, `ensemble_model`, `backtester`, and `main` modules.
- SC-009: Environment Validation Log records OS mode, Python version, `nvidia-smi`, TensorFlow GPU result, XGBoost GPU result, and VRAM profile before GPU mode is approved.
- SC-010: TensorFlow GPU is not marked approved on Windows Native TensorFlow >2.10 unless a documented supported path is validated.
- SC-011: XGBoost GPU benchmark is marked approved only when CUDA smoke test succeeds and device mode is recorded.
- SC-012: All sample ticker commands produce report-only output and 0 live broker orders.
- SC-012A: `python main.py recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5` produces `recommendations_algo_v2_*.md/json` with `screening_output_only=True` and 0 live broker orders.
- SC-013: Daily Brief includes all required fields for at least 95.00% of trading days where all required data sources are available.
- SC-014: Journal coverage reaches 100.00% for approved, rejected, blocked, and overridden decisions.
- SC-015: Monthly Scorecard separates Track-S and Track-L returns in 100.00% of monthly reports.
- SC-016: Cash/Dry Powder remains ≥5.00% unless approved reallocation exists; violations are flagged in 100.00% of monthly reviews.
- SC-017: Every Red and ZERO verdict includes human-readable reason and violated rule ID in 100.00% of reviewed report samples.
- SC-018: Approval-ready status requires 0 unresolved critical `[NEEDS CLARIFICATION]` items.

---

## Open Questions & Clarifications

### Open Questions

- Q1: 실제 총 투자금은 얼마인가? 예시값 100,000.00 AED를 유지할 것인가?
- Q2: Base currency는 AED로 확정인가, 아니면 USD/KRW 등 별도 기준이 필요한가?
- Q3: 거래 대상 시장은 US, Korea, UAE, Global ETF 중 어디까지 포함하는가?
- Q4: 허용 상품은 stocks/ETFs only인가? Bonds, T-bills, money market funds는 어떤 형태로 반영할 것인가?
- Q5: 사용 broker와 account type은 무엇인가? Cash account, margin account, portfolio margin 여부가 필요하다.
- Q6: Margin, options, 0DTE, leveraged ETF는 완전 금지인가, 별도 승인 후 허용 가능한가?
- Q7: 데이터 공급원은 무엇인가? OHLCV, fundamentals, earnings calendar, macro/rates/oil, news/sentiment 각각 필요하다.
- Q8: Track-L DCA cadence는 monthly인가 quarterly인가?
- Q9: 알림/리포트 채널은 무엇인가? File, email, Telegram, Slack, dashboard, spreadsheet 중 선택 필요.
- Q10: 자동화 수준은 `report_only`, `dry_run`, `manual_approval` 중 어디까지 v0.2.0 범위인가?
- Q11: TensorFlow GPU가 꼭 필요한가, 아니면 XGBoost GPU + TensorFlow CPU도 허용 가능한가?
- Q12: WSL2 설치 및 운영을 허용하는가?

### Clarifications Log

- 2026-05-02 Session:
  - Q: “spec.md 작성해달라” -> A: 초기 `Spec.md` 작성.
  - Q: “문서 확인후 다시 작성해 달라” -> A: `붙여넣은 텍스트 (1).txt`, `uiux.md`, `SETUP.md`, `plan.md`, Spec rules/checklists를 재검토하고 Windows/GPU 실행환경까지 통합한 v0.2.0으로 재작성.
  - Q: 실제 투자금/시장/broker/상품/데이터 공급원/자동화 수준 -> A: 미확정. `[NEEDS CLARIFICATION]` 유지.

---

## Risks & Mitigations

| Risk ID | Risk | Impact | Mitigation |
|---|---|---:|---|
| R1 | Track-S +10.00% monthly target is aggressive | High | 목표 수익이 아니라 TP Gate로 취급; -5.00% monthly loss block 적용 |
| R2 | Stop 미실행 또는 gap/slippage | High | gap loss Journal 기록, slippage review, position sizing 축소 |
| R3 | Margin 손실 확대 | High | v0.2.0 기본 금지; broker/account rule 확정 전 block |
| R4 | Options/0DTE nonlinear loss | High | v0.2.0 기본 금지 |
| R5 | AI/commodity theme concentration | Medium | Core/Quality/Cash bucket과 12.00% concentration review 적용 |
| R6 | 고평가 추격매수 | Medium | Valuation Gate, DCA, thesis review 적용 |
| R7 | Missing/stale data false eligibility | High | required data missing 시 eligibility block |
| R8 | AI prediction over-trust | High | report-only/dry-run, manual approval, AI-only auto-buy ZERO |
| R9 | TensorFlow GPU Windows Native mismatch | High | TensorFlow GPU approval은 WSL2 검증 또는 documented compatible path 필요 |
| R10 | XGBoost GPU version/CUDA conflict | Medium | CUDA smoke test와 CPU fallback 명시 |
| R11 | Ollama VRAM conflict | Medium | `--lite`, reduced batch, CPU fallback |
| R12 | Broker/account rules differ from generic assumptions | High | broker rule dependency; product/margin features blocked until confirmed |
| R13 | Tax/regulatory jurisdiction omitted | Medium | scope 밖으로 유지하되 Approved 전 jurisdiction question 해결 |
| R14 | Report/Journaling 미작성 | High | Journal coverage SC-014 및 Monthly Scorecard compliance 적용 |

---

## Traceability

| Item | Links to Requirements | Links to Success Criteria |
|---|---|---|
| User Story 1 - Track 분리 및 자금 보호 | FR-001~FR-007 | SC-001, SC-002, SC-016 |
| User Story 2 - Track-S 후보 평가 | FR-008~FR-019, FR-030~FR-036 | SC-003~SC-006, SC-017 |
| User Story 3 - Track-L 편입 평가 | FR-020~FR-029, FR-030~FR-036 | SC-007, SC-015, SC-017 |
| User Story 4 - Windows / GPU 환경 검증 | FR-037~FR-047 | SC-008~SC-011 |
| User Story 5 - 모델·백테스트 파이프라인 검증 | FR-048~FR-053 | SC-008, SC-012 |
| Recommendation scanner | FR-036, FR-048~FR-053A | SC-012, SC-012A, SC-017 |
| User Story 6 - 리포트 출력 및 감사 가능성 | FR-034~FR-036, FR-054~FR-059 | SC-013~SC-017 |
| User Story 7 - Approval Gate 및 범위 통제 | FR-003, FR-031, FR-035, FR-059 | SC-018 |

---

## Approval-Readiness Assessment

Status: Not approval-ready.

Blocking Issues:

- Critical operating parameters unresolved: total capital, base currency, markets, broker/account type, permitted instruments, data providers, automation level.
- TensorFlow GPU path is unresolved for Windows Native TensorFlow 2.16.1; WSL2 or CPU-only acceptance must be decided.
- Data freshness thresholds and universe size are undefined.
- Broker-specific margin/product rules are undefined.
- Several requirements intentionally retain `[NEEDS CLARIFICATION]` markers.

Smallest Changes Needed for `Approved`:

1. Resolve Q1~Q12.
2. Confirm default allocation or replace with final allocation.
3. Select data providers and define freshness thresholds by market.
4. Confirm broker/account/product restrictions.
5. Decide TensorFlow GPU path: WSL2, Windows Native alternative, or CPU-only.
6. Run and attach Environment Validation Log.
7. Run deterministic tests for SC-001~SC-018.
8. Confirm all ZERO rules are blocked and logged.

---

## Changelog

- v0.1.0 (2026-05-02): Initial Draft Spec.md created from `uiux.md`, `plan.md`, and Spec.md template/rules.
- v0.2.0 (2026-05-02): Rewritten after reviewing `붙여넣은 텍스트 (1).txt`, `uiux.md`, `SETUP.md`, `plan.md`; added Windows/GPU validation, CLI contract, environment logs, model/backtest contract, and stronger approval gate.
- v0.2.1 (2026-05-02): Added active package path update and report-only `recommend` CLI contract for `workspaces/stock_rtx4060/recommendation_engine.py`.

---

## Reference Links

- TensorFlow Install with pip: https://www.tensorflow.org/install/pip
- XGBoost GPU Support: https://xgboost.readthedocs.io/en/latest/gpu/
- XGBoost Installation Guide: https://xgboost.readthedocs.io/en/stable/install.html
- NVIDIA CUDA on WSL: https://developer.nvidia.com/cuda/wsl
- Microsoft Enable NVIDIA CUDA on WSL 2: https://learn.microsoft.com/en-us/windows/ai/directml/gpu-cuda-in-wsl
- FINRA Understanding the New Intraday Margin Requirements: https://www.finra.org/investors/insights/intraday-margin-requirements
- FINRA Regulatory Notice 26-10: https://www.finra.org/rules-guidance/notices/26-10
- BlackRock Q2 2026 Investment Outlook: https://www.blackrock.com/corporate/insights/blackrock-investment-institute/publications/outlook
- Vanguard Capital Markets Model Forecasts: https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vemo-return-forecasts.html
