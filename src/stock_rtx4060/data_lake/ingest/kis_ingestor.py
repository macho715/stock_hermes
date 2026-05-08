"""한국투자증권 KIS Open API → PIT lake ingestor (REST historical bars).

Endpoint: ``/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice``
Auth: OAuth2 token at ``/oauth2/tokenP``, cached in ``~/.cache/stock_1901/kis_token.json``.
Credentials read from ``~/.config/stock_1901/kis.toml`` (chmod 600 enforced).

This module is import-light (no heavy deps) so the package loads without
network. Real network calls happen only when ``ingest_kis`` is invoked.
"""
from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..audit_provenance import log_pit_write
from ..store import PITStore, get_default_store

KIS_BASE_URL = os.environ.get("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_TOKEN_CACHE = Path.home() / ".cache" / "stock_1901" / "kis_token.json"
KIS_CREDENTIAL_PATH = Path.home() / ".config" / "stock_1901" / "kis.toml"


@dataclass
class KISCredentials:
    appkey: str
    appsecret: str
    account_number: str = ""
    paper: bool = True


def _load_credentials(path: Path | None = None) -> KISCredentials:
    target = path or KIS_CREDENTIAL_PATH
    if not target.exists():
        raise FileNotFoundError(
            f"KIS credential file not found: {target}. Create it with appkey/appsecret/account_number."
        )
    mode = target.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise PermissionError(
            f"KIS credential file {target} must be chmod 600 (owner-only)."
        )
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    data = tomllib.loads(target.read_text(encoding="utf-8"))
    return KISCredentials(
        appkey=str(data["appkey"]),
        appsecret=str(data["appsecret"]),
        account_number=str(data.get("account_number", "")),
        paper=bool(data.get("paper", True)),
    )


def _fetch_token(creds: KISCredentials) -> str:
    import httpx

    KIS_TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    if KIS_TOKEN_CACHE.exists():
        cached = json.loads(KIS_TOKEN_CACHE.read_text())
        if cached.get("expires_at", 0) > time.time() + 60:
            return str(cached["access_token"])
    resp = httpx.post(
        f"{KIS_BASE_URL}/oauth2/tokenP",
        json={"grant_type": "client_credentials", "appkey": creds.appkey, "appsecret": creds.appsecret},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    cached = {
        "access_token": payload["access_token"],
        "expires_at": time.time() + int(payload.get("expires_in", 86400)) - 300,
    }
    KIS_TOKEN_CACHE.write_text(json.dumps(cached))
    KIS_TOKEN_CACHE.chmod(0o600)
    return str(payload["access_token"])


def _fetch_daily_bars(ticker: str, start: str, end: str, *, creds: KISCredentials, token: str) -> pd.DataFrame:
    import httpx

    headers = {
        "authorization": f"Bearer {token}",
        "appkey": creds.appkey,
        "appsecret": creds.appsecret,
        "tr_id": "FHKST03010100",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": ticker,
        "FID_INPUT_DATE_1": start,
        "FID_INPUT_DATE_2": end,
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "0",
    }
    resp = httpx.get(
        f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        params=params,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json().get("output2", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["index"] = pd.to_datetime(df["stck_bsop_date"], format="%Y%m%d")
    df = df.set_index("index")
    df = df.rename(
        columns={
            "stck_oprc": "Open",
            "stck_hgpr": "High",
            "stck_lwpr": "Low",
            "stck_clpr": "Close",
            "acml_vol": "Volume",
        }
    )
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna().sort_index()


def ingest_kis(
    ticker: str,
    *,
    start: str,
    end: str,
    store: PITStore | None = None,
    creds_path: Path | None = None,
) -> int:
    """Ingest KRX daily bars for ``ticker`` (6-digit KRX code) into PIT lake.

    Real network call; requires ``~/.config/stock_1901/kis.toml`` with the
    appkey/appsecret obtained from KIS Developers.
    """
    creds = _load_credentials(creds_path)
    token = _fetch_token(creds)
    df = _fetch_daily_bars(ticker, start, end, creds=creds, token=token)
    if df.empty:
        return 0
    store = store or get_default_store()
    written = store.write(ticker, df, source="kis")
    log_pit_write(ticker=ticker, source="kis", rows=written, backend=type(store).__name__)
    return written
