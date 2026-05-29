"""Pure helpers for applying CMRS output to recommendation candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .strategy import CalibBook, HorizonScore, SizingResult, SizingStrategy, make_sizer

_DOWNGRADEABLE_PREFIXES = ("ELIGIBLE", "ACCUMULATE", "GREEN", "AMBER")


@dataclass
class SizingApplication:
    size_multiplier: float
    new_rank_score: float
    strategy_used: str
    audit_event: dict
    sizing_coverage_status: str = "NO_DATA"
    screening_output_only: bool = True


def apply_sizing(
    candidate: Mapping[str, Any],
    horizon_scores: list[HorizonScore],
    calib_book: CalibBook,
    regime: str,
    regime_probs: dict[str, float],
    *,
    sizer: SizingStrategy | None = None,
    sizing_kind: str = "auto",
    alpha: float = 0.1,
    n_min: int = 30,
    coverage_status: str = "NO_DATA",
) -> SizingApplication:
    sizer = sizer or make_sizer(sizing_kind, n_min=n_min)
    res: SizingResult = sizer.size(horizon_scores, calib_book, regime, regime_probs, alpha)

    verdict = str(candidate.get("verdict", ""))
    base_rank = float(candidate.get("recommendation_rank_score", 0.0))
    if _is_downgradeable(verdict):
        mult = float(res.size_mult)
        new_rank = base_rank * mult
        applied = True
    else:
        mult = 1.0
        new_rank = base_rank
        applied = False

    audit_event = build_audit_event(
        candidate=candidate,
        res=res,
        applied=applied,
        mult=mult,
        base_rank=base_rank,
        new_rank=new_rank,
        regime=regime,
        alpha=alpha,
        coverage_status=coverage_status,
    )
    return SizingApplication(mult, new_rank, res.strategy_used, audit_event, coverage_status)


def snapshot_additive_fields(app: SizingApplication) -> dict[str, Any]:
    return {
        "size_multiplier": round(app.size_multiplier, 6),
        "sizing_strategy_used": app.strategy_used,
        "sizing_coverage_status": app.sizing_coverage_status,
    }


def _is_downgradeable(verdict: str) -> bool:
    value = (verdict or "").upper()
    return any(value.startswith(prefix) for prefix in _DOWNGRADEABLE_PREFIXES)


def build_audit_event(
    *,
    candidate: Mapping[str, Any],
    res: SizingResult,
    applied: bool,
    mult: float,
    base_rank: float,
    new_rank: float,
    regime: str,
    alpha: float,
    coverage_status: str,
) -> dict[str, Any]:
    return {
        "event": "sizing_strategy_selected",
        "ts": datetime.now(timezone.utc).isoformat(),
        "ticker": candidate.get("ticker"),
        "verdict": candidate.get("verdict"),
        "strategy_used": res.strategy_used,
        "applied": applied,
        "size_multiplier": round(mult, 6),
        "rank_score_before": round(base_rank, 6),
        "rank_score_after": round(new_rank, 6),
        "conf": round(res.conf, 6),
        "agreement": round(res.agreement, 6),
        "gate": round(res.gate, 6),
        "regime": regime,
        "coverage_target": res.coverage_target,
        "sizing_coverage_status": coverage_status,
        "sources": res.sources,
        "alpha": alpha,
        "screening_output_only": True,
        "raw_score_unchanged": True,
    }
