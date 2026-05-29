"""Factor library — technical, alpha101, cross-sectional and discovered factors.

Importing this package auto-registers all built-in factors with the global
``FactorRegistry`` singleton.  After import you can introspect:

>>> from stock_rtx4060.factors import FactorRegistry
>>> reg = FactorRegistry()
>>> reg.list()                      # all factor names
>>> reg.list(category="alpha101")   # filter by category
>>> reg.get("RSI14").compute(df)    # compute one factor

Use :func:`stock_rtx4060.feature_engine.build_features` to combine the
existing technical-indicator pipeline with arbitrary factors from the
registry — see its docstring for details.
"""

from __future__ import annotations

from . import alpha101, cross_sectional, technical
from .alpha101 import ALPHA101_FACTORS
from .analytics import (
    compute_ic,
    compute_ir,
    factor_decay,
    quintile_pnl,
    rank_autocorr,
)
from .base import OHLCV_FIELDS, Factor, FactorMeta, SourceType, is_panel, slice_as_of
from .cross_sectional import CROSS_SECTIONAL_FACTORS, attach_fundamentals
from .factor_zoo import FactorRegistry, register_factor
from .technical import TECHNICAL_FACTORS

# Auto-register all built-in factors at import time.  Re-import is safe (no-op
# when the name already exists in the registry).
_registry = FactorRegistry()
for _f in (*TECHNICAL_FACTORS, *ALPHA101_FACTORS, *CROSS_SECTIONAL_FACTORS):
    _registry.register(_f)

__all__ = [
    "Factor",
    "FactorMeta",
    "FactorRegistry",
    "SourceType",
    "register_factor",
    "OHLCV_FIELDS",
    "is_panel",
    "slice_as_of",
    "TECHNICAL_FACTORS",
    "ALPHA101_FACTORS",
    "CROSS_SECTIONAL_FACTORS",
    "attach_fundamentals",
    "compute_ic",
    "compute_ir",
    "factor_decay",
    "quintile_pnl",
    "rank_autocorr",
    "alpha101",
    "technical",
    "cross_sectional",
]
