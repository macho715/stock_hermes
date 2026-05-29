"""Tests for FactorMeta additive field extension (base.py)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from stock_rtx4060.factors.base import FactorMeta


class TestFactorMetaAdditiveFields:
    def test_factor_meta_additive_fields_backward_compatible(self) -> None:
        """Existing FactorMeta constructor works without new fields (backward compatible)."""
        # Old-style usage: only required fields
        old_meta = FactorMeta(
            name="legacy_momentum",
            category="technical",
            lookback=20,
        )

        assert old_meta.name == "legacy_momentum"
        assert old_meta.category == "technical"
        assert old_meta.lookback == 20
        # New optional fields should have defaults
        assert old_meta.source == "builtin"
        assert old_meta.discovery_session_id == ""
        assert old_meta.discovery_date == ""
        assert old_meta.budget_usd == 0.0
        import math
        assert math.isnan(old_meta.ic_at_discovery)

    def test_factor_meta_new_fields(self) -> None:
        """New RD-Agent fields can be set without breaking existing usage."""
        new_meta = FactorMeta(
            name="rd_momentum",
            category="discovered",
            lookback=21,
            description="RD-Agent discovered momentum factor",
            tags=("rd_agent", "momentum", "test"),
            source="rd_agent",
            discovery_session_id="rd_20260529_abc123",
            discovery_date="2026-05-29",
            budget_usd=3.42,
            ic_at_discovery=0.052,
        )

        assert new_meta.name == "rd_momentum"
        assert new_meta.category == "discovered"
        assert new_meta.source == "rd_agent"
        assert new_meta.discovery_session_id == "rd_20260529_abc123"
        assert new_meta.discovery_date == "2026-05-29"
        assert new_meta.budget_usd == pytest.approx(3.42)
        assert new_meta.ic_at_discovery == pytest.approx(0.052)

    def test_factor_meta_source_literal_values(self) -> None:
        """source field only accepts valid SourceType literals."""
        valid_sources = ["builtin", "rd_agent", "manual"]
        for src in valid_sources:
            meta = FactorMeta(name="test", category="technical", lookback=1, source=src)
            assert meta.source == src

        with pytest.raises(ValueError, match="source invalid"):
            FactorMeta(name="test", category="technical", lookback=1, source="invalid")

    def test_factor_meta_category_literal_values(self) -> None:
        """category field only accepts valid FactorCategory literals."""
        valid_categories = ["technical", "alpha101", "alpha158", "cross_sectional", "discovered"]
        for cat in valid_categories:
            meta = FactorMeta(name="test", category=cat, lookback=1)
            assert meta.category == cat

        with pytest.raises(ValueError, match="category invalid"):
            FactorMeta(name="test", category="invalid_category", lookback=1)

    def test_factor_meta_name_validation(self) -> None:
        """Empty name raises ValueError."""
        with pytest.raises(ValueError, match="name must be"):
            FactorMeta(name="", category="technical", lookback=1)

        with pytest.raises(ValueError, match="name must be"):
            FactorMeta(name=None, category="technical", lookback=1)  # type: ignore[arg-type]

    def test_factor_meta_lookback_validation(self) -> None:
        """lookback must be positive."""
        with pytest.raises(ValueError, match="lookback must be positive"):
            FactorMeta(name="test", category="technical", lookback=0)

        with pytest.raises(ValueError, match="lookback must be positive"):
            FactorMeta(name="test", category="technical", lookback=-1)

    def test_factor_meta_tags_default_empty_tuple(self) -> None:
        """tags defaults to empty tuple, not list (immutable)."""
        meta = FactorMeta(name="test", category="technical", lookback=1)
        assert meta.tags == ()
        assert isinstance(meta.tags, tuple)

    def test_factor_meta_immutable(self) -> None:
        """FactorMeta is frozen — fields cannot be changed after construction."""
        meta = FactorMeta(name="test", category="technical", lookback=1)

        with pytest.raises(FrozenInstanceError):
            meta.name = "changed"  # type: ignore[attr-defined]

    def test_factor_meta_with_optional_fields_all_set(self) -> None:
        """All optional fields set together — no conflicts."""
        meta = FactorMeta(
            name="full_rd_agent_factor",
            category="discovered",
            lookback=21,
            description="Complete factor with all provenance fields",
            tags=("momentum", "rd_agent"),
            source="rd_agent",
            discovery_session_id="rd_20260529_xyz789",
            discovery_date="2026-05-29",
            budget_usd=5.00,
            ic_at_discovery=0.041,
        )

        assert meta.name == "full_rd_agent_factor"
        assert meta.category == "discovered"
        assert meta.lookback == 21
        assert meta.description == "Complete factor with all provenance fields"
        assert meta.tags == ("momentum", "rd_agent")
        assert meta.source == "rd_agent"
        assert meta.discovery_session_id == "rd_20260529_xyz789"
        assert meta.discovery_date == "2026-05-29"
        assert meta.budget_usd == pytest.approx(5.0)
        assert meta.ic_at_discovery == pytest.approx(0.041)


class TestFactorMetaFrost:
    def test_factor_meta_repr(self) -> None:
        """FactorMeta repr includes key fields."""
        meta = FactorMeta(name="repr_test", category="technical", lookback=5)
        r = repr(meta)
        assert "repr_test" in r
        assert "technical" in r
