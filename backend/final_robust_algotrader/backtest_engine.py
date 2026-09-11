"""
Event-Driven Backtester Engine with Out-Of-Sample and Walk-Forward Splits.
"""
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime, timezone

from .config import AlgoTraderConfig
from .market_data import MarketDataEngine
from .signals import SignalEngine
from .risk_engine import RiskEngine
from .execution import ExecutionEngine

class BacktestEngine:
    def __init__(self, config: AlgoTraderConfig, data: MarketDataEngine):
        self.cfg = config
        self.data = data
        self.signals = SignalEngine(config.strategy, data)
        self.risk = RiskEngine(config.risk, config.prop_firm)
        self.exec = ExecutionEngine(config.execution)

    def run(self, start_bar: int = 200, end_bar: int = None) -> Dict[str, Any]:
        if end_bar is None:
            end_bar = self.data.n

        capital = self.cfg.prop_firm.initial_capital
        peak_capital = capital
        max_dd_pct = 0.0

        trades = []
        active_pos = None
        daily_trades = defaultdict(int)
        last_exit_bar = -999
        curr_day = ""

        for i in range(start_bar, end_bar):
            dt = datetime.fromtimestamp(self.data.timestamps[i], tz=timezone.utc)
            day_key = dt.strftime("%Y-%m-%d")

            if day_key != curr_day:
                curr_day = day_key
                self.risk.reset_day(capital)

            bar_open = self.data.opens[i]
            bar_high = self.data.highs[i]
            bar_low = self.data.lows[i]
            bar_close = self.data.closes[i]
            curr_atr = self.data.atr_1h[i]

            # 1. Manage active position
            if active_pos:
                pos = active_pos
                side = pos["side"]
                entry = pos["entry"]
                sl = pos["sl"]
                tp1 = pos["tp1"]
                tp2 = pos["tp2"]
                pos_size = pos["size"]
                tp1_hit = pos["tp1_hit"]

                closed = False
                exit_reason = ""
                exit_price = 0.0
                trade_pnl = 0.0

                if side == "BUY":
                    if not tp1_hit and bar_high >= tp1:
                        pos["tp1_hit"] = True
                        p1_pnl = (tp1 - entry) * (pos_size * 0.5)
                        cost = self.exec.compute_cost((entry + tp1) * (pos_size * 0.5))
                        pos["tp1_realized_pnl"] = p1_pnl - cost
                        pos["size"] = pos_size * 0.5
                        capital += pos["tp1_realized_pnl"]
                        tp1_hit = True

                    if tp1_hit:
                        c_sl = round(bar_close - self.cfg.strategy.trailing_atr_multiplier * curr_atr, 2)
                        if c_sl > pos["sl"]: pos["sl"] = c_sl

                    hit_tp2 = (bar_high >= tp2)
                    hit_sl = (bar_low <= pos["sl"])

                    if hit_tp2 and hit_sl:
                        if self.cfg.execution.conservative_intra_bar_sl_first: hit_tp2 = False
                        else: hit_sl = False

                    if hit_tp2:
                        exit_price = tp2
                        exit_reason = "TP2"
                        rem_pnl = (tp2 - entry) * pos["size"]
                        cost = self.exec.compute_cost((entry + tp2) * pos["size"])
                        trade_pnl = pos.get("tp1_realized_pnl", 0.0) + (rem_pnl - cost)
                        closed = True
                    elif hit_sl:
                        exit_price = pos["sl"]
                        if tp1_hit:
                            exit_reason = "TRAILING_PROFIT" if pos["sl"] > entry else "BE_PROFIT"
                            rem_pnl = (pos["sl"] - entry) * pos["size"]
                            cost = self.exec.compute_cost((entry + pos["sl"]) * pos["size"])
                            trade_pnl = pos.get("tp1_realized_pnl", 0.0) + (rem_pnl - cost)
                        else:
                            exit_reason = "SL"
                            raw_pnl = (pos["sl"] - entry) * pos_size
                            cost = self.exec.compute_cost((entry + pos["sl"]) * pos_size)
                            trade_pnl = raw_pnl - cost
                        closed = True

                elif side == "SELL":
                    if not tp1_hit and bar_low <= tp1:
                        pos["tp1_hit"] = True
                        p1_pnl = (entry - tp1) * (pos_size * 0.5)
                        cost = self.exec.compute_cost((entry + tp1) * (pos_size * 0.5))
                        pos["tp1_realized_pnl"] = p1_pnl - cost
                        pos["size"] = pos_size * 0.5
                        capital += pos["tp1_realized_pnl"]
                        tp1_hit = True

                    if tp1_hit:
                        c_sl = round(bar_close + self.cfg.strategy.trailing_atr_multiplier * curr_atr, 2)
                        if c_sl < pos["sl"]: pos["sl"] = c_sl

                    hit_tp2 = (bar_low <= tp2)
                    hit_sl = (bar_high >= pos["sl"])

                    if hit_tp2 and hit_sl:
                        if self.cfg.execution.conservative_intra_bar_sl_first: hit_tp2 = False
                        else: hit_sl = False

                    if hit_tp2:
                        exit_price = tp2
                        exit_reason = "TP2"
                        rem_pnl = (entry - tp2) * pos["size"]
                        cost = self.exec.compute_cost((entry + tp2) * pos["size"])
                        trade_pnl = pos.get("tp1_realized_pnl", 0.0) + (rem_pnl - cost)
                        closed = True
                    elif hit_sl:
                        exit_price = pos["sl"]
                        if tp1_hit:
                            exit_reason = "TRAILING_PROFIT" if pos["sl"] < entry else "BE_PROFIT"
                            rem_pnl = (entry - pos["sl"]) * pos["size"]
                            cost = self.exec.compute_cost((entry + pos["sl"]) * pos["size"])
                            trade_pnl = pos.get("tp1_realized_pnl", 0.0) + (rem_pnl - cost)
                        else:
                            exit_reason = "SL"
                            raw_pnl = (entry - pos["sl"]) * pos_size
                            cost = self.exec.compute_cost((entry + pos["sl"]) * pos_size)
                            trade_pnl = raw_pnl - cost
                        closed = True

                if closed:
                    if not tp1_hit: capital += trade_pnl
                    else: capital += (trade_pnl - pos.get("tp1_realized_pnl", 0.0))

                    risk_amt = pos["risk_amount"]
                    r_mult = trade_pnl / risk_amt if risk_amt > 0 else 0.0

                    trades.append({
                        "id": pos["id"],
                        "entry_bar": pos["entry_bar"],
                        "exit_bar": i,
                        "day": day_key,
                        "side": side,
                        "entry": entry,
                        "exit": exit_price,
                        "sl": pos["initial_sl"],
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

                    if capital > peak_capital: peak_capital = capital
                    dd_pct = ((peak_capital - capital) / peak_capital) * 100.0 if peak_capital > 0 else 0.0
                    if dd_pct > max_dd_pct: max_dd_pct = dd_pct

            # 2. Evaluate entry
            if not active_pos:
                if not self.risk.can_open_trade(capital, daily_trades[day_key]):
                    continue
                if (i - last_exit_bar) < self.cfg.strategy.cooldown_hours_after_exit:
                    continue

                sig = self.signals.evaluate(i)
                if sig:
                    side, sname, score, sl_m, tp1_m, tp2_m = sig
                    daily_trades[day_key] += 1
                    entry_p = bar_close
                    sl_dist = max(sl_m * curr_atr, 180.0)

                    init_sl = round(entry_p - sl_dist, 2) if side == "BUY" else round(entry_p + sl_dist, 2)
                    tp1_p = round(entry_p + (tp1_m * sl_dist), 2) if side == "BUY" else round(entry_p - (tp1_m * sl_dist), 2)
                    tp2_p = round(entry_p + (tp2_m * sl_dist), 2) if side == "BUY" else round(entry_p - (tp2_m * sl_dist), 2)

                    pos_sz = self.risk.calculate_position_size(capital, sl_dist)
                    risk_budget = capital * self.cfg.risk.base_risk_per_trade_pct

                    active_pos = {
                        "id": f"t_{i}_{side}",
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
        wins = [t for t in trades if t["is_win"]]
        losses = [t for t in trades if not t["is_win"]]
        win_cnt = len(wins)
        loss_cnt = len(losses)

        wr = (win_cnt / tot * 100.0) if tot > 0 else 0.0
        gp = sum(t["pnl"] for t in wins)
        gl = abs(sum(t["pnl"] for t in losses))
        net_pnl = gp - gl
        pf = (gp / gl) if gl > 0 else (99.9 if gp > 0 else 0.0)

        avg_win_r = sum(t["r_multiple"] for t in wins) / win_cnt if win_cnt > 0 else 0.0
        avg_loss_r = sum(abs(t["r_multiple"]) for t in losses) / loss_cnt if loss_cnt > 0 else 0.0
        exp_r = ((win_cnt / tot) * avg_win_r) - ((loss_cnt / tot) * avg_loss_r) if tot > 0 else 0.0

        curr_loss_streak = 0
        max_loss_streak = 0
        for t in trades:
            if t["is_win"]: curr_loss_streak = 0
            else:
                curr_loss_streak += 1
                if curr_loss_streak > max_loss_streak: max_loss_streak = curr_loss_streak

        return {
            "trades_count": tot,
            "win_rate": round(wr, 2),
            "profit_factor": round(pf, 2),
            "net_pnl": round(net_pnl, 2),
            "expectancy_r": round(exp_r, 3),
            "avg_win_r": round(avg_win_r, 2),
            "avg_loss_r": round(avg_loss_r, 2),
            "max_dd_pct": round(max_dd_pct, 2),
            "max_loss_streak": max_loss_streak,
            "trades": trades
        }
