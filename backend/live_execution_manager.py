import os
import json
import time
import urllib.request
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

POSITIONS_FILE = "backend/data/live_positions.json"
EQUITY_FILE = "backend/data/live_equity.json"

INITIAL_CAPITAL = 10000.00
FILE_LOCK = threading.Lock()

from backend.quant_engine.position_sizing import PositionSizingEngine, PositionSizingResult
from backend.quant_engine.config import PropFirmRulesConfig

GLOBAL_PROP_RULES = PropFirmRulesConfig()

def _ensure_dir(filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def _read_positions_unlocked() -> List[Dict[str, Any]]:
    if not os.path.exists(POSITIONS_FILE):
        return []
    try:
        with open(POSITIONS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _write_positions_unlocked(positions: List[Dict[str, Any]]):
    _ensure_dir(POSITIONS_FILE)
    try:
        with open(POSITIONS_FILE, "w") as f:
            json.dump(positions, f, indent=2)
    except Exception as e:
        print(f"[LIVE EXECUTION] Error writing positions: {e}")

def _read_equity_unlocked() -> Dict[str, Any]:
    if not os.path.exists(EQUITY_FILE):
        now_time = datetime.now(timezone.utc).strftime("%H:%M")
        return {
            "initialCapital": INITIAL_CAPITAL,
            "realizedPnl": 0.0,
            "closedTradesCount": 0,
            "winCount": 0,
            "liveEquityCurve": [
                {"timestamp": f"Start {now_time}", "equity": INITIAL_CAPITAL}
            ],
            "tradeHistory": []
        }
    try:
        with open(EQUITY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        now_time = datetime.now(timezone.utc).strftime("%H:%M")
        return {
            "initialCapital": INITIAL_CAPITAL,
            "realizedPnl": 0.0,
            "closedTradesCount": 0,
            "winCount": 0,
            "liveEquityCurve": [
                {"timestamp": f"Start {now_time}", "equity": INITIAL_CAPITAL}
            ],
            "tradeHistory": []
        }

def _write_equity_unlocked(state: Dict[str, Any]):
    _ensure_dir(EQUITY_FILE)
    try:
        with open(EQUITY_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[LIVE EXECUTION] Error writing equity state: {e}")

def load_positions() -> List[Dict[str, Any]]:
    with FILE_LOCK:
        return _read_positions_unlocked()

def save_positions(positions: List[Dict[str, Any]]):
    with FILE_LOCK:
        _write_positions_unlocked(positions)

def load_equity_state() -> Dict[str, Any]:
    with FILE_LOCK:
        return _read_equity_unlocked()

def save_equity_state(state: Dict[str, Any]):
    with FILE_LOCK:
        _write_equity_unlocked(state)

def fetch_binance_price(symbol: str) -> float:
    sym = symbol.replace("/", "").upper()
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
    req = urllib.request.Request(url, headers={"User-Agent": "ApexLiveEngine/5.0"})
    with urllib.request.urlopen(req, timeout=3) as resp:
        res = json.loads(resp.read().decode())
        return float(res["price"])

def open_position_from_signal(signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with FILE_LOCK:
        positions = _read_positions_unlocked()
        sym = signal.get("symbol")
        
        # Check if symbol already has an open live position
        for p in positions:
            if p.get("symbol") == sym and p.get("status") == "OPEN":
                return None

        entry = float(signal.get("entry", 0.0))
        sl = float(signal.get("sl", 0.0))
        tp = float(signal.get("tp", 0.0))
        side = signal.get("side", "BUY").upper()
        
        if entry <= 0:
            return None

        if sl <= 0:
            sl = round(entry * (0.99 if side == "BUY" else 1.01), 4)

        if tp <= 0:
            tp = round(entry * (1.025 if side == "BUY" else 0.975), 4)

        # Institutional Prop Firm Position Sizing (aligned 100% with PositionSizingEngine)
        equity_state = _read_equity_unlocked()
        current_balance = equity_state["initialCapital"] + equity_state["realizedPnl"]
        
        open_pos_list = [p for p in positions if p.get("status") == "OPEN"]

        sizing_res = PositionSizingEngine.calculate_position_size(
            symbol=sym,
            side=side,
            entry_price=entry,
            stop_loss=sl,
            current_equity=current_balance,
            open_positions=open_pos_list,
            pending_orders=[],
            prop_rules=GLOBAL_PROP_RULES,
            confidence_score=float(signal.get("confidence", 80.0))
        )

        if not sizing_res.is_approved or sizing_res.final_size <= 0:
            print(f"[LIVE ENGINE REJECT] Position for {sym} rejected: {sizing_res.rejection_reason}")
            return None

        size = sizing_res.final_size
        leverage = int(sizing_res.effective_leverage)
        margin_used = sizing_res.initial_margin
        pos_id = f"pos_{sym.replace('/', '').lower()}_{int(time.time())}"
        
        try:
            curr_price = fetch_binance_price(sym)
        except Exception:
            curr_price = entry

        # Market Execution: entry price is the actual Binance price at the moment of order placement
        executed_entry = curr_price if curr_price > 0 else entry

        if side == "BUY":
            unrealized = (curr_price - executed_entry) * size
        else:
            unrealized = (executed_entry - curr_price) * size

        expected_profit = round(abs(tp - executed_entry) * size, 2)
        expected_loss = round(abs(executed_entry - sl) * size, 2)

        new_pos = {
            "id": pos_id,
            "account": "FTMO 10K LIVE EVALUATION",
            "symbol": sym,
            "side": side,
            "entryPrice": executed_entry,
            "currentPrice": curr_price,
            "size": size,
            "leverage": leverage,
            "marginUsed": margin_used,
            "unrealizedPnl": round(unrealized, 2),
            "unrealizedPnlPercent": round((unrealized / max(1.0, margin_used)) * 100.0, 2),
            "sl": sl,
            "tp1": tp,
            "tp2": round(tp * (1.01 if side == "BUY" else 0.99), 2),
            "tp3": round(tp * (1.02 if side == "BUY" else 0.98), 2),
            "breakEvenPrice": executed_entry,
            "trailingStopActive": False,
            "trailingDistancePct": 0.5,
            "atr": 35.0 if "BTC" in sym else 2.0,
            "riskPercent": 1.5,
            "rewardPercent": 3.0,
            "expectedProfit": expected_profit,
            "expectedLoss": expected_loss,
            "commission": round(margin_used * 0.0004, 2),
            "fundingFee": 0.0,
            "swapFees": 0.0,
            "liquidationPrice": round(entry * (0.80 if side == "BUY" else 1.20), 2),
            "duration": "0h 15m",
            "timeOpen": datetime.now(timezone.utc).strftime("%H:%M"),
            "aiExplanation": signal.get("reasoning") or signal.get("ai_explanation") or "M15 OrderFlow + Confluence Trend Entry",
            "aiConfidence": signal.get("confidence") or signal.get("ai_confidence") or 85.0,
            "aiRecommendation": "HOLD",
            "status": "OPEN",
            "entry_timestamp": time.time(),
            "formatted_entry_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "signal_id": signal.get("id"),
            "timeline": [
                {
                    "id": f"tl_{int(time.time())}",
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M UTC"),
                    "title": "Position Opened",
                    "reason": "AI Signal Executed at Market Price",
                    "triggeredBy": "Quant Execution Engine",
                    "riskImpact": "1.5% Base Risk",
                    "challengeImpact": "+0.0% PnL",
                    "severity": "info"
                }
            ]
        }

        positions.append(new_pos)
        _write_positions_unlocked(positions)
        print(f"[LIVE ENGINE] Opened LIVE Position: {pos_id} ({sym} {side} @ ${executed_entry:,.2f})")

    # Notify Telegram outside lock to prevent blocking
    try:
        from backend.telegram_bot import telegram_notifier
        telegram_notifier.send_trade_open_notification(new_pos)
    except Exception as e:
        print(f"[LIVE ENGINE] Telegram alert error on open: {e}")

    return new_pos

def sync_live_positions_and_equity() -> Dict[str, Any]:
    with FILE_LOCK:
        positions = _read_positions_unlocked()
        equity_state = _read_equity_unlocked()
        open_positions = [p for p in positions if p.get("status") == "OPEN"]

        total_unrealized = 0.0
        positions_updated = False
        equity_updated = False

        for p in open_positions:
            sym = p.get("symbol")
            try:
                curr_price = fetch_binance_price(sym)
                p["currentPrice"] = curr_price
                
                entry = float(p.get("entryPrice", curr_price))
                size = float(p.get("size", 0.1))
                side = p.get("side", "BUY").upper()
                sl = float(p.get("sl", 0.0))
                tp = float(p.get("tp1", 0.0))
                margin = float(p.get("marginUsed", 100.0))

                if side == "BUY":
                    unrealized = (curr_price - entry) * size
                else:
                    unrealized = (entry - curr_price) * size

                p["unrealizedPnl"] = round(unrealized, 2)
                p["unrealizedPnlPercent"] = round((unrealized / max(1.0, margin)) * 100.0, 2)
                
                p["account"] = p.get("account") or "FTMO 10K LIVE EVALUATION"
                p["aiExplanation"] = p.get("aiExplanation") or p.get("ai_explanation") or "M15 OrderFlow Confluence"
                p["aiConfidence"] = p.get("aiConfidence") or p.get("ai_confidence") or 85.0
                p["duration"] = p.get("duration") or "0h 15m"
                p["timeOpen"] = p.get("timeOpen") or "Just Now"

                total_unrealized += unrealized
                positions_updated = True

                # Check SL/TP Hits
                hit_event = None
                if side == "BUY":
                    if curr_price >= tp:
                        hit_event = "TP1"
                    elif curr_price <= sl:
                        hit_event = "SL"
                elif side == "SELL":
                    if curr_price <= tp:
                        hit_event = "TP1"
                    elif curr_price >= sl:
                        hit_event = "SL"

                if hit_event:
                    p["status"] = f"CLOSED_{hit_event}"
                    p["exit_timestamp"] = time.time()
                    p["closePrice"] = curr_price
                    p["realizedPnl"] = round(unrealized, 2)

                    equity_state["realizedPnl"] = round(equity_state["realizedPnl"] + unrealized, 2)
                    equity_state["closedTradesCount"] += 1
                    if unrealized > 0:
                        equity_state["winCount"] += 1

                    new_eq = round(equity_state["initialCapital"] + equity_state["realizedPnl"], 2)
                    now_str = datetime.now(timezone.utc).strftime("%H:%M")
                    equity_state["liveEquityCurve"].append({"timestamp": now_str, "equity": new_eq})
                    equity_state["tradeHistory"].append(p)
                    equity_updated = True

                    print(f"[LIVE ENGINE] Position {p['id']} closed via {hit_event}! Realized PnL: ${unrealized:+.2f}")

                    try:
                        from backend.telegram_bot import telegram_notifier
                        telegram_notifier.send_trade_update_notification(
                            p["id"], hit_event,
                            {"price": curr_price, "pnl": unrealized, "pnl_pct": p["unrealizedPnlPercent"]}
                        )
                    except Exception as tg_e:
                        print(f"[LIVE ENGINE] Telegram close alert error: {tg_e}")

            except Exception as e:
                print(f"[LIVE ENGINE] Error syncing symbol {sym}: {e}")

        if positions_updated:
            _write_positions_unlocked(positions)
        if equity_updated:
            _write_equity_unlocked(equity_state)

        current_total_equity = round(equity_state["initialCapital"] + equity_state["realizedPnl"] + total_unrealized, 2)

        return {
            "initialCapital": equity_state["initialCapital"],
            "currentEquity": current_total_equity,
            "realizedPnl": equity_state["realizedPnl"],
            "unrealizedPnl": round(total_unrealized, 2),
            "totalTrades": equity_state["closedTradesCount"],
            "winRate": round((equity_state["winCount"] / max(1, equity_state["closedTradesCount"])) * 100.0, 1),
            "liveEquityCurve": equity_state["liveEquityCurve"],
            "openPositions": [p for p in positions if p.get("status") == "OPEN"]
        }

def reset_live_execution(initial_capital: float = INITIAL_CAPITAL) -> Dict[str, Any]:
    with FILE_LOCK:
        _write_positions_unlocked([])
        
        now_time = datetime.now(timezone.utc).strftime("%H:%M")
        equity_state = {
            "initialCapital": initial_capital,
            "realizedPnl": 0.0,
            "closedTradesCount": 0,
            "winCount": 0,
            "liveEquityCurve": [
                {"timestamp": f"Reset {now_time}", "equity": initial_capital}
            ],
            "tradeHistory": []
        }
        _write_equity_unlocked(equity_state)

    try:
        from backend.ai_signal_engine import save_signals_history
        save_signals_history([])
    except Exception as e:
        print(f"[LIVE RESET] Signals history wipe error: {e}")

    return {"status": "SUCCESS", "message": f"Live execution reset to ${initial_capital:,.2f} baseline starting fresh today."}
