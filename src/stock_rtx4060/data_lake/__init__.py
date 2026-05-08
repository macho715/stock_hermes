"""PIT-correct (point-in-time) data lake for stock_rtx4060.

Two backends are exposed via the ``DATA_LAKE_BACKEND`` env var:
- ``duckdb`` (default): hive-partitioned Parquet under ``./data_lake/parquet``
- ``arctic`` (optional): ArcticDB LMDB/S3 — install ``arcticdb`` to enable.

Bitemporal model: every row carries ``_ingested_at``. Queries through
``pit_resolver.read(..., as_of=...)`` return rows known at or before ``as_of``.
"""
from .store import PITStore, get_default_store, DuckDBStore
from .pit_resolver import read as read_pit
from .audit_provenance import log_pit_read

__all__ = [
    "PITStore",
    "DuckDBStore",
    "get_default_store",
    "read_pit",
    "log_pit_read",
]
