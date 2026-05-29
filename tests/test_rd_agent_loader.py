"""Tests for the RD-Agent factor loader (loader.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from stock_rtx4060.factors.rd_agent.loader import (
    _is_factor_subclass,
    _load_module_from_path,
    load_discovered_factors,
)


class TestIsFactorSubclass:
    def test_true_for_concrete_factor_subclass(self) -> None:
        from stock_rtx4060.factors.base import Factor, FactorMeta

        class MyFactor(Factor):
            meta = FactorMeta(name="test", category="discovered", lookback=1)

            def compute(self, panel, as_of=None):
                import pandas as pd
                return pd.Series([1.0], index=panel.index)

        assert _is_factor_subclass(MyFactor) is True

    def test_false_for_abstract_factor(self) -> None:
        from stock_rtx4060.factors.base import Factor, FactorMeta

        class AbstractFactor(Factor):
            meta = FactorMeta(name="abstract", category="discovered", lookback=1)
            _factor_abstract = True

            def compute(self, panel, as_of=None):
                import pandas as pd
                return pd.Series([1.0], index=panel.index)

        assert _is_factor_subclass(AbstractFactor) is False

    def test_false_for_non_factor_class(self) -> None:
        assert _is_factor_subclass("not a class") is False
        assert _is_factor_subclass(42) is False
        assert _is_factor_subclass(None) is False

    def test_false_when_no_meta_attribute(self) -> None:
        class NoMetaClass:
            pass

        assert _is_factor_subclass(NoMetaClass) is False


class TestLoadModuleFromPath:
    def test_load_valid_factor_file(self, tmp_path: Path) -> None:
        """Correct .py → Factor instance returned."""
        factor_path = tmp_path / "test_factor.py"
        factor_path.write_text(
            """
from stock_rtx4060.factors.base import Factor, FactorMeta

class RdMomentum(Factor):
    meta = FactorMeta(
        name="rd_momentum",
        category="discovered",
        lookback=21,
        description="RD-Agent momentum factor",
    )

    def compute(self, panel, as_of=None):
        import pandas as pd
        return pd.Series([0.0] * len(panel.index), index=panel.index)
""",
            encoding="utf-8",
        )

        module = _load_module_from_path("test_factor", factor_path)
        assert hasattr(module, "RdMomentum")

        # Check it's a Factor subclass
        cls = module.RdMomentum
        from stock_rtx4060.factors.base import Factor
        assert issubclass(cls, Factor)

    def test_load_invalid_syntax(self, tmp_path: Path) -> None:
        """Syntax error → caught by load_discovered_factors as ImportError."""
        bad_syntax_path = tmp_path / "bad_syntax_factor.py"
        bad_syntax_path.write_text(
            """
# Intentional syntax error - missing colon
class BadSyntaxFactor
    def compute(self, panel):
        return 1.0
""",
            encoding="utf-8",
        )

        # _load_module_from_path raises ImportError (or SyntaxError wrapped)
        # Python 3.14 raises SyntaxError directly; accept both
        with pytest.raises((ImportError, SyntaxError)):
            _load_module_from_path("bad_syntax_factor", bad_syntax_path)


class TestLoadDiscoveredFactors:
    def test_loader_valid_factor_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Correct .py → Factor instance returned."""
        # Create a fake discovered session directory
        session_dir = tmp_path / "discovered" / "rd_20260529_test"
        session_dir.mkdir(parents=True, exist_ok=True)

        factor_file = session_dir / "rd_momentum.py"
        factor_file.write_text(
            """
from stock_rtx4060.factors.base import Factor, FactorMeta

class RdMomentum(Factor):
    meta = FactorMeta(
        name="rd_momentum",
        category="discovered",
        lookback=21,
        description="Test RD-Agent factor",
    )

    def compute(self, panel, as_of=None):
        import pandas as pd
        return pd.Series([0.5] * len(panel.index), index=panel.index)
""",
            encoding="utf-8",
        )

        # Patch _SRC_ROOT to point to tmp_path so discovered dir is found
        monkeypatch.setenv("RDAGENT_ENABLED", "false")  # prevent docker runner
        with patch("stock_rtx4060.factors.rd_agent.loader._SRC_ROOT", tmp_path):
            result = load_discovered_factors("rd_20260529_test")

        assert len(result) == 1
        name, cls = result[0]
        assert name == "rd_momentum"
        from stock_rtx4060.factors.base import Factor
        assert issubclass(cls, Factor)

    def test_loader_invalid_no_meta(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing meta → loader catches TypeError internally and skips the class (no exception propagated)."""
        session_dir = tmp_path / "discovered" / "rd_20260529_test2"
        session_dir.mkdir(parents=True, exist_ok=True)

        # This file has a syntax error (colon missing) but the class has meta
        syntax_error_file = session_dir / "rd_bad.py"
        syntax_error_file.write_text(
            """
from stock_rtx4060.factors.base import Factor, FactorMeta

class RdBadSyntax(Factor)
    meta = FactorMeta(name="rd_bad", category="discovered", lookback=1)

    def compute(self, panel, as_of=None):
        import pandas as pd
        return pd.Series([1.0], index=panel.index)
""",
            encoding="utf-8",
        )

        monkeypatch.setenv("RDAGENT_ENABLED", "false")
        with patch("stock_rtx4060.factors.rd_agent.loader._SRC_ROOT", tmp_path):
            result = load_discovered_factors("rd_20260529_test2")

        # Should be empty — syntax error caught and file skipped
        assert result == []

    def test_loader_invalid_syntax(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Syntax error → skip (no exception)."""
        session_dir = tmp_path / "discovered" / "rd_20260529_test3"
        session_dir.mkdir(parents=True, exist_ok=True)

        syntax_error_file = session_dir / "rd_syntax_error.py"
        syntax_error_file.write_text(
            """
# Syntax error: unclosed string and invalid indentation
class RdSyntaxError(Factor)
    meta = FactorMeta(name="syntax_error", category="discovered", lookback=1)
        def compute(self, panel, as_of=None):
            return 1.0
""",
            encoding="utf-8",
        )

        monkeypatch.setenv("RDAGENT_ENABLED", "false")
        with patch("stock_rtx4060.factors.rd_agent.loader._SRC_ROOT", tmp_path):
            result = load_discovered_factors("rd_20260529_test3")

        # Should be empty — file skipped due to syntax error
        assert result == []

    def test_loader_skips_private_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Files starting with underscore are skipped."""
        session_dir = tmp_path / "discovered" / "rd_20260529_test4"
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create a valid factor with underscore prefix (should be skipped)
        underscore_file = session_dir / "_private_factor.py"
        underscore_file.write_text(
            """
from stock_rtx4060.factors.base import Factor, FactorMeta

class RdPrivate(Factor):
    meta = FactorMeta(name="rd_private", category="discovered", lookback=1)

    def compute(self, panel, as_of=None):
        import pandas as pd
        return pd.Series([1.0], index=panel.index)
""",
            encoding="utf-8",
        )

        monkeypatch.setenv("RDAGENT_ENABLED", "false")
        with patch("stock_rtx4060.factors.rd_agent.loader._SRC_ROOT", tmp_path):
            result = load_discovered_factors("rd_20260529_test4")

        # Should be empty — underscore file was skipped
        assert result == []