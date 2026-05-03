"""Hardware and GPU validation utilities for ``stock_rtx4060``.

The module avoids importing TensorFlow or XGBoost at import time. Validation is
performed through short subprocess smoke tests with timeouts.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CPU_LOGICAL_CORES = os.cpu_count() or 1
CPU_EFFECTIVE_WORKERS = max(1, min(16, CPU_LOGICAL_CORES - 2))
CPU_INTRAOP_THREADS = max(1, min(6, CPU_EFFECTIVE_WORKERS))
CPU_INTEROP_THREADS = max(1, min(4, CPU_EFFECTIVE_WORKERS))

os.environ.setdefault("OMP_NUM_THREADS", str(CPU_INTRAOP_THREADS))
os.environ.setdefault("MKL_NUM_THREADS", str(CPU_INTRAOP_THREADS))
os.environ.setdefault("OPENBLAS_NUM_THREADS", str(CPU_INTRAOP_THREADS))
os.environ.setdefault("NUMEXPR_NUM_THREADS", str(CPU_EFFECTIVE_WORKERS))
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    timed_out: bool = False


@dataclass(frozen=True)
class RuntimeStatus:
    os_name: str
    python: str
    nvidia_smi: dict[str, Any]
    tensorflow_gpu: dict[str, Any]
    xgboost_gpu: dict[str, Any]
    gate: str
    notes: list[str]


HW_PROFILE: dict[str, Any] = {
    "target_machine": {
        "cpu": "Intel Core i5-13500HX",
        "gpu": "NVIDIA GeForce RTX 4060 Laptop",
        "vram_gb": 8,
        "os": "Windows 11 + optional WSL2",
    },
    "runtime_machine": {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "logical_cores": CPU_LOGICAL_CORES,
        "workers": CPU_EFFECTIVE_WORKERS,
    },
    "optimization": {
        "xgboost_gpu_device": "cuda",
        "xgboost_tree_method": "hist",
        "tensorflow_native_windows_gpu": "unsupported_after_tf_2_10",
        "recommended_tf_gpu_path": "WSL2",
    },
}


def _run(command: list[str], timeout_s: int = 12) -> CommandResult:
    command_text = " ".join(command)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        return CommandResult(False, command_text, stderr=str(exc), returncode=None)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            False,
            command_text,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            returncode=None,
            timed_out=True,
        )
    return CommandResult(
        completed.returncode == 0,
        command_text,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        returncode=completed.returncode,
    )


def _python_probe(code: str, timeout_s: int = 20) -> dict[str, Any]:
    result = _run([sys.executable, "-c", code], timeout_s=timeout_s)
    payload: dict[str, Any] = {
        "ok": False,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "timed_out": result.timed_out,
    }
    if not result.ok:
        return payload
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        parsed.setdefault("ok", True)
        return parsed
    payload["stderr"] = payload["stderr"] or "probe returned no JSON payload"
    return payload


def detect_nvidia_smi(timeout_s: int = 8) -> dict[str, Any]:
    if shutil.which("nvidia-smi") is None:
        return {"ok": False, "reason": "nvidia-smi not found on PATH"}
    result = _run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        timeout_s=timeout_s,
    )
    if not result.ok:
        return asdict(result)
    gpus = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 4:
            gpus.append(
                {
                    "name": parts[0],
                    "memory_total_mb": _safe_int(parts[1]),
                    "driver_version": parts[2],
                    "compute_capability": parts[3],
                }
            )
    return {"ok": bool(gpus), "gpus": gpus, "raw": result.stdout}


def tensorflow_gpu_status(timeout_s: int = 25) -> dict[str, Any]:
    code = r'''
import json
payload = {"ok": False}
try:
    import tensorflow as tf
    payload["version"] = tf.__version__
    gpus = tf.config.list_physical_devices("GPU")
    payload["gpu_count"] = len(gpus)
    payload["gpus"] = [gpu.name for gpu in gpus]
    payload["ok"] = len(gpus) > 0
except Exception as exc:
    payload["error"] = f"{type(exc).__name__}: {exc}"
print(json.dumps(payload, ensure_ascii=False))
'''
    payload = _python_probe(code, timeout_s=timeout_s)
    if platform.system().lower() == "windows":
        payload.setdefault("notes", []).append(
            "TensorFlow >=2.11 GPU is not supported on native Windows; use WSL2 for NVIDIA CUDA GPU."
        )
    return payload


def xgboost_gpu_status(timeout_s: int = 30) -> dict[str, Any]:
    code = r'''
import json
payload = {"ok": False}
try:
    import numpy as np
    from xgboost import XGBClassifier
    X = np.random.default_rng(42).normal(size=(96, 8))
    y = (X[:, 0] + X[:, 1] * 0.25 > 0).astype(int)
    model = XGBClassifier(
        n_estimators=8,
        max_depth=2,
        learning_rate=0.2,
        tree_method="hist",
        device="cuda",
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X, y)
    payload.update({"ok": True, "version": __import__("xgboost").__version__, "device": "cuda"})
except Exception as exc:
    try:
        import xgboost
        payload["version"] = xgboost.__version__
    except Exception:
        pass
    payload["error"] = f"{type(exc).__name__}: {exc}"
print(json.dumps(payload, ensure_ascii=False))
'''
    return _python_probe(code, timeout_s=timeout_s)


def runtime_status(include_tensorflow: bool = False, include_xgboost: bool = True) -> RuntimeStatus:
    notes: list[str] = []
    nvidia = detect_nvidia_smi()
    tf_status = {"ok": False, "skipped": True, "reason": "not requested"}
    xgb_status = {"ok": False, "skipped": True, "reason": "not requested"}

    if include_tensorflow:
        tf_status = tensorflow_gpu_status()
    if include_xgboost:
        xgb_status = xgboost_gpu_status()

    if platform.system().lower() == "windows":
        notes.append("Windows Native TensorFlow GPU is AMBER unless WSL2 GPU validation passes.")
    if not nvidia.get("ok"):
        notes.append("nvidia-smi did not validate an NVIDIA GPU; benchmark will run CPU-only here.")
    if include_xgboost and not xgb_status.get("ok"):
        notes.append("XGBoost CUDA smoke test did not pass; XGBoost should fall back to CPU.")

    gate = "GREEN" if include_xgboost and xgb_status.get("ok") and nvidia.get("ok") else "AMBER"
    return RuntimeStatus(
        os_name=platform.platform(),
        python=sys.version.split()[0],
        nvidia_smi=nvidia,
        tensorflow_gpu=tf_status,
        xgboost_gpu=xgb_status,
        gate=gate,
        notes=notes,
    )


def xgb_params(prefer_gpu: bool = False, lite: bool = False, random_state: int = 42) -> dict[str, Any]:
    return {
        "n_estimators": 120 if lite else 300,
        "max_depth": 4 if lite else 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "logloss",
        "random_state": random_state,
        "tree_method": "hist",
        "device": "cuda" if prefer_gpu else "cpu",
        "n_jobs": CPU_EFFECTIVE_WORKERS,
    }


def configure_tensorflow(vram_limit_mb: int = 6_144, mixed_precision: bool = True) -> dict[str, Any]:
    status = {"ok": False, "gpu_available": False, "vram_limit_mb": vram_limit_mb}
    try:
        import tensorflow as tf  # type: ignore

        gpus = tf.config.list_physical_devices("GPU")
        status["version"] = tf.__version__
        status["gpu_count"] = len(gpus)
        if not gpus:
            status["error"] = "no TensorFlow-visible GPU"
            return status
        try:
            tf.config.set_logical_device_configuration(
                gpus[0],
                [tf.config.LogicalDeviceConfiguration(memory_limit=vram_limit_mb)],
            )
        except RuntimeError:
            pass
        if mixed_precision:
            from tensorflow.keras import mixed_precision as mp  # type: ignore

            mp.set_global_policy("mixed_float16")
            status["mixed_precision"] = True
        tf.config.threading.set_intra_op_parallelism_threads(CPU_INTRAOP_THREADS)
        tf.config.threading.set_inter_op_parallelism_threads(CPU_INTEROP_THREADS)
        status.update({"ok": True, "gpu_available": True, "gpus": [gpu.name for gpu in gpus]})
    except Exception as exc:  # pragma: no cover - environment dependent
        status["error"] = f"{type(exc).__name__}: {exc}"
    return status


def save_runtime_status(path: str | Path, status: RuntimeStatus) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(status), ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def print_hw_summary() -> None:
    print("=" * 72)
    print("stock_rtx4060 runtime profile")
    print("=" * 72)
    print("Target CPU/GPU : i5-13500HX + RTX 4060 Laptop 8GB")
    print(f"Runtime        : {platform.platform()} | Python {sys.version.split()[0]}")
    print(f"Workers        : {CPU_EFFECTIVE_WORKERS} effective / {CPU_LOGICAL_CORES} logical")
    print("XGBoost GPU    : tree_method='hist', device='cuda' when validation passes")
    print("TensorFlow GPU : WSL2 path required for NVIDIA GPU on modern Windows setups")
    print("=" * 72)


def _safe_int(value: str) -> int | None:
    try:
        return int(float(value))
    except ValueError:
        return None
