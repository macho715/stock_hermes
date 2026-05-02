---
name: GPU Claim Validation
description: Enforce GPU validation evidence before RTX4060, CUDA, XGBoost, or TensorFlow performance claims.
---

Review this change for GPU, CUDA, TensorFlow, XGBoost, and RTX4060 claims.

Fail this check if any change does one or more of the following:

- Claims GPU speedup, CUDA success, RTX4060 acceleration, or TensorFlow GPU support without runtime evidence.
- Assumes TensorFlow GPU works on Windows Native for TensorFlow versions after 2.10.
- Treats XGBoost GPU validation as equivalent to TensorFlow GPU validation.
- Removes CPU fallback when GPU validation fails.
- Omits `nvidia-smi`, Python version, XGBoost version, TensorFlow GPU status, selected device path, or VRAM profile from GPU evidence.

Pass only if:

- XGBoost GPU and TensorFlow GPU are validated separately when mentioned.
- CPU fallback remains functional.
- Benchmark reports compare equivalent CPU/GPU workloads where possible.

Required local evidence for GPU-related changes:

```powershell
.\run.ps1 env --xgboost --output reports\runtime_status_xgboost.json
.\run.ps1 benchmark --rows 800 --repeats 1 --include-gpu --output-dir reports\gpu_validation
```

When failing, classify the claim as AMBER unless it directly affects correctness, then classify it as RED.
