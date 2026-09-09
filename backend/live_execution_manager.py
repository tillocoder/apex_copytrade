import os
import json
import time
import urllib.request
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
POSITIONS_FILE = os.path.join(DATA_DIR, "live_positions.json")
EQUITY_FILE = os.path.join(DATA_DIR, "live_equity.json")

INITIAL_CAPITAL = 10000.00
FILE_LOCK = threading.Lock()

from backend.quant_engine.position_sizing import PositionSizingEngine, PositionSizingResult
from backend.quant_engine.config import PropFirmRulesConfig

GLOBAL_PROP_RULES = PropFirmRulesConfig()

BLACKLISTED_SYMBOLS = {"ETH/USDT", "ETHUSDT"}
MAX_DAILY_TRADES_PER_SYMBOL = 2

def _ensure_dir(filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def is_trade_win(trade: Dict[str, Any]) -> bool:
    """Unified helper to strictly determine if a trade was profitable."""
    pnl = float(trade.get("realizedPnl", trade.get("realized_pnl", 0.0)) or 0.0)
    status = str(trade.get("status", "")).upper()
    return pnl > 0.0 or any(status.startswith(prefix) for prefix in ["CLOSED_TP1", "CLOSED_TP2", "CLOSED_BE_PROFIT", "CLOSED_PROFIT", "CLOSED_TRAILING_PROFIT"])

def _read_positions_unlocked() -> List[Dict[str, Any]]:
    if not os.path.exists(POSITIONS_FILE):
        return []
    try:
        with open(POSITIONS_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return []

def _write_positions_unlocked(positions: List[Dict[str, Any]]):
    """Atomic write with temporary file replacement to avoid read collisions."""
    _ensure_dir(POSITIONS_FILE)
    temp_file = POSITIONS_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(positions, f, indent=2)
        os.replace(temp_file, POSITIONS_FILE)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        print(f"[LIVE EXECUTION] Error atomically writing positions: {e}")

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
        with open(EQUITY_FILE, "r", encoding="utf-8-sig") as f:
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
    """Atomic write with temporary file replacement to guarantee immediate disk consistency."""
    _ensure_dir(EQUITY_FILE)
    temp_file = EQUITY_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_file, EQUITY_FILE)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        print(f"[LIVE EXECUTION] Error atomically writing equity state: {e}")

def load_positions() -> List[Dict[str, Any]]:
    with FILE_LOCK:
        return _read_positions_unlocked()

def save_positions(positions: List[Dict[str, Any]]):
    with FILE_LOCK:
        _write_positions_unlocked(positions)

def load_equity_state() -> Dict[str, Any]:
    with FILE_LOCK:
        eq = _read_equity_unlocked()
        th = eq.get("tradeHistory", [])
        wins = sum(1 for t in th if is_trade_win(t))
        eq["totalTrades"] = len(th)
        eq["closedTradesCount"] = len(th)
        eq["winCount"] = wins
        eq["winRate"] = round((wins / max(1, len(th))) * 100.0, 1) if th else 0.0
        curr_eq = round(float(eq.get("initialCapital", INITIAL_CAPITAL)) + float(eq.get("realizedPnl", 0.0)), 2)
        eq["currentEquity"] = curr_eq
        eq["equity"] = curr_eq
        eq["balance"] = curr_eq
        eq["nav"] = curr_eq
        return eq

def save_equity_state(state: Dict[str, Any]):
    with FILE_LOCK:
        _write_equity_unlocked(state)

def fetch_binance_price(symbol: str) -> float:
    sym = symbol.replace("/", "").upper()
    endpoints = [
        f"https://api.binance.com/api/v3/ticker/price?symbol={sym}",
        f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}",
        f"https://api1.binance.com/api/v3/ticker/price?symbol={sym}",
        f"https://api3.binance.com/api/v3/ticker/price?symbol={sym}"
    ]
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ApexLiveEngine/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                res = json.loads(resp.read().decode())
                return float(res["price"])
        except Exception:
            continue
    return 0.0

