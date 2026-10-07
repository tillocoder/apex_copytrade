"""
Paper Trading Tracker & Performance Analytics
Tracks active paper positions over subsequent market bars:
- MFE (Maximum Favorable Excursion)
- MAE (Maximum Adverse Excursion)
- TP1 / TP2 / SL / Expiry hits
- R-multiple realization
- Performance Analytics across Symbols, Regimes, Setups, and Confidence Buckets (70-75, 75-80, 80-85, 85-90, 90+).
"""

import os
import json
import time
from typing import Dict, List, Any, Optional

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "ai_market_discovery", "paper_trade_log.json")


class PaperTracker:
    def __init__(self, storage_path: str = DATA_FILE):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self.trades: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.trades, f, indent=2)

    def record_signal(self, signal: Dict[str, Any], risk_profile: Dict[str, Any]):
        """Records a new validated signal into the paper tracker."""
        if signal.get("decision") not in ("LONG", "SHORT"):
            return

        sig_id = f"ai_sig_{signal.get('symbol')}_{int(time.time())}"
        trade = {
            "id": sig_id,
            "timestamp": int(time.time() * 1000),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "symbol": signal.get("symbol"),
            "direction": signal.get("decision"),
            "entry_price": float(signal.get("entry", 0.0)),
            "stop_loss": float(signal.get("stop_loss", 0.0)),
            "take_profit_1": float(signal.get("take_profit_1", 0.0)),
            "take_profit_2": float(signal.get("take_profit_2", 0.0)),
            "confidence": float(signal.get("confidence", 0.0)),
            "setup_quality": float(signal.get("setup_quality", 0.0)),
            "regime": signal.get("regime", "UNKNOWN"),
            "setup_type": signal.get("setup_type", "UNKNOWN"),
            "status": "ACTIVE",
            "mfe_pct": 0.0,
            "mae_pct": 0.0,
            "mfe_r": 0.0,
            "mae_r": 0.0,
            "r_result": None,
            "tp1_hit": False,
            "tp2_hit": False,
            "sl_hit": False,
            "exit_time": None,
            "holding_minutes": 0,
            "expiry_time": int(time.time() * 1000) + int(signal.get("signal_expiry_minutes", 60)) * 60 * 1000,
            "quantity": risk_profile.get("quantity", 0.0),
            "notional_usd": risk_profile.get("notional_usd", 0.0),
            "why_this_setup": signal.get("why_this_setup", "")
        }
        self.trades.append(trade)
        self._save()

    def update_bar(self, symbol: str, bar: Dict[str, float]):
        """Convenience method to update open trades for a single symbol bar."""
        self.update_open_trades({symbol.replace("/", ""): bar})

    def update_open_trades(self, live_prices: Dict[str, Dict[str, float]]):
        """
        Updates open signals against latest market candle prices {symbol: {high, low, close}}.
        Checks TP1, TP2, SL, MFE, MAE, Expiry.
        """
        now_ts = int(time.time() * 1000)
        changed = False

        for t in self.trades:
            if t["status"] != "ACTIVE":
                continue

            sym = t["symbol"].replace("/", "")
            if sym not in live_prices:
                continue

            candle = live_prices[sym]
            h = candle.get("high", t["entry_price"])
            l = candle.get("low", t["entry_price"])
            c = candle.get("close", t["entry_price"])

            entry = t["entry_price"]
            sl = t["stop_loss"]
            tp1 = t["take_profit_1"]
            tp2 = t["take_profit_2"]
            is_long = t["direction"] == "LONG"
            risk_dist = abs(entry - sl) if abs(entry - sl) > 0 else 1.0

            # Calculate excursions
            if is_long:
                favorable = max(0.0, h - entry)
                adverse = max(0.0, entry - l)
            else:
                favorable = max(0.0, entry - l)
                adverse = max(0.0, h - entry)

            mfe_pct = (favorable / entry) * 100.0
            mae_pct = (adverse / entry) * 100.0
            mfe_r = favorable / risk_dist
            mae_r = adverse / risk_dist

            t["mfe_pct"] = max(t["mfe_pct"], round(mfe_pct, 2))
            t["mae_pct"] = max(t["mae_pct"], round(mae_pct, 2))
            t["mfe_r"] = max(t["mfe_r"], round(mfe_r, 2))
            t["mae_r"] = max(t["mae_r"], round(mae_r, 2))
            t["holding_minutes"] = round((now_ts - t["timestamp"]) / 60000.0, 1)

            # Check SL hit first (pessimistic)
            hit_sl = (l <= sl) if is_long else (h >= sl)
            hit_tp1 = (h >= tp1) if is_long else (l <= tp1)
            hit_tp2 = (h >= tp2) if is_long else (l <= tp2)

            if hit_sl:
                t["status"] = "CLOSED_SL"
                t["sl_hit"] = True
                t["r_result"] = -1.0
                t["exit_time"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
                changed = True
            elif hit_tp2:
                t["status"] = "CLOSED_TP2"
                t["tp1_hit"] = True
                t["tp2_hit"] = True
                t["r_result"] = round(abs(tp2 - entry) / risk_dist, 2)
                t["exit_time"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
                changed = True
            elif hit_tp1 and not t["tp1_hit"]:
                t["tp1_hit"] = True
                t["status"] = "PARTIAL_TP1"
                t["r_result"] = round(abs(tp1 - entry) / risk_dist, 2)
                changed = True
            elif now_ts >= t["expiry_time"]:
                # Signal expired
                t["status"] = "EXPIRED"
                if is_long:
                    cur_r = (c - entry) / risk_dist
                else:
                    cur_r = (entry - c) / risk_dist
                t["r_result"] = round(cur_r, 2)
                t["exit_time"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
                changed = True

        if changed:
            self._save()

    def get_analytics(self) -> Dict[str, Any]:
        """Computes comprehensive performance analytics across confidence buckets and setups."""
        closed = [t for t in self.trades if t["status"] in ("CLOSED_SL", "CLOSED_TP1", "CLOSED_TP2", "PARTIAL_TP1", "EXPIRED")]
        n_closed = len(closed)

        winners = [t for t in closed if (t.get("r_result") or 0) > 0]
        losers = [t for t in closed if (t.get("r_result") or 0) <= 0]

        win_rate = (len(winners) / n_closed * 100.0) if n_closed > 0 else 0.0
        avg_r = sum(t.get("r_result", 0.0) for t in closed) / n_closed if n_closed > 0 else 0.0
        gross_win_r = sum(t.get("r_result", 0.0) for t in winners)
        gross_loss_r = abs(sum(t.get("r_result", 0.0) for t in losers))
        profit_factor = round(gross_win_r / gross_loss_r, 2) if gross_loss_r > 0 else (99.0 if gross_win_r > 0 else 0.0)

        # Confidence Bucket Analysis
        buckets = {
            "70-75": {"total": 0, "wins": 0, "sum_r": 0.0},
            "75-80": {"total": 0, "wins": 0, "sum_r": 0.0},
            "80-85": {"total": 0, "wins": 0, "sum_r": 0.0},
            "85-90": {"total": 0, "wins": 0, "sum_r": 0.0},
            "90+":   {"total": 0, "wins": 0, "sum_r": 0.0},
        }

        for t in closed:
            conf = t.get("confidence", 75.0)
            r = t.get("r_result", 0.0)
            is_win = r > 0
            if conf < 75: b = "70-75"
            elif conf < 80: b = "75-80"
            elif conf < 85: b = "80-85"
            elif conf < 90: b = "85-90"
            else: b = "90+"

            buckets[b]["total"] += 1
            if is_win: buckets[b]["wins"] += 1
            buckets[b]["sum_r"] += r

        confidence_correlation = {}
        for b, v in buckets.items():
            tot = v["total"]
            wr = round(v["wins"] / tot * 100.0, 1) if tot > 0 else 0.0
            avg_b_r = round(v["sum_r"] / tot, 2) if tot > 0 else 0.0
            confidence_correlation[b] = {
                "total_trades": tot,
                "win_rate_pct": wr,
                "expectancy_r": avg_b_r
            }

        return {
            "total_signals_recorded": len(self.trades),
            "active_signals_count": sum(1 for t in self.trades if t["status"] == "ACTIVE"),
            "closed_signals_count": n_closed,
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": profit_factor,
            "expectancy_r": round(avg_r, 2),
            "total_r_realized": round(sum(t.get("r_result", 0.0) for t in closed), 2),
            "avg_mfe_r": round(sum(t.get("mfe_r", 0.0) for t in closed) / n_closed, 2) if n_closed > 0 else 0.0,
            "avg_mae_r": round(sum(t.get("mae_r", 0.0) for t in closed) / n_closed, 2) if n_closed > 0 else 0.0,
            "tp1_hit_rate_pct": round(sum(1 for t in closed if t.get("tp1_hit")) / n_closed * 100.0, 1) if n_closed > 0 else 0.0,
            "tp2_hit_rate_pct": round(sum(1 for t in closed if t.get("tp2_hit")) / n_closed * 100.0, 1) if n_closed > 0 else 0.0,
            "sl_rate_pct": round(sum(1 for t in closed if t.get("sl_hit")) / n_closed * 100.0, 1) if n_closed > 0 else 0.0,
            "confidence_bucket_breakdown": confidence_correlation
        }

    def get_recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self.trades[-limit:]))

    get_performance_analytics = get_analytics
