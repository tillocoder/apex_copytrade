import hmac
import hashlib
import time
import json
import os
import asyncio
import requests
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlencode

from .config import DEFAULT_CONFIG, load_env_file

async def run_in_thread(func, *args, **kwargs):
    import functools
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

class BinanceFuturesConnector:
    """
    Institutional Binance Futures Connector (USD(S)-M Futures):
    - Full HMAC-SHA256 signature authentication
    - Server time drift synchronization
    - Dynamic .env credential hot-reloading (Secret NEVER exposed to frontend)
    - Reconciles account, position risk, and open orders
    - Dual-side / One-way mode enforcement
    - 100x leverage enforcement
    - User Data Stream listenKey generation & keepalive
    """
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")
        self.base_url = DEFAULT_CONFIG.rest_base_url
        self.time_offset_ms = 0
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ApexQuant/4.2 (Binance Futures Production Engine)"
        })
        if self.api_key:
            self.session.headers.update({"X-MBX-APIKEY": self.api_key})
            
        self.exchange_filters = {
            "tickSize": DEFAULT_CONFIG.tick_size,
            "stepSize": DEFAULT_CONFIG.step_size,
            "minQty": DEFAULT_CONFIG.min_qty,
            "minNotional": DEFAULT_CONFIG.min_notional
        }
        self.max_allowed_leverage = 100
        self.leverage_verified = False
        self.position_mode_verified = False
        self.listen_key: Optional[str] = None

    def reload_credentials_from_env(self) -> bool:
        """Dynamically re-reads .env to capture newly added API keys without restart."""
        load_env_file()
        new_key = os.getenv("BINANCE_API_KEY", "").strip()
        new_secret = os.getenv("BINANCE_API_SECRET", "").strip()
        if new_key and new_secret:
            if new_key != self.api_key or new_secret != self.api_secret:
                self.api_key = new_key
                self.api_secret = new_secret
                self.session.headers.update({"X-MBX-APIKEY": self.api_key})
                self.leverage_verified = False
                self.position_mode_verified = False
                return True
        return False

    def update_keys(self, api_key: str, api_secret: str):
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})
        self.leverage_verified = False
        self.position_mode_verified = False

    def has_credentials(self) -> bool:
        self.reload_credentials_from_env()
        return bool(self.api_key and self.api_secret)

    def get_public_connection_status(self) -> Dict[str, Any]:
        """Returns safe connection metadata. Secret key is NEVER returned."""
        self.reload_credentials_from_env()
        has_creds = bool(self.api_key and self.api_secret)
        preview = None
        if self.api_key and len(self.api_key) >= 10:
            preview = f"{self.api_key[:6]}...{self.api_key[-4:]}"
        return {
            "hasCredentials": has_creds,
            "keyPreview": preview,
            "leverageVerified": self.leverage_verified,
            "positionModeVerified": self.position_mode_verified,
            "timeOffsetMs": self.time_offset_ms
        }

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = int(time.time() * 1000) + self.time_offset_ms
        params["recvWindow"] = 5000
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def sync_server_time(self) -> int:
        try:
            r = self.session.get(f"{self.base_url}/fapi/v1/time", timeout=5)
            if r.status_code == 200:
                server_time = r.json().get("serverTime", int(time.time() * 1000))
                local_time = int(time.time() * 1000)
                self.time_offset_ms = server_time - local_time
                return self.time_offset_ms
        except Exception as e:
            print(f"[BINANCE_TIME_SYNC_ERR] {e}")
        return 0

    async def sync_server_time_async(self):
        return await run_in_thread(self.sync_server_time)

    def fetch_exchange_info(self) -> Dict[str, Any]:
        """Fetches tick size, step size, minQty, and minNotional for ETHUSDT."""
        try:
            r = self.session.get(f"{self.base_url}/fapi/v1/exchangeInfo", timeout=8)
            if r.status_code == 200:
                data = r.json()
                symbols = data.get("symbols", [])
                for s in symbols:
                    if s.get("symbol") == DEFAULT_CONFIG.symbol:
                        filters = s.get("filters", [])
                        for f in filters:
                            ft = f.get("filterType")
                            if ft == "PRICE_FILTER":
                                self.exchange_filters["tickSize"] = float(f.get("tickSize", 0.01))
                            elif ft == "LOT_SIZE":
                                self.exchange_filters["stepSize"] = float(f.get("stepSize", 0.001))
                                self.exchange_filters["minQty"] = float(f.get("minQty", 0.001))
                            elif ft in ("MIN_NOTIONAL", "NOTIONAL"):
                                self.exchange_filters["minNotional"] = float(f.get("notional", f.get("minNotional", 20.0)))
                        break
        except Exception as e:
            print(f"[BINANCE_EXCHANGE_INFO_ERR] {e}")
        return self.exchange_filters

    async def fetch_exchange_info_async(self):
        return await run_in_thread(self.fetch_exchange_info)

    def verify_and_set_position_mode(self, dual_side: bool = False) -> Tuple[bool, str]:
        """Enforces One-Way Mode (dualSidePosition=false)."""
        if not self.has_credentials():
            return False, "Missing API credentials"
        try:
            params = self._sign({"dualSidePosition": "true" if dual_side else "false"})
            r = self.session.post(f"{self.base_url}/fapi/v1/positionSide/dual", data=params, timeout=5)
            res = r.json()
            # code -4059 means "No need to change position side" -> already in correct mode
            if r.status_code == 200 or res.get("code") == -4059:
                self.position_mode_verified = True
                return True, "One-way position mode confirmed"
            return False, res.get("msg", "Failed to set position mode")
        except Exception as e:
            return False, str(e)

    async def verify_and_set_position_mode_async(self, dual_side: bool = False):
        return await run_in_thread(self.verify_and_set_position_mode, dual_side)

    def verify_and_set_leverage(self, leverage: int = 100) -> Tuple[bool, str]:
        """Sets 100x leverage on ETHUSDT."""
        if not self.has_credentials():
            return False, "Missing API credentials"
        try:
            params = self._sign({
                "symbol": DEFAULT_CONFIG.symbol,
                "leverage": leverage
            })
            r = self.session.post(f"{self.base_url}/fapi/v1/leverage", data=params, timeout=5)
            if r.status_code == 200:
                res = r.json()
                self.max_allowed_leverage = int(res.get("leverage", leverage))
                self.leverage_verified = True
                return True, f"Leverage successfully set to {self.max_allowed_leverage}x"
            else:
                err = r.json()
                return False, err.get("msg", f"HTTP {r.status_code}")
        except Exception as e:
            return False, str(e)

    async def verify_and_set_leverage_async(self, leverage: int = 100):
        return await run_in_thread(self.verify_and_set_leverage, leverage)

    def verify_and_set_margin_type(self, margin_type: str = "ISOLATED") -> Tuple[bool, str]:
        """Sets margin type on ETHUSDT (ISOLATED or CROSSED)."""
        if not self.has_credentials():
            return False, "Missing API credentials"
        try:
            params = self._sign({
                "symbol": DEFAULT_CONFIG.symbol,
                "marginType": margin_type.upper()
            })
            r = self.session.post(f"{self.base_url}/fapi/v1/marginType", data=params, timeout=5)
            res = r.json()
            if r.status_code == 200 or res.get("code") == -4046:  # -4046 means "No need to change margin type"
                return True, f"Margin type set to {margin_type.upper()}"
            return False, res.get("msg", "Failed to change margin type")
        except Exception as e:
            return False, str(e)

    async def verify_and_set_margin_type_async(self, margin_type: str = "ISOLATED"):
        return await run_in_thread(self.verify_and_set_margin_type, margin_type)

    def fetch_account_state(self) -> Dict[str, Any]:
        """Fetches total balance, available margin, and active position on ETHUSDT."""
        if not self.has_credentials():
            return {"connected": False, "reason": "No credentials"}
        try:
            params = self._sign({})
            r = self.session.get(f"{self.base_url}/fapi/v2/account", params=params, timeout=5)
            if r.status_code != 200:
                return {"connected": False, "reason": f"API error: {r.status_code}"}
            
            data = r.json()
            total_wallet_balance = float(data.get("totalWalletBalance", 0.0))
            available_balance = float(data.get("availableBalance", 0.0))
            total_unrealized_pnl = float(data.get("totalUnrealizedProfit", 0.0))
            
            eth_pos = None
            positions = data.get("positions", [])
            for p in positions:
                if p.get("symbol") == DEFAULT_CONFIG.symbol:
                    amt = float(p.get("positionAmt", 0.0))
                    if abs(amt) > 0.0001:
                        side = "LONG" if amt > 0 else "SHORT"
                        entry_price = float(p.get("entryPrice", 0.0))
                        unrealized_pnl = float(p.get("unrealizedProfit", 0.0))
                        leverage = int(p.get("leverage", 100))
                        liq_price = float(p.get("liquidationPrice", 0.0))
                        notional = abs(amt) * entry_price
                        margin = notional / max(1, leverage)
                        eth_pos = {
                            "symbol": DEFAULT_CONFIG.symbol,
                            "displaySymbol": DEFAULT_CONFIG.display_symbol,
                            "side": side,
                            "qty": abs(amt),
                            "entryPrice": entry_price,
                            "markPrice": float(p.get("markPrice", entry_price)),
                            "liquidationPrice": liq_price,
                            "margin": round(margin, 4),
                            "leverage": leverage,
                            "unrealizedPnl": round(unrealized_pnl, 4),
                            "isolated": p.get("isolated", False)
                        }
                    break

            return {
                "connected": True,
                "balance": total_wallet_balance,
                "availableBalance": available_balance,
                "unrealizedPnl": total_unrealized_pnl,
                "usedMargin": round(total_wallet_balance - available_balance, 4),
                "position": eth_pos
            }
        except Exception as e:
            return {"connected": False, "reason": str(e)}

    async def fetch_account_state_async(self):
        return await run_in_thread(self.fetch_account_state)

    def fetch_open_orders(self, symbol: str = "ETHUSDT") -> List[Dict[str, Any]]:
        """Fetches all open orders (SL, TP, limit) for reconciliation."""
        if not self.has_credentials():
            return []
        try:
            params = self._sign({"symbol": symbol})
            r = self.session.get(f"{self.base_url}/fapi/v1/openOrders", params=params, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"[BINANCE_OPEN_ORDERS_ERR] {e}")
        return []

    async def fetch_open_orders_async(self, symbol: str = "ETHUSDT"):
        return await run_in_thread(self.fetch_open_orders, symbol)

    def place_order(self, symbol: str, side: str, order_type: str, qty: float,
                    price: Optional[float] = None, stop_price: Optional[float] = None,
                    client_order_id: Optional[str] = None, reduce_only: bool = False) -> Dict[str, Any]:
        """Places a production Futures order with strict validation."""
        if not self.has_credentials():
            return {"error": True, "msg": "API keys not set"}

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": qty
        }
        if price is not None:
            params["price"] = price
            params["timeInForce"] = "GTC"
        if stop_price is not None:
            params["stopPrice"] = stop_price
        if client_order_id:
            params["newClientOrderId"] = client_order_id
        if reduce_only:
            params["reduceOnly"] = "true"

        signed = self._sign(params)
        try:
            r = self.session.post(f"{self.base_url}/fapi/v1/order", data=signed, timeout=6)
            res = r.json()
            if r.status_code == 200:
                return res
            else:
                return {"error": True, "code": res.get("code"), "msg": res.get("msg", f"HTTP {r.status_code}")}
        except Exception as e:
            return {"error": True, "msg": str(e)}

    async def place_order_async(self, **kwargs):
        return await run_in_thread(self.place_order, **kwargs)

    def cancel_order(self, symbol: str, order_id: Optional[int] = None, client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancels a specific open order."""
        if not self.has_credentials():
            return {"error": True, "msg": "API keys not set"}
        params = {"symbol": symbol}
        if order_id is not None:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        signed = self._sign(params)
        try:
            r = self.session.delete(f"{self.base_url}/fapi/v1/order", data=signed, timeout=5)
            return r.json()
        except Exception as e:
            return {"error": True, "msg": str(e)}

    async def cancel_order_async(self, **kwargs):
        return await run_in_thread(self.cancel_order, **kwargs)

    def cancel_all_orders(self, symbol: str = "ETHUSDT") -> Dict[str, Any]:
        """Cancels all active open orders for the symbol."""
        if not self.has_credentials():
            return {"error": True, "msg": "API keys not set"}
        params = self._sign({"symbol": symbol})
        try:
            r = self.session.delete(f"{self.base_url}/fapi/v1/allOpenOrders", data=params, timeout=5)
            return r.json()
        except Exception as e:
            return {"error": True, "msg": str(e)}

    async def cancel_all_orders_async(self, symbol: str = "ETHUSDT"):
        return await run_in_thread(self.cancel_all_orders, symbol)

    def create_listen_key(self) -> Optional[str]:
        """Creates a User Data Stream listenKey."""
        if not self.has_credentials():
            return None
        try:
            r = self.session.post(f"{self.base_url}/fapi/v1/listenKey", timeout=5)
            if r.status_code == 200:
                self.listen_key = r.json().get("listenKey")
                return self.listen_key
        except Exception as e:
            print(f"[BINANCE_LISTENKEY_ERR] {e}")
        return None

    def keepalive_listen_key(self) -> bool:
        """Pings listenKey every 30 minutes to prevent expiration."""
        if not self.listen_key or not self.has_credentials():
            return False
        try:
            r = self.session.put(f"{self.base_url}/fapi/v1/listenKey", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
