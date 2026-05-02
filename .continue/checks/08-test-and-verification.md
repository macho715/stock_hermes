---
name: Test and Verification
description: Enforce completion evidence for code, recommendation, and GPU-related changes.
---

Review this change for missing verification evidence.

Fail this check if:

- Python code changed but no compile or smoke test result is documented.
- Recommendation logic changed but no synthetic recommendation report was generated and inspected.
- Risk gate changed but no corresponding test was added or updated in `tests/test_core.py`.
- GPU behavior changed but runtime/GPU evidence is missing.
- The change claims completion while tests fail or are not run.
- The change suppresses errors instead of fixing root causes.

Minimum evidence after general code changes:

```powershell
python -m compileall .
python main.py --help
.\run.ps1 self-test
```

Test evidence:

```powershell
C:\Users\jichu\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

Recommendation logic evidence:

```powershell
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports\algo_v2_validation
```

Benchmark or GPU evidence when relevant:

```powershell
.\run.ps1 env --xgboost --output reports\runtime_status_xgboost.json
.\run.ps1 benchmark --rows 800 --repeats 1 --include-gpu --output-dir reports\gpu_validation
```

Pass only if:

- Commands pass or failures are documented with root cause and next action.
- Changed files, commands run, pass/fail results, remaining risks, assumptions, and unverified areas are summarized.
