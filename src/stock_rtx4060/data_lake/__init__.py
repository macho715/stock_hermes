"""PIT-correct (point-in-time) data lake for stock_rtx4060.

Two backends are exposed via the ``DATA_LAKE_BACKEND`` env var:
- ``duckdb`` (default): hive-partitioned Parquet under ``./data_lake/parquet``
- ``arctic`` (optional): ArcticDB LMDB/S3 — install ``arcticdb`` to enable.

Bitemporal model: every row carries ``_ingested_at``. Queries through
``pit_resolver.read(..., as_of=...)`` return rows known at or before ``as_of``.

DuckLake 1.0 (opt-in):
- Set ``DUCKLAKE_ENABLED=true`` to activate the DuckLake metadata layer.
- Default is ``false``; the standard Parquet path is always used when disabled.
- Requires DuckDB >=1.5.3 (``duckdb>=1.5.3`` in requirements.in).
"""
import os as _os

# W2-B2: DuckLake 1.0 feature flag — off by default for safe rollout.
DUCKLAKE_ENABLED: bool = _os.environ.get("DUCKLAKE_ENABLED", "false").lower() in ("1", "true", "yes")

from .audit_provenance import log_pit_read
from .pit_resolver import read as read_pit
from .store import DuckDBStore, PITStore, get_default_store

__all__ = [
    "PITStore",
    "DuckDBStore",
    "get_default_store",
    "read_pit",
    "log_pit_read",
]
