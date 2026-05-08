"""Phase-6 safety contract — the LLM advisor MUST NEVER upgrade a verdict.

This is the canonical safety test for the hybrid advisor blend.  The
deterministic GREEN/AMBER/RED gate emitted by
:func:`stock_rtx4060.recommendation_engine._verdict` is sacred:

* a positive ``advisory_score`` may NOT push AMBER → GREEN
* a positive ``advisory_score`` may NOT push RED   → AMBER
* a negative ``advisory_score`` MAY downgrade GREEN → AMBER (or worse)

If this test ever fails, the engine is broken — the verdict gate has
been compromised and the deployment must be blocked until the safety
floor is restored.
"""

from __future__ import annotations

from stock_rtx4060.recommendation_engine import (
    RecommendationConfig,
    ValidationCheck,
    _verdict,
    _worst_verdict,
)


def _passing_checks() -> list[ValidationCheck]:
    return [
        ValidationCheck("DATA_ROWS", "PASS", ""),
        ValidationCheck("LIQUIDITY", "PASS", ""),
        ValidationCheck("MARKET_REGIME", "PASS", ""),
        ValidationCheck("MODEL_EDGE", "PASS", ""),
        ValidationCheck("OOF_COVERAGE", "PASS", ""),
        ValidationCheck("BACKTEST_SANITY", "PASS", ""),
        ValidationCheck("RISK_PLAN", "PASS", ""),
        ValidationCheck("TRACK_SCORE", "PASS", ""),
        ValidationCheck("AUTOMATION_BOUNDARY", "PASS", ""),
    ]


def _blend(score: float, advisory_score: float, weight: float) -> float:
    blended = score * (1.0 - weight) + (50.0 + advisory_score * 50.0) * weight
    return max(0.0, min(100.0, blended))


def test_amber_stays_amber_under_strong_positive_advisor():
    cfg = RecommendationConfig(advisor_run=True, advisor_blend_weight=0.30)
    checks = _passing_checks()
    deterministic_score = 72.0  # AMBER for Track-S (amber=65, green=75)
    advisory_score, confidence = +1.0, 1.0
    final_score = _blend(deterministic_score, advisory_score, cfg.advisor_blend_weight)

    det_verdict = _verdict("S", deterministic_score, checks, cfg)
    blended_verdict = _verdict("S", final_score, checks, cfg)
    final_verdict, _ = _worst_verdict(det_verdict, blended_verdict)

    assert det_verdict[0] == "AMBER_REVIEW_ONLY"
    # Without the safety contract the blended score (80.4) would upgrade
    # the verdict to GREEN — but _worst_verdict keeps the AMBER decision.
    assert final_verdict == "AMBER_REVIEW_ONLY", (
        f"safety contract breach: AMBER candidate upgraded by LLM "
        f"(score={deterministic_score}, advisory={advisory_score}, conf={confidence}, "
        f"blended={final_score:.2f}, blended_verdict={blended_verdict[0]})"
    )


def test_red_stays_red_under_strong_positive_advisor():
    cfg = RecommendationConfig(advisor_run=True, advisor_blend_weight=0.50)
    checks = _passing_checks()
    deterministic_score = 50.0  # RED for Track-S (amber=65, green=75)
    advisory_score, confidence = +1.0, 1.0
    final_score = _blend(deterministic_score, advisory_score, cfg.advisor_blend_weight)

    det_verdict = _verdict("S", deterministic_score, checks, cfg)
    blended_verdict = _verdict("S", final_score, checks, cfg)
    final_verdict, _ = _worst_verdict(det_verdict, blended_verdict)

    assert det_verdict[0] == "RED_NOT_RECOMMENDED"
    assert final_verdict == "RED_NOT_RECOMMENDED", (
        f"safety contract breach: RED candidate upgraded by LLM "
        f"(score={deterministic_score}, advisory={advisory_score}, conf={confidence}, "
        f"blended={final_score:.2f})"
    )


def test_green_can_be_downgraded_to_amber_by_negative_advisor():
    cfg = RecommendationConfig(advisor_run=True, advisor_blend_weight=0.30)
    checks = _passing_checks()
    deterministic_score = 78.0  # GREEN for Track-S (>= 75)
    advisory_score, confidence = -1.0, 1.0
    final_score = _blend(deterministic_score, advisory_score, cfg.advisor_blend_weight)

    det_verdict = _verdict("S", deterministic_score, checks, cfg)
    blended_verdict = _verdict("S", final_score, checks, cfg)
    final_verdict, _ = _worst_verdict(det_verdict, blended_verdict)

    assert det_verdict[0] == "ELIGIBLE_RECOMMENDATION"
    # A strong contrarian view is allowed to lower the verdict.
    assert final_verdict in {"AMBER_REVIEW_ONLY", "RED_NOT_RECOMMENDED"}
    assert final_score < deterministic_score


def test_green_can_be_downgraded_to_red_by_strong_negative_advisor():
    cfg = RecommendationConfig(advisor_run=True, advisor_blend_weight=0.50)
    checks = _passing_checks()
    deterministic_score = 78.0
    advisory_score, confidence = -1.0, 1.0
    final_score = _blend(deterministic_score, advisory_score, cfg.advisor_blend_weight)

    det_verdict = _verdict("S", deterministic_score, checks, cfg)
    blended_verdict = _verdict("S", final_score, checks, cfg)
    final_verdict, _ = _worst_verdict(det_verdict, blended_verdict)
    assert final_verdict == "RED_NOT_RECOMMENDED"


def test_amber_long_track_stays_amber_under_strong_positive_advisor():
    cfg = RecommendationConfig(advisor_run=True, advisor_blend_weight=0.30)
    checks = _passing_checks()
    deterministic_score = 75.0  # AMBER for Track-L (amber=70, green=80)
    advisory_score = +1.0
    final_score = _blend(deterministic_score, advisory_score, cfg.advisor_blend_weight)

    det_verdict = _verdict("L", deterministic_score, checks, cfg)
    blended_verdict = _verdict("L", final_score, checks, cfg)
    final_verdict, _ = _worst_verdict(det_verdict, blended_verdict)

    assert det_verdict[0] == "AMBER_WATCHLIST"
    assert final_verdict == "AMBER_WATCHLIST"


def test_default_config_has_advisor_disabled():
    cfg = RecommendationConfig()
    assert cfg.advisor_run is False
    assert cfg.advisor_blend_weight == 0.0
