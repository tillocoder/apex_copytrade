from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional, Tuple, Dict, Any

class TournamentBacktest:
    def __init__(self, data, cfg, execution_cfg):
        self.data = data
        self.cfg = cfg
        self.exec_cfg = execution_cfg

    def _cost(self, notional):
        # FIX: notional is already (entry + exit) * size, which covers both legs.
        # Therefore rate is one-way rate (comm + slip), NOT multiplied by 2.0.
        rate = self.exec_cfg.commission_per_side_pct + self.exec_cfg.slippage_per_side_pct
        return notional * rate

    def run(self, candidate_cls, max_daily_trades=2, cooldown=2):
        data = self.data
        n = data.n
        capital = 10000.0
        peak_capital = 10000.0
        max_dd_pct = 0.0
        trades = []
        active_pos = None
        last_exit_bar = 0
        daily_trades = defaultdict(int)

        for i in range(n):
            day_key = datetime.fromtimestamp(data.timestamps[i], tz=timezone.utc).strftime("%Y-%m-%d")
            bar_high = data.highs[i]
            bar_low = data.lows[i]
            bar_close = data.closes[i]
            curr_atr = data.atr_1h[i]

            if active_pos:
                entry = active_pos["entry"]
                side = active_pos["side"]
                tp1 = active_pos["tp1"]
                tp2 = active_pos["tp2"]
                pos_size = active_pos["size"]
                tp1_hit = active_pos.get("tp1_hit", False)
                closed = False
                exit_price = bar_close
                exit_reason = ""
                trade_pnl = 0.0

                if side == "BUY":
                    if not tp1_hit and bar_high >= tp1:
                        active_pos["tp1_hit"] = True
                        p1_pnl = (tp1 - entry) * (pos_size * 0.5)
                        cost = self._cost((entry + tp1) * (pos_size * 0.5))
                        active_pos["tp1_realized_pnl"] = p1_pnl - cost
                        active_pos["size"] = pos_size * 0.5
                        capital += active_pos["tp1_realized_pnl"]
                        tp1_hit = True
                    if tp1_hit:
                        trail = bar_close - 1.2 * curr_atr
                        if trail > active_pos["sl"]:
                            active_pos["sl"] = trail
                    hit_tp2 = bar_high >= tp2
                    hit_sl = bar_low <= active_pos["sl"]
                    if hit_tp2 and hit_sl:
                        hit_tp2 = False
                    if hit_tp2:
                        exit_price = tp2; exit_reason = "TP2"
                        rem_pnl = (tp2 - entry) * active_pos["size"]
                        cost = self._cost((entry + tp2) * active_pos["size"])
                        trade_pnl = active_pos.get("tp1_realized_pnl", 0.0) + (rem_pnl - cost)
                        closed = True
                    elif hit_sl:
                        exit_price = active_pos["sl"]
                        if tp1_hit:
                            exit_reason = "TRAILING_PROFIT"
                            rem_pnl = (active_pos["sl"] - entry) * active_pos["size"]
                            cost = self._cost((entry + active_pos["sl"]) * active_pos["size"])
                            trade_pnl = active_pos.get("tp1_realized_pnl", 0.0) + (rem_pnl - cost)
                        else:
                            exit_reason = "SL"
                            raw_pnl = (active_pos["sl"] - entry) * pos_size
                            cost = self._cost((entry + active_pos["sl"]) * pos_size)
                            trade_pnl = raw_pnl - cost
                        closed = True

                elif side == "SELL":
                    if not tp1_hit and bar_low <= tp1:
                        active_pos["tp1_hit"] = True
                        p1_pnl = (entry - tp1) * (pos_size * 0.5)
                        cost = self._cost((entry + tp1) * (pos_size * 0.5))
                        active_pos["tp1_realized_pnl"] = p1_pnl - cost
                        active_pos["size"] = pos_size * 0.5
                        capital += active_pos["tp1_realized_pnl"]
                        tp1_hit = True
                    if tp1_hit:
                        trail = bar_close + 1.2 * curr_atr
                        if trail < active_pos["sl"]:
                            active_pos["sl"] = trail
                    hit_tp2 = bar_low <= tp2
                    hit_sl = bar_high >= active_pos["sl"]
                    if hit_tp2 and hit_sl:
                        hit_tp2 = False
                    if hit_tp2:
                        exit_price = tp2; exit_reason = "TP2"
                        rem_pnl = (entry - tp2) * active_pos["size"]
                        cost = self._cost((entry + tp2) * active_pos["size"])
                        trade_pnl = active_pos.get("tp1_realized_pnl", 0.0) + (rem_pnl - cost)
                        closed = True
                    elif hit_sl:
                        exit_price = active_pos["sl"]
                        if tp1_hit:
                            exit_reason = "TRAILING_PROFIT"
                            rem_pnl = (entry - active_pos["sl"]) * active_pos["size"]
                            cost = self._cost((entry + active_pos["sl"]) * active_pos["size"])
                            trade_pnl = active_pos.get("tp1_realized_pnl", 0.0) + (rem_pnl - cost)
                        else:
                            exit_reason = "SL"
                            raw_pnl = (entry - active_pos["sl"]) * pos_size
                            cost = self._cost((entry + active_pos["sl"]) * pos_size)
                            trade_pnl = raw_pnl - cost
                        closed = True

                if closed:
                    if tp1_hit:
                        capital += (trade_pnl - active_pos.get("tp1_realized_pnl", 0.0))
                    else:
                        capital += trade_pnl
                    risk_amt = active_pos["risk_amount"]
                    r_mult = trade_pnl / risk_amt if risk_amt > 0 else 0.0
                    trades.append({
                        "id": active_pos["id"],
                        "day": day_key,
                        "side": side,
                        "entry": entry,
                        "exit": round(exit_price, 2),
                        "sl": active_pos["initial_sl"],
                        "tp1": tp1,
                        "tp2": tp2,
                        "reason": exit_reason,
                        "pnl": round(trade_pnl, 2),
                        "r_multiple": round(r_mult, 3),
                        "is_win": trade_pnl > 0,
                        "capital_after": round(capital, 2)
                    })
                    active_pos = None
                    last_exit_bar = i
                    if capital > peak_capital:
                        peak_capital = capital
                    dd = ((peak_capital - capital) / peak_capital) * 100.0 if peak_capital > 0 else 0.0
                    if dd > max_dd_pct:
                        max_dd_pct = dd

            if not active_pos:
                if daily_trades[day_key] >= max_daily_trades:
                    continue
                if (i - last_exit_bar) < cooldown:
                    continue
                sig = candidate_cls.evaluate(i, data, self.cfg.strategy)
                if sig:
                    side, sl_m, tp1_m, tp2_m = sig
                    daily_trades[day_key] += 1
                    entry_p = bar_close
                    sl_dist = max(sl_m * curr_atr, 0.002 * entry_p)
                    init_sl = round(entry_p - sl_dist, 2) if side == "BUY" else round(entry_p + sl_dist, 2)
                    tp1_p = round(entry_p + tp1_m * sl_dist, 2) if side == "BUY" else round(entry_p - tp1_m * sl_dist, 2)
                    tp2_p = round(entry_p + tp2_m * sl_dist, 2) if side == "BUY" else round(entry_p - tp2_m * sl_dist, 2)
                    risk_budget = capital * 0.0035
                    pos_sz = risk_budget / max(sl_dist, 1.0)
                    active_pos = {
                        "id": "t_" + str(i) + "_" + side,
                        "entry_bar": i,
                        "side": side,
                        "entry": entry_p,
                        "sl": init_sl,
                        "initial_sl": init_sl,
                        "tp1": tp1_p,
                        "tp2": tp2_p,
                        "risk_amount": risk_budget,
                        "size": pos_sz,
                        "tp1_hit": False,
                        "tp1_realized_pnl": 0.0
                    }

        tot = len(trades)
        if tot == 0:
            return {"trades_count": 0, "win_rate": 0.0, "profit_factor": 0.0,
                    "net_pnl": 0.0, "expectancy_r": 0.0, "avg_win_r": 0.0,
                    "avg_loss_r": 0.0, "max_dd_pct": 0.0, "max_loss_streak": 0, "trades": []}
        wins = [t for t in trades if t["is_win"]]
        losses = [t for t in trades if not t["is_win"]]
        wc = len(wins); lc = len(losses)
        gp = sum(t["pnl"] for t in wins)
        gl = abs(sum(t["pnl"] for t in losses))
        pf = gp / gl if gl > 0 else (99.9 if gp > 0 else 0.0)
        awr = sum(t["r_multiple"] for t in wins) / wc if wc > 0 else 0.0
        alr = sum(abs(t["r_multiple"]) for t in losses) / lc if lc > 0 else 0.0
        exp = (wc / tot) * awr - (lc / tot) * alr
        streak = 0; max_streak = 0
        for t in trades:
            if t["is_win"]: streak = 0
            else:
                streak += 1
                if streak > max_streak: max_streak = streak
        return {
            "trades_count": tot,
            "win_rate": round(wc / tot * 100.0, 2),
            "profit_factor": round(pf, 2),
            "net_pnl": round(gp - gl, 2),
            "expectancy_r": round(exp, 3),
            "avg_win_r": round(awr, 2),
            "avg_loss_r": round(alr, 2),
            "max_dd_pct": round(max_dd_pct, 2),
            "max_loss_streak": max_streak,
            "trades": trades
        }
