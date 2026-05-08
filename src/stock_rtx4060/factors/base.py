"""Factor abstraction shared by all factor implementations.

A ``Factor`` is a deterministic, point-in-time computation that consumes a
panel of OHLCV data (single-ticker DataFrame *or* MultiIndex wide panel) and
returns a Series of values aligned to the panel's date index.  Each factor
declares its lookback (in trading bars) and a category, so the registry can
group them and the validator can enforce minimum data requirements.

Two input shapes are supported by every Factor implementation:

* **Single-ticker** ``pd.DataFrame`` indexed by date with flat OHLCV columns
  (``Open, High, Low, Close, Volume``).  ``compute`` returns a ``pd.Series``
  indexed by date.

* **Wide panel** ``pd.DataFrame`` indexed by date with a ``MultiIndex`` on
  columns of shape ``(ticker, field)``.  ``compute`` returns a ``pd.Series``
  indexed by ``(date, ticker)`` MultiIndex (i.e. stacked across tickers).

The ``as_of`` argument, when supplied, truncates the panel so the factor is
evaluated *as if* the run happened on that date — never peeking forward.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

FactorCategory = Literal[
    "technical",
    "alpha101",
    "alpha158",
    "cross_sectional",
    "discovered",
]

OHLCV_FIELDS = ("Open", "High", "Low", "Close", "Volume")


@dataclass(frozen=True)
class FactorMeta:
    """Static description of a factor.

    Attributes
    ----------
    name:
        Unique factor name; used as a column name and registry key.
    category:
        High-level family (technical, alpha101, alpha158, cross_sectional,
        discovered).
    lookback:
        Minimum number of trading bars required before the factor can emit
        a non-NaN value at any single date.  Used to validate input length.
    description:
        Free-text description / formula citation.
    """

    name: str
    category: FactorCategory
    lookback: int
    description: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise ValueError("FactorMeta.name must be a non-empty string")
        if self.lookback <= 0:
            raise ValueError("FactorMeta.lookback must be positive")
        if self.category not in (
            "technical",
            "alpha101",
            "alpha158",
            "cross_sectional",
            "discovered",
        ):
            raise ValueError(f"FactorMeta.category invalid: {self.category!r}")


def is_panel(panel: pd.DataFrame) -> bool:
    """Return True when ``panel`` is a wide MultiIndex (ticker, field) panel."""
    return isinstance(panel.columns, pd.MultiIndex)


def slice_as_of(panel: pd.DataFrame, as_of: pd.Timestamp | None) -> pd.DataFrame:
    """Truncate a panel at ``as_of`` (inclusive) to enforce point-in-time."""
    if as_of is None:
        return panel
    ts = pd.Timestamp(as_of)
    return panel.loc[panel.index <= ts]


def field_for(panel: pd.DataFrame, field_name: str) -> pd.DataFrame | pd.Series:
    """Project an OHLCV field from either single-ticker or wide-panel input."""
    if is_panel(panel):
        # Cross-section of one OHLCV field across tickers => DataFrame[date, ticker].
        return panel.xs(field_name, axis=1, level=-1)
    if field_name not in panel.columns:
        raise KeyError(f"OHLCV field '{field_name}' missing from panel")
    return panel[field_name]


class Factor(ABC):
    """Abstract Factor.  Subclasses declare ``meta`` and implement ``compute``."""

    meta: FactorMeta

    # Subclasses that are themselves abstract dispatchers (e.g. share ``compute``
    # but require subclasses to fill in ``_single``) should set
    # ``_factor_abstract = True`` on the class to opt out of the meta check.
    _factor_abstract: bool = False

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Skip the meta check when the class is explicitly flagged abstract.
        if cls.__dict__.get("_factor_abstract"):
            return
        abstracts = getattr(cls, "__abstractmethods__", frozenset())
        if abstracts:
            return
        if not isinstance(getattr(cls, "meta", None), FactorMeta):
            raise TypeError(f"Concrete Factor subclass {cls.__name__} must define class attribute `meta: FactorMeta`")

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def lookback(self) -> int:
        return self.meta.lookback

    @abstractmethod
    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        """Compute factor values.

        Returns ``pd.Series`` indexed by date (single-ticker) or by
        ``(date, ticker)`` MultiIndex (wide panel).  No look-ahead: the value
        at index ``t`` may only depend on input rows with index ``<= t``.
        """

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"<{self.__class__.__name__} name={self.meta.name} cat={self.meta.category} lookback={self.meta.lookback}>"
        )