def open_position_from_signal(signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Opens a live position with professional prop firm position sizing and 2-stage TP targeting.
    """
    with FILE_LOCK:
        positions = _read_positions_unlocked()
        equity_state = _read_equity_unlocked()

        sym = signal.get("symbol", "BTC/USDT")
        if sym.upper() in BLACKLISTED_SYMBOLS:
            print(f"[LIVE EXECUTION] {sym} is blacklisted by quantitative policy. Skipping.")
            return None

        # Check Max Daily Trades Cap (Max 2 trades per day per asset)
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_trades_count = 0
        for p in positions:
            p_date = p.get("openedAt", "")[:10]
            if not p_date and p.get("entry_timestamp"):
                p_date = datetime.fromtimestamp(p["entry_timestamp"], tz=timezone.utc).strftime("%Y-%m-%d")
            if p.get("symbol") == sym and p_date == today_utc:
                today_trades_count += 1
        for th in equity_state.get("tradeHistory", []):
            th_date = th.get("openedAt", "")[:10]
            if not th_date and th.get("entry_timestamp"):
                th_date = datetime.fromtimestamp(th["entry_timestamp"], tz=timezone.utc).strftime("%Y-%m-%d")
            if th.get("symbol") == sym and th_date == today_utc:
                today_trades_count += 1

        if today_trades_count >= MAX_DAILY_TRADES_PER_SYMBOL:
            print(f"[LIVE EXECUTION] Daily trades cap reached for {sym} ({today_trades_count}/{MAX_DAILY_TRADES_PER_SYMBOL}). Skipping.")
            return None

        side = signal.get("side", signal.get("direction", "BUY")).upper()
        if side == "LONG":
            side = "BUY"
        elif side == "SHORT":
            side = "SELL"

        signal_entry = float(signal.get("entry_price") or signal.get("entry") or 0.0)
        signal_sl = float(signal.get("sl") or signal.get("stop_loss") or 0.0)
        signal_tp1 = float(signal.get("tp1") or 0.0)
        signal_tp2 = float(signal.get("tp2") or 0.0)

        # Ensure no active duplicate position for the same symbol
        for p in positions:
            if p.get("symbol") == sym and p.get("status") == "OPEN":
                print(f"[LIVE EXECUTION] Position for {sym} already open ({p.get('id')}). Skipping duplicate.")
                return None

        # Fetch live Binance market execution price
        try:
            live_price = fetch_binance_price(sym)
            executed_entry = live_price if live_price > 0 else signal_entry
        except Exception as e:
            print(f"[LIVE EXECUTION] Error fetching live price for {sym}, using signal entry: {e}")
            executed_entry = signal_entry

        # Calculate exact SL/TP distances
        if side == "BUY":
            sl_dist = executed_entry - signal_sl if signal_sl > 0 else executed_entry * 0.005
            sl_price = round(executed_entry - sl_dist, 2)
            tp1_min = executed_entry + (1.8 * sl_dist)
            tp1_price = round(max(signal_tp1, tp1_min) if signal_tp1 > 0 else tp1_min, 2)
            tp2_min = executed_entry + (3.0 * sl_dist)
            tp2_price = round(max(signal_tp2, tp2_min) if signal_tp2 > 0 else tp2_min, 2)
        else:
            sl_dist = signal_sl - executed_entry if signal_sl > 0 else executed_entry * 0.005
            sl_price = round(executed_entry + sl_dist, 2)
            tp1_min = executed_entry - (1.8 * sl_dist)
            tp1_price = round(min(signal_tp1, tp1_min) if signal_tp1 > 0 else tp1_min, 2)
            tp2_min = executed_entry - (3.0 * sl_dist)
            tp2_price = round(min(signal_tp2, tp2_min) if signal_tp2 > 0 else tp2_min, 2)

        # Prop Firm strict sizing (0.13% risk per trade)
        current_eq = equity_state.get("initialCapital", INITIAL_CAPITAL) + equity_state.get("realizedPnl", 0.0)
        calc_result: PositionSizingResult = PositionSizingEngine.calculate_position(
            account_balance=current_eq,
            entry_price=executed_entry,
            stop_loss=sl_price,
            rules=GLOBAL_PROP_RULES,
            symbol=sym
        )

        pos_id = f"pos_{sym.replace('/', '').lower()}_{int(time.time() * 1000)}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        new_pos = {
            "id": pos_id,
            "signal_id": signal.get("id"),
            "symbol": sym,
            "side": side,
            "entryPrice": round(executed_entry, 2),
            "entry_price": round(executed_entry, 2),
            "entry_timestamp": time.time(),
            "size": round(calc_result.position_size, 4),
            "original_size": round(calc_result.position_size, 4),
            "leverage": calc_result.leverage,
            "marginUsed": round(calc_result.margin_required, 2),
            "riskAmount": round(calc_result.risk_amount, 2),
            "riskPercent": round(calc_result.risk_percent, 2),
            "sl": sl_price,
            "stopLoss": sl_price,
            "tp1": tp1_price,
            "tp2": tp2_price,
            "takeProfit": tp1_price,
            "tp1_hit": False,
            "tp1_realized_pnl": 0.0,
            "trailingStopActive": False,
            "currentPrice": round(executed_entry, 2),
            "unrealizedPnl": 0.0,
            "unrealizedPnlPercent": 0.0,
            "realizedPnl": 0.0,
            "status": "OPEN",
            "openedAt": now_iso,
            "timeOpen": now_iso,
            "duration": "0m",
            "account": "PAPER EXECUTION · REAL BINANCE DATA",
            "aiExplanation": signal.get("rationale") or f"Institutional {signal.get('setup', 'OrderBlock Sweep')} Execution",
            "aiConfidence": signal.get("confidence") or signal.get("score") or 82.5,
            "events": [
                {"timestamp": now_iso, "event": "ORDER_FILLED", "price": round(executed_entry, 2)}
            ]
        }

        positions.append(new_pos)
        _write_positions_unlocked(positions)
        print(f"[PAPER ENGINE] Opened market-data position: {pos_id} ({sym} {side} @ ${executed_entry:,.2f})")

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
                if curr_price <= 0:
                    curr_price = float(p.get("currentPrice") or p.get("entryPrice", 0.0))
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
                
                p["account"] = p.get("account") or "PAPER EXECUTION · REAL BINANCE DATA"
                p["aiExplanation"] = p.get("aiExplanation") or p.get("ai_explanation") or ""
                p["aiConfidence"] = p.get("aiConfidence") or p.get("ai_confidence") or 0.0
                p["duration"] = p.get("duration") or ""
                p["timeOpen"] = p.get("timeOpen") or ""

                total_unrealized += unrealized
                positions_updated = True

                # INSTITUTIONAL MULTI-STAGE TP1 PARTIAL SCALE-OUT & EXPANSION TRAILING
                hit_event = None
                tp1_val = float(p.get("tp1") or tp)
                tp2_val = float(p.get("tp2") or (entry + 2.8 * abs(entry - sl) if side == "BUY" else entry - 2.8 * abs(entry - sl)))
                tp1_hit = p.get("tp1_hit", False)

                if side == "BUY":
                    # 1. TP1 Partial Scale-Out (50% locked)
                    if not tp1_hit and curr_price >= tp1_val:
                        partial_pnl = round((tp1_val - entry) * (size * 0.5), 2)
                        p["tp1_hit"] = True
                        p["tp1_realized_pnl"] = partial_pnl
                        p["original_size"] = size
                        p["size"] = round(size * 0.5, 4)
                        p["marginUsed"] = round(float(p.get("marginUsed", 1000)) * 0.5, 2)
                        
                        # Realize 50% profit into equity balance immediately
                        equity_state["realizedPnl"] = round(equity_state["realizedPnl"] + partial_pnl, 2)
                        equity_updated = True
                        positions_updated = True

                        # FLUSH TO DISK IMMEDIATELY before sending notification
                        _write_positions_unlocked(positions)
                        _write_equity_unlocked(equity_state)
                        
                        print(f"[LIVE ENGINE] {sym} TP1 HIT @ ${curr_price:.2f}! Secured 50% (+${partial_pnl:.2f} USD). Remaining 50% runner active for TP2 ${tp2_val:.2f}.")
                        
                        try:
                            from backend.telegram_bot import telegram_notifier
                            telegram_notifier.send_trade_update_notification(
                                p["id"], "TP1",
                                {
                                    "symbol": sym,
                                    "side": side,
                                    "entry_price": entry,
                                    "price": curr_price,
                                    "pnl": partial_pnl,
                                    "signal_id": p.get("signal_id"),
                                    "tp1": tp1_val,
                                    "tp2": tp2_val,
                                    "sl": p.get("sl")
                                }
                            )
                        except Exception as tg_e:
                            print(f"[LIVE ENGINE] Telegram TP1 alert error: {tg_e}")

                    # 2. Protected ATR Trailing Stop After TP1 (Avoid premature Break-Even knockout on retests)
                    if p.get("tp1_hit", False):
                        atr_val = float(p.get("atr", abs(tp1_val - entry) / 1.8) or 150.0)
                        candidate_trail = round(curr_price - 1.2 * atr_val, 2)
                        if candidate_trail > float(p.get("sl", sl)):
                            p["sl"] = candidate_trail
                            p["trailingStopActive"] = True
                            positions_updated = True
                            _write_positions_unlocked(positions)
                            print(f"[LIVE ENGINE] {sym} BUY ATR Trailing Stop updated to ${candidate_trail:.2f} (Current Price: ${curr_price:.2f})")
                            try:
                                from backend.telegram_bot import telegram_notifier
                                telegram_notifier.send_trade_update_notification(
                                    p["id"], "TRAILING_SL",
                                    {
                                        "symbol": sym,
                                        "side": side,
                                        "entry_price": entry,
                                        "price": curr_price,
                                        "sl": p["sl"],
                                        "tp2": tp2_val,
                                        "signal_id": p.get("signal_id")
                                    }
                                )
                            except Exception as tg_e:
                                print(f"[LIVE ENGINE] Telegram Trailing alert error: {tg_e}")

                    # 3. TP2 Hit (Close remaining 50%)
                    if curr_price >= tp2_val:
                        hit_event = "TP2"
                    # 4. SL Hit
                    elif curr_price <= float(p.get("sl", sl)):
                        hit_event = "SL" if not tp1_hit else "BE_PROFIT"

                elif side == "SELL":
                    # 1. TP1 Partial Scale-Out (50% locked)
                    if not tp1_hit and curr_price <= tp1_val:
                        partial_pnl = round((entry - tp1_val) * (size * 0.5), 2)
                        p["tp1_hit"] = True
                        p["tp1_realized_pnl"] = partial_pnl
                        p["original_size"] = size
                        p["size"] = round(size * 0.5, 4)
                        p["marginUsed"] = round(float(p.get("marginUsed", 1000)) * 0.5, 2)
                        
                        equity_state["realizedPnl"] = round(equity_state["realizedPnl"] + partial_pnl, 2)
                        equity_updated = True
                        positions_updated = True

                        # FLUSH TO DISK IMMEDIATELY before sending notification
                        _write_positions_unlocked(positions)
                        _write_equity_unlocked(equity_state)
                        
                        print(f"[LIVE ENGINE] {sym} TP1 HIT @ ${curr_price:.2f}! Secured 50% (+${partial_pnl:.2f} USD).")
                        
                        try:
                            from backend.telegram_bot import telegram_notifier
                            telegram_notifier.send_trade_update_notification(
                                p["id"], "TP1",
                                {
                                    "symbol": sym,
                                    "side": side,
                                    "entry_price": entry,
                                    "price": curr_price,
                                    "pnl": partial_pnl,
                                    "signal_id": p.get("signal_id"),
                                    "tp1": tp1_val,
                                    "tp2": tp2_val,
                                    "sl": p.get("sl")
                                }
                            )
                        except Exception as tg_e:
                            print(f"[LIVE ENGINE] Telegram SELL TP1 alert error: {tg_e}")

                    # 2. Protected ATR Trailing Stop After TP1 for SELL
                    if p.get("tp1_hit", False):
                        atr_val = float(p.get("atr", abs(entry - tp1_val) / 1.8) or 150.0)
                        candidate_trail = round(curr_price + 1.2 * atr_val, 2)
                        if candidate_trail < float(p.get("sl", sl)):
                            p["sl"] = candidate_trail
                            p["trailingStopActive"] = True
                            positions_updated = True
                            _write_positions_unlocked(positions)
                            print(f"[LIVE ENGINE] {sym} SELL ATR Trailing Stop updated to ${candidate_trail:.2f} (Current Price: ${curr_price:.2f})")
                            try:
                                from backend.telegram_bot import telegram_notifier
                                telegram_notifier.send_trade_update_notification(
                                    p["id"], "TRAILING_SL",
                                    {
                                        "symbol": sym,
                                        "side": side,
                                        "entry_price": entry,
                                        "price": curr_price,
                                        "sl": p["sl"],
                                        "tp2": tp2_val,
                                        "signal_id": p.get("signal_id")
                                    }
                                )
                            except Exception as tg_e:
                                print(f"[LIVE ENGINE] Telegram SELL Trailing alert error: {tg_e}")

                    # 3. TP2 Hit
                    if curr_price <= tp2_val:
                        hit_event = "TP2"
                    # 4. SL Hit
                    elif curr_price >= float(p.get("sl", sl)):
                        hit_event = "SL" if not tp1_hit else "BE_PROFIT"

                if hit_event:
                    final_rem_size = float(p.get("size", size))
                    final_rem_pnl = round((curr_price - entry) * final_rem_size if side == "BUY" else (entry - curr_price) * final_rem_size, 2)
                    tp1_pnl = float(p.get("tp1_realized_pnl", 0.0))
                    total_trade_pnl = round(tp1_pnl + final_rem_pnl, 2)
                    
                    p["status"] = f"CLOSED_{hit_event}"
                    p["exit_timestamp"] = time.time()
                    p["closePrice"] = curr_price
                    p["realizedPnl"] = total_trade_pnl

                    equity_state["realizedPnl"] = round(equity_state["realizedPnl"] + final_rem_pnl, 2)
                    equity_state["closedTradesCount"] += 1
                    if is_trade_win(p):
                        equity_state["winCount"] += 1

                    new_eq = round(equity_state["initialCapital"] + equity_state["realizedPnl"], 2)
                    now_str = datetime.now(timezone.utc).strftime("%H:%M")
                    equity_state["liveEquityCurve"].append({"timestamp": now_str, "equity": new_eq})
                    equity_state["tradeHistory"].append(p)
                    equity_updated = True
                    positions_updated = True

                    _write_positions_unlocked(positions)
                    _write_equity_unlocked(equity_state)

                    print(f"[LIVE ENGINE] Position {p['id']} closed via {hit_event}! Total Net PnL: ${total_trade_pnl:+.2f}")

                    signal_id = p.get("signal_id")
                    if signal_id:
                        try:
                            from backend.database import SignalsRepository
                            existing_sig = SignalsRepository.get_by_id(signal_id)
                            if existing_sig:
                                existing_sig["status"] = f"CLOSED_{hit_event}"
                                existing_sig["exit_price"] = curr_price
                                existing_sig["realized_pnl"] = total_trade_pnl
                                existing_sig["exit_timestamp"] = time.time()
                                SignalsRepository.save_or_update(existing_sig)
                                print(f"[LIVE ENGINE] Signal {signal_id} status -> CLOSED_{hit_event}")
                        except Exception as sig_err:
                            print(f"[LIVE ENGINE] Signal status sync error: {sig_err}")

                    try:
                        from backend.telegram_bot import telegram_notifier
                        telegram_notifier.send_trade_update_notification(
                            p["id"], hit_event,
                            {
                                "symbol": sym,
                                "side": side,
                                "entry_price": entry,
                                "price": curr_price,
                                "pnl": total_trade_pnl,
                                "stage_pnl": final_rem_pnl,
                                "tp1_pnl": tp1_pnl,
                                "tp1_hit": tp1_hit,
                                "pnl_pct": p.get("unrealizedPnlPercent", 0.0),
                                "signal_id": p.get("signal_id"),
                                "tp1": p.get("tp1"),
                                "tp2": p.get("tp2"),
                                "sl": p.get("sl")
                            }
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
        total_closed = equity_state.get("closedTradesCount", len(equity_state.get("tradeHistory", [])))
        win_count = equity_state.get("winCount", 0)
        win_rate = round((win_count / max(1, total_closed)) * 100.0, 1) if total_closed > 0 else 0.0

        return {
            "initialCapital": equity_state["initialCapital"],
            "currentEquity": current_total_equity,
            "realizedPnl": equity_state["realizedPnl"],
            "unrealizedPnl": round(total_unrealized, 2),
            "totalTrades": total_closed,
            "winRate": win_rate,
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
