"""Dynamic factor loader for RD-Agent discovered factors.

Scans ``discovered/{session_id}/*.py`` files, imports them dynamically,
extracts ``Factor`` subclasses that declare ``FactorMeta``, and returns them
as a list of ``(name, FactorClass)`` tuples.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path

# Ensure the package root is on the path so discovered factor modules can be
# imported without needing to install them.
_SRC_ROOT = Path(__file__).parent.parent.parent.parent
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from stock_rtx4060.factors.base import Factor, FactorMeta  # noqa: E402


def _iter_discovered_files(session_id: str) -> Iterator[Path]:
    """Yield ``.py`` files under ``discovered/{session_id}/``."""
    discovered = _SRC_ROOT / "discovered" / session_id
    if not discovered.is_dir():
        return
    for path in sorted(discovered.glob("*.py")):
        if path.name.startswith("_"):
            continue
        yield path


def _load_module_from_path(module_name: str, path: Path) -> object:
    """Import a module directly from a file path, bypassing sys.path."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _is_factor_subclass(obj: object) -> bool:
    """Return True when ``obj`` is a concrete ``Factor`` subclass."""
    return (
        isinstance(obj, type)
        and issubclass(obj, Factor)
        and obj is not Factor
        and not getattr(obj, "_factor_abstract", False)
        and isinstance(getattr(obj, "meta", None), FactorMeta)
    )


def load_discovered_factors(session_id: str) -> list[tuple[str, type[Factor]]]:
    """Load all discovered ``Factor`` subclasses for the given session.

    Parameters
    ----------
    session_id:
        The RD-Agent session identifier.  Corresponds to the sub-folder
        ``discovered/{session_id}/``.

    Returns
    -------
    list[tuple[str, type[Factor]]]
        List of ``(factor_name, FactorClass)`` tuples.  Factors are sorted
        by filename then by class name.
    """
    factors: list[tuple[str, type[Factor]]] = []

    for py_path in _iter_discovered_files(session_id):
        module_name = f"discovered_{session_id}_{py_path.stem}"
        try:
            module = _load_module_from_path(module_name, py_path)
        except Exception:
            # Skip files that fail to import — no exception, no traceback.
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if _is_factor_subclass(attr):
                factors.append((attr.meta.name, attr))

    return factors
