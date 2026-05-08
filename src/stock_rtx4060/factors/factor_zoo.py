"""Factor registry — central catalogue for built-in and discovered factors.

The registry is a process-wide singleton so other modules can introspect what
factors exist (e.g. validator computes correlation against everything in the
zoo).  Built-in factors register themselves on package import via the
``@register_factor`` decorator.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .base import Factor, FactorCategory


class FactorRegistry:
    """Singleton catalogue of registered ``Factor`` instances."""

    _instance: FactorRegistry | None = None

    def __new__(cls) -> FactorRegistry:
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._factors = {}  # type: ignore[attr-defined]
            cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        # __new__ does the work; this protects __init__ from re-clobbering.
        if not hasattr(self, "_factors"):
            self._factors: dict[str, Factor] = {}

    def register(self, factor: Factor, *, replace: bool = False) -> None:
        """Add ``factor`` to the catalogue."""
        name = factor.name
        if name in self._factors and not replace:
            return
        self._factors[name] = factor

    def get(self, name: str) -> Factor:
        if name not in self._factors:
            raise KeyError(f"Factor '{name}' is not registered")
        return self._factors[name]

    def list(self, category: FactorCategory | None = None) -> list[str]:
        if category is None:
            return sorted(self._factors.keys())
        return sorted(name for name, f in self._factors.items() if f.meta.category == category)

    def all(self) -> list[Factor]:
        return [self._factors[k] for k in sorted(self._factors)]

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._factors

    def __len__(self) -> int:
        return len(self._factors)

    def compute_all(
        self,
        panel: pd.DataFrame,
        as_of: pd.Timestamp | None = None,
        *,
        names: Iterable[str] | None = None,
        category: FactorCategory | None = None,
    ) -> pd.DataFrame:
        """Compute every (or filtered) factor and return a wide DataFrame.

        For single-ticker input, columns are factor names indexed by date.
        For wide-panel input, the result is a wide DataFrame indexed by
        ``(date, ticker)`` with one column per factor.
        """
        if names is None:
            chosen = self.list(category)
        else:
            chosen = [n for n in names if n in self._factors]
        if not chosen:
            return pd.DataFrame(index=panel.index)

        out: dict[str, pd.Series] = {}
        for n in chosen:
            try:
                series = self._factors[n].compute(panel, as_of=as_of)
            except Exception:  # pragma: no cover - per-factor failure must not poison the run
                continue
            out[n] = series
        if not out:
            return pd.DataFrame(index=panel.index)
        return pd.DataFrame(out)


def register_factor(factor: Factor, *, replace: bool = False) -> Factor:
    """Convenience: register a factor instance and return it."""
    FactorRegistry().register(factor, replace=replace)
    return factor
