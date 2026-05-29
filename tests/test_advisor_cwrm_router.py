"""Unit tests for CWRMRouter — disagreement-based routing (AMH Memory W4)."""
from __future__ import annotations

import pytest

from stock_rtx4060.advisors.memory.cwrm_router import CWRMRouter, RoutingDecision


@pytest.fixture()
def router():
    return CWRMRouter(deep_threshold=0.5, conf_min=0.3)


def test_deep_path_when_high_disagreement_and_conf(router):
    """news=0.8, macro=-0.5 → disagreement=1.3 > 0.5 and conf_product=0.6*0.7=0.42 > 0.3."""
    result = router.route(0.8, 0.6, -0.5, 0.7)
    assert result.path == "deep"
    assert result.disagreement == pytest.approx(1.3, abs=1e-3)


def test_shallow_path_when_low_disagreement(router):
    """news=0.2, macro=0.1 → disagreement=0.1 < 0.5."""
    result = router.route(0.2, 0.9, 0.1, 0.9)
    assert result.path == "shallow"


def test_shallow_path_when_high_disagreement_but_low_conf(router):
    """Disagreement > threshold but conf_product too low → shallow."""
    result = router.route(0.8, 0.1, -0.5, 0.1)  # conf_product=0.01 < 0.3
    assert result.path == "shallow"


def test_routing_decision_is_frozen():
    r = RoutingDecision(path="shallow", disagreement=0.1, conf_product=0.5, deep_threshold=0.5, conf_min=0.3)
    with pytest.raises((AttributeError, TypeError)):
        r.path = "deep"  # type: ignore[misc]


def test_cwrm_threshold_boundary_exact(router):
    """Exactly at threshold → not deep (strict >)."""
    result = router.route(0.5, 1.0, 0.0, 1.0)  # disagreement=0.5 == threshold
    assert result.path == "shallow"


def test_cwrm_custom_threshold():
    router_strict = CWRMRouter(deep_threshold=0.2, conf_min=0.1)
    result = router_strict.route(0.5, 0.8, -0.1, 0.8)
    assert result.path == "deep"


def test_route_returns_routing_decision_type(router):
    result = router.route(0.0, 0.5, 0.0, 0.5)
    assert isinstance(result, RoutingDecision)
    assert result.path in ("shallow", "deep")
