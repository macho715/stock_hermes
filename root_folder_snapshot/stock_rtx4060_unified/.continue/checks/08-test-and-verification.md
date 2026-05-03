---
name: Test and Verification
description: Enforce completion evidence for code, recommendation, and GPU-related changes.
---

Review this change for missing verification evidence.

Fail this check if:

- Python code changed but no compile or smoke test result is documented.
- Recommendation logic changed but no synthetic recommendation report was generated and inspected.
- Ops v1 workflow changed but no Ops v1 smoke output was generated and inspected.
- Provider or audit logging changed but no audit JSONL artifact was generated and inspected.
- MCP adapter contract changed but no boundary test confirms read/report-only behavior.
- Risk gate changed but no corresponding test was added or updated in `tests/test_core.py`.
- GPU behavior changed but runtime/GPU evidence is missing.
- The change claims completion while tests fail or are not run.
- The change suppresses errors instead of fixing root causes.

Minimum evidence after general code changes:

```powershell
.\.venv\Scripts\python.exe -m compileall main.py src tests
python main.py --help
.\run.ps1 self-test
```

Test evidence:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Recommendation logic evidence:

```powershell
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports\algo_v2_validation
```

Ops v1 workflow evidence:

```powershell
.\run.ps1 ops-v1 --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports\ops_v1_validation
```

Provider/audit evidence:

```powershell
.\run.ps1 recommend --data-provider synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports\recommendations_phase1_smoke
```

Benchmark or GPU evidence when relevant:

```powershell
.\run.ps1 env --xgboost --output reports\runtime_status_xgboost.json
.\run.ps1 benchmark --rows 800 --repeats 1 --include-gpu --output-dir reports\gpu_validation
```

Pass only if:

- Commands pass or failures are documented with root cause and next action.
- Changed files, commands run, pass/fail results, remaining risks, assumptions, and unverified areas are summarized.
