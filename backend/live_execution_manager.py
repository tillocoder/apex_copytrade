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

def _ensure_dir(filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def _read_positions_unlocked() -> List[Dict[str, Any]]:
    if not os.path.exists(POSITIONS_FILE):
        return []
    try:
        with open(POSITIONS_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return []

def _write_positions_unlocked(positions: List[Dict[str, Any]]):
    _ensure_dir(POSITIONS_FILE)
    try:
        with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
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
    _ensure_dir(EQUITY_FILE)
    try:
        with open(EQUITY_FILE, "w", encoding="utf-8") as f:
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
        tp = float(signal.get("tp1", signal.get("tp", 0.0)) or 0.0)
        side = signal.get("side", "BUY").upper()
        
        if entry <= 0 or sl <= 0 or tp <= 0:
            print(f"[PAPER ENGINE REJECT] {sym} rejected: signal is missing a valid entry, stop, or TP1.")
            return None
        if (side == "BUY" and not (sl < entry < tp)) or (side == "SELL" and not (tp < entry < sl)):
            print(f"[PAPER ENGINE REJECT] {sym} rejected: invalid {side} entry/SL/TP ordering.")
            return None

        # Strict M15 Range Safety Clamp (prevents D1/H4 wide swing leakage)
        is_btc = "BTC" in sym.upper()
        max_allowed_sl_dist = 650.0 if is_btc else 45.0
        sl_dist = abs(entry - sl)
        if sl_dist > max_allowed_sl_dist:
            print(f"[LIVE ENGINE CLAMP] {sym} SL distance {sl_dist:.2f} was too wide; clamping to strict M15 {max_allowed_sl_dist:.2f} pts.")
            if side == "BUY":
                sl = round(entry - max_allowed_sl_dist, 2)
                tp = round(entry + 1.5 * max_allowed_sl_dist, 2)
            else:
                sl = round(entry + max_allowed_sl_dist, 2)
                tp = round(entry - 1.5 * max_allowed_sl_dist, 2)

        # Institutional Prop Firm Position Sizing (aligned 100% with PositionSizingEngine)
        equity_state = _read_equity_unlocked()
        current_balance = equity_state["initialCapital"] + equity_state["realizedPnl"]
        
        # Hard Circuit Breaker Guard (Stop trading if total loss >= $800 = 8.0% DD safety floor)
        total_loss = INITIAL_CAPITAL - current_balance
        if total_loss >= (INITIAL_CAPITAL * 0.08):
            print(f"[LIVE ENGINE REJECT] {sym} rejected: Hard Prop Drawdown Safety Floor reached (-{round((total_loss/INITIAL_CAPITAL)*100, 2)}%)")
            return None

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

        signal_indicators = signal.get("indicators") or {}
        signal_atr = float(signal_indicators.get("atr", 0.0) or 0.0)
        risk_percent = round((expected_loss / max(current_balance, 1.0)) * 100.0, 3)
        reward_percent = round((expected_profit / max(current_balance, 1.0)) * 100.0, 3)

        new_pos = {
            "id": pos_id,
            "account": "PAPER EXECUTION · REAL BINANCE DATA",
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
            "tp2": float(signal.get("tp2", 0.0) or 0.0),
            "tp3": float(signal.get("tp3", 0.0) or 0.0),
            "breakEvenPrice": executed_entry,
            "trailingStopActive": False,
            "trailingDistancePct": 0.5,
            "atr": signal_atr,
            "riskPercent": risk_percent,
            "rewardPercent": reward_percent,
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

                    # 2. Dynamic Trailing After TP1: Only move to Break-Even once price expands 25% towards TP2!
                    if p.get("tp1_hit", False):
                        expansion_target = tp1_val + 0.25 * (tp2_val - tp1_val)
                        if curr_price >= expansion_target and p.get("sl") < entry:
                            p["sl"] = round(entry + 0.1 * abs(tp1_val - entry), 2) # Lock slightly above entry (guaranteed green buffer)
                            p["trailingStopActive"] = True
                            positions_updated = True
                            print(f"[LIVE ENGINE] {sym} expanded towards TP2! Trailed SL to Entry+Buffer: ${p['sl']:.2f}")
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
                        
                        print(f"[LIVE ENGINE] {sym} TP1 HIT @ ${curr_price:.2f}! Secured 50% (+${partial_pnl:.2f} USD).")
                        
                        try:
                            from backend.telegram_bot import telegram_notifier
                            telegram_notifier.send_direct_message(
                                5563813326,
                                f"🎯 <b>{sym} TP1 URILDI! (+${partial_pnl:.2f} USD)</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"💰 <b>50% Foyda Naqd Qilindi:</b> +${partial_pnl:.2f}\n"
                                f"🚀 <b>Qolgan 50%:</b> TP2 (${tp2_val:,.2f}) tomon davom etmoqda.\n"
                                f"🛡️ <i>Narx TP2 tomon kengayishi bilan SL avtomatik Break-Even'ga ko'chiriladi!</i>"
                            )
                        except Exception:
                            pass

                    # 2. Dynamic Trailing After TP1 for SELL
                    if p.get("tp1_hit", False):
                        expansion_target = tp1_val - 0.25 * (tp1_val - tp2_val)
                        if curr_price <= expansion_target and p.get("sl") > entry:
                            p["sl"] = round(entry - 0.1 * abs(entry - tp1_val), 2)
                            p["trailingStopActive"] = True
                            positions_updated = True
                            print(f"[LIVE ENGINE] {sym} expanded towards TP2! Trailed SL to Entry+Buffer: ${p['sl']:.2f}")

                    # 3. TP2 Hit
                    if curr_price <= tp2_val:
                        hit_event = "TP2"
                    # 4. SL Hit
                    elif curr_price >= float(p.get("sl", sl)):
                        hit_event = "SL" if not tp1_hit else "BE_PROFIT"

                if hit_event:
                    final_rem_size = float(p.get("size", size))
                    final_rem_pnl = (curr_price - entry) * final_rem_size if side == "BUY" else (entry - curr_price) * final_rem_size
                    total_trade_pnl = round(float(p.get("tp1_realized_pnl", 0.0)) + final_rem_pnl, 2)
                    
                    p["status"] = f"CLOSED_{hit_event}"
                    p["exit_timestamp"] = time.time()
                    p["closePrice"] = curr_price
                    p["realizedPnl"] = total_trade_pnl

                    equity_state["realizedPnl"] = round(equity_state["realizedPnl"] + final_rem_pnl, 2)
                    equity_state["closedTradesCount"] += 1
                    if total_trade_pnl > 0:
                        equity_state["winCount"] += 1

                    new_eq = round(equity_state["initialCapital"] + equity_state["realizedPnl"], 2)
                    now_str = datetime.now(timezone.utc).strftime("%H:%M")
                    equity_state["liveEquityCurve"].append({"timestamp": now_str, "equity": new_eq})
                    equity_state["tradeHistory"].append(p)
                    equity_updated = True

                    print(f"[LIVE ENGINE] Position {p['id']} closed via {hit_event}! Total Net PnL: ${total_trade_pnl:+.2f}")

                    # ── CRITICAL FIX: Sync signal status when position closes ──────
                    signal_id = p.get("signal_id")
                    if signal_id:
                        try:
                            from backend.database import SignalsRepository
                            existing_sig = SignalsRepository.get_by_id(signal_id)
                            if existing_sig:
                                existing_sig["status"] = f"CLOSED_{hit_event}"
                                existing_sig["exit_price"] = curr_price
                                existing_sig["realized_pnl"] = round(unrealized, 2)
                                existing_sig["exit_timestamp"] = time.time()
                                SignalsRepository.save_or_update(existing_sig)
                                print(f"[LIVE ENGINE] Signal {signal_id} status -> CLOSED_{hit_event}")
                        except Exception as sig_err:
                            print(f"[LIVE ENGINE] Signal status sync error: {sig_err}")
                    # ──────────────────────────────────────────────────────────────────

                    try:
                        from backend.telegram_bot import telegram_notifier
                        telegram_notifier.send_trade_update_notification(
                            p["id"], hit_event,
                            {
                                "symbol": sym,
                                "side": side,
                                "entry_price": entry,
                                "price": curr_price,
                                "pnl": unrealized,
                                "pnl_pct": p["unrealizedPnlPercent"],
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
