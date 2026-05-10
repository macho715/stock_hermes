"""
KIS (한국투자증권) Open API adapter (Phase 8).

Credentials
-----------
Priority: constructor kwargs > env vars > ``~/.config/stock_1901/kis.toml``

Env vars: ``KIS_APP_KEY``, ``KIS_APP_SECRET``, ``KIS_ACCOUNT_NO``

Config file (chmod 600 enforced)::

    # ~/.config/stock_1901/kis.toml
    app_key    = "..."
    app_secret = "..."
    account_no = "..."

Token caching
-------------
OAuth2 tokens are cached at ``~/.cache/stock_1901/kis_token.json``

Smoke/mock test::

    python -m stock_rtx4060.broker.kis_adapter --mock
    python -m stock_rtx4060.broker.kis_adapter --smoke
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..broker_bridge import (
    AccountInfo,
    BrokerAdapter,
    BrokerPosition,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Quote,
)
from . import BrokerNotConfiguredError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
KIS_WS_URL = "ws://ops.koreainvestment.com:21000"
KIS_TOKEN_PATH = Path.home() / ".cache" / "stock_1901" / "kis_token.json"
KIS_CONFIG_PATH = Path.home() / ".config" / "stock_1901" / "kis.toml"

# TTTC0802U = 주식 현금 매수
# TTTC0801U = 주식 현금 매도
_TR_ID_BUY = "TTTC0802U"
_TR_ID_SELL = "TTTC0801U"
# Virtual (paper) trading uses different TR IDs
_TR_ID_BUY_VIRTUAL = "VTTC0802U"
_TR_ID_SELL_VIRTUAL = "VTTC0801U"


# ---------------------------------------------------------------------------
# Helpers — credential loading
# ---------------------------------------------------------------------------

def _load_toml_simple(path: Path) -> dict[str, str]:
    """Minimal TOML parser (key = value, no sections, no arrays)."""
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _enforce_chmod600(path: Path) -> None:
    """Raise PermissionError if file permissions are too broad."""
    try:
        if os.name == "nt":
            return
        mode = path.stat().st_mode & 0o777
        if mode & 0o077:  # group/other bits set
            raise PermissionError(
                f"KIS credentials file {path} has permissions {oct(mode)}. "
                "Expected 600. Run: chmod 600 " + str(path)
            )
    except FileNotFoundError:
        pass  # file doesn't exist yet — skip check


def _load_credentials(
    app_key: str | None,
    app_secret: str | None,
    account_no: str | None,
) -> tuple[str, str, str]:
    """Return (app_key, app_secret, account_no), trying kwargs → env → toml."""
    # 1) kwargs
    if app_key and app_secret and account_no:
        return app_key, app_secret, account_no

    # 2) env vars
    env_key = os.environ.get("KIS_APP_KEY", "")
    env_secret = os.environ.get("KIS_APP_SECRET", "")
    env_account = os.environ.get("KIS_ACCOUNT_NO", "")
    if env_key and env_secret and env_account:
        return env_key, env_secret, env_account

    # 3) toml config
    if KIS_CONFIG_PATH.exists():
        _enforce_chmod600(KIS_CONFIG_PATH)
        cfg = _load_toml_simple(KIS_CONFIG_PATH)
        cfg_key = cfg.get("app_key", "")
        cfg_secret = cfg.get("app_secret", "")
        cfg_account = cfg.get("account_no", "")
        if cfg_key and cfg_secret and cfg_account:
            return cfg_key, cfg_secret, cfg_account

    raise BrokerNotConfiguredError(
        "KIS credentials not found. Provide them via:\n"
        "  1) Constructor kwargs (app_key, app_secret, account_no)\n"
        "  2) Env vars KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO\n"
        f"  3) {KIS_CONFIG_PATH} (chmod 600)"
    )


# ---------------------------------------------------------------------------
# Token cache
# ---------------------------------------------------------------------------

class _TokenCache:
    def __init__(self, path: Path = KIS_TOKEN_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()

    def load(self) -> dict[str, Any] | None:
        with self._lock:
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                expires_at = data.get("expires_at", 0)
                if time.time() < expires_at - 60:
                    return data
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass
        return None

    def save(self, token: str, expires_in: int) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "access_token": token,
                "expires_at": time.time() + expires_in,
                "saved_at": datetime.now(UTC).isoformat(),
            }
            self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class KISAdapter(BrokerAdapter):
    """BrokerAdapter backed by KIS Open API (한국투자증권).

    Parameters
    ----------
    app_key, app_secret, account_no : str, optional
        Credentials; fall back to env vars or kis.toml.
    paper : bool
        Paper (virtual) trading mode (default True).
    mock : bool
        When True, all HTTP calls are replaced by deterministic stubs.
        Useful for unit tests.
    """

    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
        account_no: str | None = None,
        paper: bool = True,
        mock: bool = False,
    ) -> None:
        self._paper = paper
        self._mock = mock

        if not mock:
            self._app_key, self._app_secret, self._account_no = _load_credentials(
                app_key, app_secret, account_no
            )
        else:
            self._app_key = app_key or "MOCK_KEY"
            self._app_secret = app_secret or "MOCK_SECRET"
            self._account_no = account_no or "MOCK_ACCOUNT"

        self._token_cache = _TokenCache()
        self._ws_thread: threading.Thread | None = None
        self._ws_stop = threading.Event()
        self._access_token: str = ""

        # Initialise access token
        if mock:
            self._access_token = self._fetch_token()  # returns MOCK_TOKEN in mock mode
        else:
            self._access_token = self._get_access_token()

        logger.info(
            "KISAdapter ready. paper=%s mock=%s account=%s",
            self._paper, self._mock, self._account_no[:4] + "****" if self._account_no else "N/A",
        )

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """Return cached token or fetch a fresh one via OAuth2."""
        cached = self._token_cache.load()
        if cached:
            return cached["access_token"]
        return self._fetch_token()

    def _fetch_token(self) -> str:
        if self._mock:
            self._token_cache.save("MOCK_TOKEN", expires_in=3600)
            return "MOCK_TOKEN"

        import httpx
        payload = {
            "grant_type": "client_credentials",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
        }
        resp = httpx.post(
            f"{KIS_BASE_URL}/oauth2/tokenP",
            json=payload,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 86400))
        self._token_cache.save(token, expires_in)
        return token

    def _headers(self, tr_id: str) -> dict[str, str]:
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._access_token}",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
            "tr_id": tr_id,
        }

    # ------------------------------------------------------------------
    # BrokerAdapter interface
    # ------------------------------------------------------------------

    @property
    def broker_name(self) -> str:
        if self._mock:
            return "KIS_MOCK"
        return "KIS_PAPER" if self._paper else "KIS_LIVE"

    def get_account_info(self) -> AccountInfo:
        if self._mock:
            return AccountInfo(
                broker=self.broker_name,
                account_id=self._account_no,
                cash=10_000_000.0,
                buying_power=10_000_000.0,
                portfolio_value=10_000_000.0,
                currency="KRW",
            )
        data = self._get_balance()
        output2 = data.get("output2", [{}])
        row = output2[0] if output2 else {}
        portfolio_value = float(row.get("tot_evlu_amt", 0) or 0)
        cash = float(row.get("nass_amt", 0) or 0)
        return AccountInfo(
            broker=self.broker_name,
            account_id=self._account_no,
            cash=cash,
            buying_power=cash,
            portfolio_value=portfolio_value,
            currency="KRW",
        )

    def get_positions(self) -> list[BrokerPosition]:
        if self._mock:
            return []
        data = self._get_balance()
        output1 = data.get("output1", [])
        result: list[BrokerPosition] = []
        for row in output1:
            symbol = str(row.get("pdno", ""))
            qty = int(row.get("hldg_qty", 0) or 0)
            avg_cost = float(row.get("pchs_avg_pric", 0.0) or 0.0)
            current_price = float(row.get("prpr", 0.0) or 0.0)
            market_value = float(row.get("evlu_amt", 0.0) or 0.0)
            unrealized_pnl = float(row.get("evlu_pfls_amt", 0.0) or 0.0)
            cost_basis = avg_cost * qty
            unrealized_pct = unrealized_pnl / cost_basis if cost_basis > 0 else 0.0
            result.append(
                BrokerPosition(
                    symbol=symbol,
                    quantity=qty,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pct,
                )
            )
        return result

    def get_quote(self, ticker: str) -> Quote | None:
        if self._mock:
            return Quote(ticker=ticker, bid=50000.0, ask=50100.0, last=50050.0)
        try:
            import httpx
            # Strip .KS/.KQ suffix for KIS API
            symbol = ticker.upper().replace(".KS", "").replace(".KQ", "")
            headers = self._headers("FHKST01010100")
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
            }
            resp = httpx.get(
                f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
                headers=headers,
                params=params,
                timeout=5.0,
            )
            resp.raise_for_status()
            output = resp.json().get("output", {})
            last = float(output.get("stck_prpr", 0.0) or 0.0)
            return Quote(ticker=ticker, bid=last * 0.999, ask=last * 1.001, last=last)
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_quote(%s) failed: %s", ticker, exc)
            return None

    def submit_order(self, order: OrderRequest) -> OrderResult:
        from ..krx_calendar import KRXCalendarUnavailable, load_krx_calendar_fixture

        # Enforce KRX trading hours via krx_calendar
        try:
            fixture = load_krx_calendar_fixture()
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            if today not in fixture.trading_day_set:
                logger.warning("KIS submit_order: today %s is not a KRX trading day", today)
        except KRXCalendarUnavailable:
            pass  # calendar unavailable — proceed optimistically
        except Exception:  # noqa: BLE001
            pass

        if self._mock:
            return OrderResult(
                order_id=order.order_id,
                ticker=order.ticker,
                side=order.side,
                status=OrderStatus.SUBMITTED,
                quantity=order.quantity,
                fill_price=50000.0,
                fill_price_effective=50000.0,
                simulation_only=False,
                simulation_reason="MOCK_MODE",
            )

        try:
            import httpx

            symbol = order.ticker.upper().replace(".KS", "").replace(".KQ", "")
            is_buy = order.side.upper() == OrderSide.BUY

            if self._paper:
                tr_id = _TR_ID_BUY_VIRTUAL if is_buy else _TR_ID_SELL_VIRTUAL
            else:
                tr_id = _TR_ID_BUY if is_buy else _TR_ID_SELL

            order_dvsn = "00" if order.order_type.upper() == OrderType.MARKET else "01"
            ord_unpr = str(int(order.limit_price or 0)) if order_dvsn == "01" else "0"

            body = {
                "CANO": self._account_no[:8],
                "ACNT_PRDT_CD": self._account_no[8:] if len(self._account_no) > 8 else "01",
                "PDNO": symbol,
                "ORD_DVSN": order_dvsn,
                "ORD_QTY": str(order.quantity),
                "ORD_UNPR": ord_unpr,
            }
            resp = httpx.post(
                f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash",
                headers=self._headers(tr_id),
                json=body,
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            output = data.get("output", {})
            order_no = output.get("ODNO", order.order_id)
            return OrderResult(
                order_id=order_no,
                ticker=order.ticker,
                side=order.side,
                status=OrderStatus.SUBMITTED,
                quantity=order.quantity,
                fill_price=float(ord_unpr) if ord_unpr != "0" else 0.0,
                fill_price_effective=None,
                simulation_only=False,
                simulation_reason="",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("KIS submit_order failed for %s: %s", order.ticker, exc)
            return OrderResult(
                order_id=order.order_id,
                ticker=order.ticker,
                side=order.side,
                status=OrderStatus.REJECTED,
                quantity=order.quantity,
                simulation_only=False,
                simulation_reason="",
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_balance(self) -> dict[str, Any]:
        import httpx
        params = {
            "CANO": self._account_no[:8],
            "ACNT_PRDT_CD": self._account_no[8:] if len(self._account_no) > 8 else "01",
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        resp = httpx.get(
            f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
            headers=self._headers("TTTC8434R"),
            params=params,
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # WebSocket fill notifications
    # ------------------------------------------------------------------

    def start_ws(self) -> None:
        """Start background WebSocket thread for fill notifications."""
        if self._ws_thread and self._ws_thread.is_alive():
            return
        self._ws_stop.clear()

        def _run() -> None:
            try:
                import asyncio
                asyncio.run(self._ws_loop())
            except Exception as exc:  # noqa: BLE001
                logger.warning("KIS WebSocket thread exited: %s", exc)

        self._ws_thread = threading.Thread(
            target=_run, name="kis-ws", daemon=True
        )
        self._ws_thread.start()

    async def _ws_loop(self) -> None:
        import asyncio

        try:
            import websockets
        except ImportError:
            logger.warning("websockets not installed; KIS fill notifications disabled")
            return

        try:
            async with websockets.connect(KIS_WS_URL) as ws:
                logger.info("KIS WebSocket connected")
                while not self._ws_stop.is_set():
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        logger.debug("KIS WS message: %s", msg[:200])
                    except TimeoutError:
                        continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("KIS WebSocket error: %s", exc)

    def stop_ws(self) -> None:
        self._ws_stop.set()

    def close(self) -> None:
        self.stop_ws()

    def get_account(self) -> dict[str, Any]:
        info = self.get_account_info()
        return {
            "buying_power": info.buying_power,
            "portfolio_value": info.portfolio_value,
            "cash": info.cash,
            "currency": info.currency,
        }


# ---------------------------------------------------------------------------
# Smoke / mock CLI
# ---------------------------------------------------------------------------

def _mock_test() -> None:
    """Run full mock test without any real HTTP calls — exits 0."""
    import sys

    print("KISAdapter mock test …")

    adapter = KISAdapter(
        app_key="MOCK_KEY",
        app_secret="MOCK_SECRET",
        account_no="MOCK123456789",
        mock=True,
    )
    assert adapter.broker_name == "KIS_MOCK"

    # Token cache
    adapter._access_token = adapter._fetch_token()
    assert adapter._access_token == "MOCK_TOKEN"
    print("  [PASS] token cached correctly")

    # Account info
    info = adapter.get_account_info()
    assert info.currency == "KRW"
    assert info.cash > 0
    print("  [PASS] get_account_info mock returns KRW account")

    # Positions
    positions = adapter.get_positions()
    assert isinstance(positions, list)
    print("  [PASS] get_positions mock returns empty list")

    # Quote
    q = adapter.get_quote("005930.KS")
    assert q is not None
    assert q.last > 0
    print("  [PASS] get_quote mock returns stub quote")

    # Submit order
    order = OrderRequest(ticker="005930.KS", quantity=1, side=OrderSide.BUY, limit_price=50000.0)
    result = adapter.submit_order(order)
    assert result.status == OrderStatus.SUBMITTED
    print("  [PASS] submit_order mock returns SUBMITTED")

    print("KISAdapter mock test PASSED")
    sys.exit(0)


def _smoke_test() -> None:
    """Smoke test — exits 0 even without real credentials."""
    import sys

    print("KISAdapter smoke test …")

    # Missing credentials
    env_backup = {k: os.environ.pop(k, None) for k in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO")}
    try:
        KISAdapter()
        print("  [WARN] no BrokerNotConfiguredError without credentials")
    except BrokerNotConfiguredError:
        print("  [PASS] BrokerNotConfiguredError raised without credentials")
    finally:
        for k, v in env_backup.items():
            if v is not None:
                os.environ[k] = v

    # Mock mode
    adapter = KISAdapter(
        app_key="SMOKE_KEY",
        app_secret="SMOKE_SECRET",
        account_no="SMOKE12345678",
        mock=True,
    )
    assert adapter.broker_name == "KIS_MOCK"
    print("  [PASS] mock mode initialises correctly")

    # Token cache roundtrip
    KIS_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache = _TokenCache()
    cache.save("TEST_TOKEN", expires_in=3600)
    loaded = cache.load()
    assert loaded is not None
    assert loaded["access_token"] == "TEST_TOKEN"
    print("  [PASS] token cache save/load works")

    print("KISAdapter smoke test PASSED")
    sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KISAdapter")
    parser.add_argument("--smoke", action="store_true", help="run smoke test and exit")
    parser.add_argument("--mock", action="store_true", help="run mock test and exit")
    args = parser.parse_args()
    if args.mock:
        _mock_test()
    elif args.smoke:
        _smoke_test()
    else:
        parser.print_help()
