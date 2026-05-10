"""Benchmark harness for feature generation, model fit, and backtest."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .backtester import Backtester
from .ensemble_model import EnsemblePredictor, ModelConfig
from .feature_engine import TechnicalIndicators, make_synthetic_ohlcv
from .hw_profile import runtime_status
from .reports import now_stamp


@dataclass(frozen=True)
class BenchmarkItem:
    name: str
    seconds: float
    rows: int
    backend: str
    status: str = "ok"
    notes: str = ""


@dataclass(frozen=True)
class BenchmarkReport:
    rows: int
    repeats: int
    runtime_gate: str
    items: list[BenchmarkItem]
    status: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "repeats": self.repeats,
            "runtime_gate": self.runtime_gate,
            "items": [asdict(item) for item in self.items],
            "status": self.status,
        }


def run_benchmark(rows: int = 1500, repeats: int = 3, include_gpu: bool = False, include_lstm: bool = False, lite: bool = True) -> BenchmarkReport:
    rows = max(300, int(rows))
    repeats = max(1, int(repeats))
    status = runtime_status(include_tensorflow=include_lstm, include_xgboost=include_gpu)
    items: list[BenchmarkItem] = []
    df = make_synthetic_ohlcv(rows)

    feature_frame_holder: dict[str, pd.DataFrame] = {}

    def build_features() -> None:
        feature_frame_holder["frame"] = TechnicalIndicators(df).build_all(horizon=5)

    feature_seconds = _best_of(repeats, build_features)
    feature_frame = feature_frame_holder["frame"]
    items.append(BenchmarkItem("feature_engine.build_all", feature_seconds, len(feature_frame), "pandas/numpy"))

    def train_cpu() -> None:
        model = EnsemblePredictor(ModelConfig(n_splits=3, prefer_gpu=False, use_xgboost=False, lite=lite, use_lstm=False))
        model.fit(feature_frame)
        feature_frame_holder["cpu_model"] = model

    cpu_seconds = _best_of(1 if rows > 3000 else repeats, train_cpu)
    cpu_model = feature_frame_holder["cpu_model"]
    items.append(BenchmarkItem("walk_forward_train", cpu_seconds, len(feature_frame), cpu_model.xgb.backend))

    if include_gpu:
        def train_xgboost_cpu() -> None:
            model = EnsemblePredictor(ModelConfig(n_splits=3, prefer_gpu=False, use_xgboost=True, lite=lite, use_lstm=False))
            model.fit(feature_frame)
            feature_frame_holder["xgboost_cpu_model"] = model

        xgboost_cpu_seconds = _best_of(1 if rows > 3000 else repeats, train_xgboost_cpu)
        xgboost_cpu_model = feature_frame_holder["xgboost_cpu_model"]
        items.append(
            BenchmarkItem(
                "walk_forward_train_xgboost_cpu",
                xgboost_cpu_seconds,
                len(feature_frame),
                xgboost_cpu_model.xgb.backend,
                notes="Same XGBoost model settings as GPU path with device='cpu'.",
            )
        )

        def train_gpu() -> None:
            model = EnsemblePredictor(ModelConfig(n_splits=3, prefer_gpu=True, use_xgboost=True, lite=lite, use_lstm=False))
            model.fit(feature_frame)
            feature_frame_holder["gpu_model"] = model

        gpu_seconds = _best_of(1 if rows > 3000 else repeats, train_gpu)
        gpu_model = feature_frame_holder["gpu_model"]
        items.append(BenchmarkItem("walk_forward_train_gpu_requested", gpu_seconds, len(feature_frame), gpu_model.xgb.backend, notes="Falls back if CUDA/XGBoost GPU is unavailable."))

    if include_lstm:
        def train_lstm() -> None:
            model = EnsemblePredictor(ModelConfig(n_splits=2, prefer_gpu=include_gpu, use_xgboost=include_gpu, lite=True, use_lstm=True))
            model.fit(feature_frame)
            feature_frame_holder["lstm_model"] = model

        try:
            lstm_seconds = _best_of(1, train_lstm)
            lstm_model = feature_frame_holder["lstm_model"]
            items.append(BenchmarkItem("lstm_optional_train", lstm_seconds, len(feature_frame), "tensorflow-lstm" if lstm_model.lstm else "disabled/fallback"))
        except Exception as exc:
            items.append(BenchmarkItem("lstm_optional_train", 0.0, len(feature_frame), "tensorflow", status="failed", notes=f"{type(exc).__name__}: {exc}"))

    model = feature_frame_holder["cpu_model"]
    signal = pd.Series(model.predict_proba(feature_frame.drop(columns=["target_direction", "target_return"])), index=feature_frame.index)
    prices = df["Close"].reindex(feature_frame.index).ffill()

    def run_bt() -> None:
        Backtester().run(prices, signal)

    bt_seconds = _best_of(repeats, run_bt)
    items.append(BenchmarkItem("backtester.run", bt_seconds, len(prices), "python/pandas"))
    return BenchmarkReport(rows=rows, repeats=repeats, runtime_gate=status.gate, items=items, status=asdict(status))


def write_benchmark_report(report: BenchmarkReport, output_dir: str | Path = "reports") -> tuple[Path, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()
    json_path = out / f"benchmark_{stamp}.json"
    md_path = out / f"benchmark_{stamp}.md"
    payload = report.to_dict()
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    df = pd.DataFrame(payload["items"])
    lines = [
        "# Benchmark Report",
        "",
        f"Rows requested: {report.rows}",
        f"Repeats: {report.repeats}",
        f"Runtime Gate: **{report.runtime_gate}**",
        "",
        "## Timings",
        "",
        df.to_markdown(index=False),
        "",
        "## Notes",
        "",
        "- GPU rows are only valid when backend reports `xgboost-cuda` or TensorFlow lists a GPU.",
        "- In CPU-only environments this harness intentionally records fallback behavior instead of failing.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def _best_of(repeats: int, func: Callable[[], None]) -> float:
    timings = []
    for _ in range(repeats):
        start = time.perf_counter()
        func()
        timings.append(time.perf_counter() - start)
    return round(min(timings), 6)
