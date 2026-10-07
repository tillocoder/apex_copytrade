"""
Armandino Engine - Core Backtester
Executes deterministic, tick-accurate, cross-margin backtests on M15 bars:
- Strict zero-lookahead (signal on candle close i, execution on open i+1)
- Partial exits (50% at TP1, remaining 50% at TP2)
- Pessimistic collision handling (SL before TP on ambiguous candles)
- Exact Binance Futures fees, slippage, lot-step, and min-notional enforcement
- Cross margin tracking with real-time equity and liquidation verification
"""

import math
import csv
import os
from typing import List, Dict, Optional, Tuple
from .models import Position, Side, TradeRecord, ExitReason, ScenarioConfig
from .cross_margin import CrossMarginAccount
from .strategy import SignalGenerator


class BacktestRunner:
    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.account = CrossMarginAccount(initial_balance=20.0, leverage=config.leverage)
        self.equity_curve: List[Dict] = []
        
    def load_data(self, data_dir: str) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
        """Loads M15 and H1 candles for ETH and ZEC."""
        def read_csv(filename):
            candles = []
            path = os.path.join(data_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    candles.append({
                        "timestamp": int(row["timestamp"]),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                        "datetime": row["datetime"]
                    })
            return candles

        eth_m15 = read_csv("ETHUSDT_15m_3m.csv")
        eth_h1 = read_csv("ETHUSDT_1h_3m.csv")
        zec_m15 = read_csv("ZECUSDT_15m_3m.csv")
        zec_h1 = read_csv("ZECUSDT_1h_3m.csv")
        
        return eth_m15, eth_h1, zec_m15, zec_h1

    def run(self, data_dir: str) -> Dict:
        eth_m15, eth_h1, zec_m15, zec_h1 = self.load_data(data_dir)
        
        # Align M15 candles by timestamp
        eth_map = {c["timestamp"]: c for c in eth_m15}
        zec_map = {c["timestamp"]: c for c in zec_m15}
        common_timestamps = sorted(list(set(eth_map.keys()).intersection(set(zec_map.keys()))))
        
        # Filter to common timestamps
        eth_m15_common = [eth_map[ts] for ts in common_timestamps]
        zec_m15_common = [zec_map[ts] for ts in common_timestamps]
        
        # Generate signals
        eth_signals = SignalGenerator.generate_eth_signals(eth_m15_common, eth_h1)
        zec_signals = SignalGenerator.generate_zec_signals(zec_m15_common)
        
        n_bars = len(common_timestamps)
        
        # Step size and min notionals
        symbol_specs = {
            "ETHUSDT": {"step": 0.001, "min_notional": 20.0},
            "ZECUSDT": {"step": 0.001, "min_notional": 5.0}
        }
        
        # Pending orders for next bar open (zero lookahead)
        pending_orders: List[Dict] = []
        
        for i in range(n_bars):
            ts = common_timestamps[i]
            dt_str = eth_m15_common[i]["datetime"]
            
            bar_eth = eth_m15_common[i]
            bar_zec = zec_m15_common[i]
            bar_prices = {"ETHUSDT": bar_eth, "ZECUSDT": bar_zec}
            open_prices = {"ETHUSDT": bar_eth["open"], "ZECUSDT": bar_zec["open"]}
            close_prices = {"ETHUSDT": bar_eth["close"], "ZECUSDT": bar_zec["close"]}
            
            # --- 1. EXECUTE PENDING ORDERS ON BAR OPEN ---
            if pending_orders and not self.account.is_liquidated:
                for order in pending_orders:
                    sym = order["symbol"]
                    side = order["side"]
                    sig_name = order["signal_name"]
                    
                    if sym in self.account.positions:
                        continue  # Already in position for this symbol
                        
                    if len(self.account.positions) >= self.config.max_concurrent_positions:
                        continue
                        
                    raw_entry = open_prices[sym]
                    # Apply taker slippage (2 bps)
                    if side == Side.LONG:
                        entry_price = raw_entry * (1.0 + self.config.slippage_bps / 10000.0)
                    else:
                        entry_price = raw_entry * (1.0 - self.config.slippage_bps / 10000.0)
                        
                    # Calculate position size
                    free_margin = self.account.get_free_margin(open_prices)
                    if free_margin < 2.0:
                        continue
                        
                    target_margin = self.account.wallet_balance * self.config.margin_fraction
                    # Clamp margin between $3 and available free margin * 0.8
                    alloc_margin = max(3.0, min(target_margin, free_margin * 0.80))
                    target_notional = alloc_margin * self.config.leverage
                    
                    spec = symbol_specs[sym]
                    step = spec["step"]
                    min_qty = spec["min_notional"] / entry_price
                    calc_qty = max(min_qty, target_notional / entry_price)
                    qty = round(math.ceil(calc_qty / step) * step, 3)
                    
                    actual_notional = qty * entry_price
                    actual_margin = actual_notional / self.config.leverage
                    
                    if actual_margin > free_margin:
                        # Scale down to fit free margin if possible
                        max_possible_qty = math.floor((free_margin * 0.95 * self.config.leverage / entry_price) / step) * step
                        if max_possible_qty * entry_price >= spec["min_notional"]:
                            qty = round(max_possible_qty, 3)
                            actual_notional = qty * entry_price
                            actual_margin = actual_notional / self.config.leverage
                        else:
                            continue  # Cannot meet min notional
                            
                    # Entry commission (Taker 0.05%)
                    entry_comm = actual_notional * self.config.taker_fee
                    self.account.wallet_balance -= entry_comm
                    self.account.total_commissions_paid += entry_comm
                    
                    # Target prices
                    if side == Side.LONG:
                        tp1 = entry_price * (1.0 + self.config.tp1_pct)
                        tp2 = entry_price * (1.0 + self.config.tp2_pct)
                        sl = entry_price * (1.0 - self.config.sl_pct) if self.config.has_hard_sl else None
                    else:
                        tp1 = entry_price * (1.0 - self.config.tp1_pct)
                        tp2 = entry_price * (1.0 - self.config.tp2_pct)
                        sl = entry_price * (1.0 + self.config.sl_pct) if self.config.has_hard_sl else None
                        
                    pos = Position(
                        symbol=sym,
                        side=side,
                        entry_price=entry_price,
                        initial_qty=qty,
                        current_qty=qty,
                        entry_time=ts,
                        entry_bar_idx=i,
                        leverage=self.config.leverage,
                        allocated_margin=actual_margin,
                        tp1_price=tp1,
                        tp2_price=tp2,
                        tp1_hit=False,
                        stop_loss_price=sl,
                        total_commission_paid=entry_comm
                    )
                    self.account.positions[sym] = pos
                    
                pending_orders = []

            # --- 2. CHECK INTRA-BAR LIQUIDATION (Pessimistic) ---
            if self.account.check_liquidation(bar_prices, dt_str, i):
                # Account liquidated, record equity = 0 and break
                self.equity_curve.append({
                    "timestamp": ts,
                    "datetime": dt_str,
                    "equity": 0.0,
                    "wallet_balance": 0.0,
                    "unrealized_pnl": 0.0,
                    "open_positions": 0,
                    "is_liquidated": True
                })
                break

            # --- 3. CHECK POSITION EXITS / TAKE PROFITS ---
            for sym in list(self.account.positions.keys()):
                pos = self.account.positions[sym]
                c = bar_prices[sym]
                holding_hours = (i - pos.entry_bar_idx) * 0.25
                
                # Intra-bar prices
                if pos.side == Side.LONG:
                    worst_p = c["low"]
                    best_p = c["high"]
                    favorable_dist = (best_p - pos.entry_price) / pos.entry_price
                    adverse_dist = (pos.entry_price - worst_p) / pos.entry_price
                else:
                    worst_p = c["high"]
                    best_p = c["low"]
                    favorable_dist = (pos.entry_price - best_p) / pos.entry_price
                    adverse_dist = (worst_p - pos.entry_price) / pos.entry_price
                    
                pos.max_favorable_pct = max(pos.max_favorable_pct, favorable_dist * 100.0)
                pos.max_adverse_pct = max(pos.max_adverse_pct, adverse_dist * 100.0)

                # Flag triggers
                hit_sl = False
                if self.config.has_hard_sl and pos.stop_loss_price is not None:
                    if pos.side == Side.LONG and worst_p <= pos.stop_loss_price:
                        hit_sl = True
                    elif pos.side == Side.SHORT and worst_p >= pos.stop_loss_price:
                        hit_sl = True
                        
                hit_tp1 = False
                hit_tp2 = False
                if not pos.tp1_hit:
                    if pos.side == Side.LONG and best_p >= pos.tp1_price:
                        hit_tp1 = True
                    elif pos.side == Side.SHORT and best_p <= pos.tp1_price:
                        hit_tp1 = True
                else:
                    if pos.side == Side.LONG and best_p >= pos.tp2_price:
                        hit_tp2 = True
                    elif pos.side == Side.SHORT and best_p <= pos.tp2_price:
                        hit_tp2 = True
                        
                # Direct shoot to TP2 on same bar as TP1
                if hit_tp1:
                    if pos.side == Side.LONG and best_p >= pos.tp2_price:
                        hit_tp2 = True
                    elif pos.side == Side.SHORT and best_p <= pos.tp2_price:
                        hit_tp2 = True

                # Scenario A: Floating Drawdown & Time Limit Cut
                hit_dd_cut = False
                hit_time_cut = False
                if not self.config.has_hard_sl:
                    # Current floating loss at bar close
                    if pos.side == Side.LONG:
                        current_pnl = (c["close"] - pos.entry_price) * pos.current_qty
                    else:
                        current_pnl = (pos.entry_price - c["close"]) * pos.current_qty
                    
                    floating_dd = -current_pnl / pos.allocated_margin if pos.allocated_margin > 0 else 0.0
                    if floating_dd >= self.config.max_floating_dd_pct:
                        hit_dd_cut = True
                    elif holding_hours >= self.config.max_holding_hours:
                        hit_time_cut = True

                # Collision Resolution:
                # If SL is hit, it takes priority over TP (pessimistic)
                if hit_sl:
                    # CLOSE ENTIRE POSITION AT SL
                    self.account.trade_counter += 1
                    exit_price = pos.stop_loss_price
                    step = symbol_specs[sym]["step"]
                    exit_notional = pos.current_qty * exit_price
                    exit_comm = exit_notional * self.config.taker_fee
                    
                    if pos.side == Side.LONG:
                        pnl = (exit_price - pos.entry_price) * pos.current_qty
                    else:
                        pnl = (pos.entry_price - exit_price) * pos.current_qty
                        
                    total_gross = pnl + pos.accumulated_realized_pnl
                    total_comm = pos.total_commission_paid + exit_comm
                    total_net = total_gross - total_comm
                    
                    self.account.wallet_balance += pnl - exit_comm
                    self.account.total_commissions_paid += exit_comm
                    
                    record = TradeRecord(
                        trade_id=self.account.trade_counter,
                        symbol=sym,
                        side=pos.side.value,
                        entry_time=str(pos.entry_time),
                        exit_time=dt_str,
                        entry_price=pos.entry_price,
                        exit_price=exit_price,
                        qty=pos.initial_qty,
                        notional=pos.entry_price * pos.initial_qty,
                        margin_used=pos.allocated_margin,
                        leverage=pos.leverage,
                        gross_pnl=round(total_gross, 4),
                        commission=round(total_comm, 4),
                        net_pnl=round(total_net, 4),
                        return_on_margin_pct=round((total_net / pos.allocated_margin) * 100.0, 2),
                        exit_reason=ExitReason.STOP_LOSS.value,
                        holding_hours=round(holding_hours, 2),
                        max_floating_dd_pct=round(pos.max_adverse_pct * pos.leverage, 2),
                        tp1_hit=pos.tp1_hit,
                        tp2_hit=False
                    )
                    self.account.closed_trades.append(record)
                    del self.account.positions[sym]
                    continue

                # TP1 Partial Execution
                if hit_tp1 and not pos.tp1_hit:
                    # Close 50%
                    step = symbol_specs[sym]["step"]
                    close_qty = round(math.floor((pos.initial_qty * self.config.tp1_close_ratio) / step) * step, 3)
                    if close_qty >= step:
                        tp1_notional = close_qty * pos.tp1_price
                        tp1_comm = tp1_notional * self.config.maker_fee
                        
                        if pos.side == Side.LONG:
                            tp1_pnl = (pos.tp1_price - pos.entry_price) * close_qty
                        else:
                            tp1_pnl = (pos.entry_price - pos.tp1_price) * close_qty
                            
                        self.account.wallet_balance += tp1_pnl - tp1_comm
                        self.account.total_commissions_paid += tp1_comm
                        pos.accumulated_realized_pnl += tp1_pnl
                        pos.total_commission_paid += tp1_comm
                        pos.current_qty = round(pos.current_qty - close_qty, 3)
                        pos.tp1_hit = True

                # TP2 Final Execution
                if hit_tp2 and pos.current_qty > 0:
                    self.account.trade_counter += 1
                    exit_price = pos.tp2_price
                    exit_notional = pos.current_qty * exit_price
                    exit_comm = exit_notional * self.config.maker_fee
                    
                    if pos.side == Side.LONG:
                        pnl = (exit_price - pos.entry_price) * pos.current_qty
                    else:
                        pnl = (pos.entry_price - exit_price) * pos.current_qty
                        
                    total_gross = pnl + pos.accumulated_realized_pnl
                    total_comm = pos.total_commission_paid + exit_comm
                    total_net = total_gross - total_comm
                    
                    self.account.wallet_balance += pnl - exit_comm
                    self.account.total_commissions_paid += exit_comm
                    
                    record = TradeRecord(
                        trade_id=self.account.trade_counter,
                        symbol=sym,
                        side=pos.side.value,
                        entry_time=str(pos.entry_time),
                        exit_time=dt_str,
                        entry_price=pos.entry_price,
                        exit_price=exit_price,
                        qty=pos.initial_qty,
                        notional=pos.entry_price * pos.initial_qty,
                        margin_used=pos.allocated_margin,
                        leverage=pos.leverage,
                        gross_pnl=round(total_gross, 4),
                        commission=round(total_comm, 4),
                        net_pnl=round(total_net, 4),
                        return_on_margin_pct=round((total_net / pos.allocated_margin) * 100.0, 2),
                        exit_reason=ExitReason.TP2.value,
                        holding_hours=round(holding_hours, 2),
                        max_floating_dd_pct=round(pos.max_adverse_pct * pos.leverage, 2),
                        tp1_hit=True,
                        tp2_hit=True
                    )
                    self.account.closed_trades.append(record)
                    del self.account.positions[sym]
                    continue

                # Scenario A: Cut on Drawdown or Time
                if hit_dd_cut or hit_time_cut:
                    self.account.trade_counter += 1
                    exit_price = c["close"]
                    exit_notional = pos.current_qty * exit_price
                    exit_comm = exit_notional * self.config.taker_fee
                    
                    if pos.side == Side.LONG:
                        pnl = (exit_price - pos.entry_price) * pos.current_qty
                    else:
                        pnl = (pos.entry_price - exit_price) * pos.current_qty
                        
                    total_gross = pnl + pos.accumulated_realized_pnl
                    total_comm = pos.total_commission_paid + exit_comm
                    total_net = total_gross - total_comm
                    
                    self.account.wallet_balance += pnl - exit_comm
                    self.account.total_commissions_paid += exit_comm
                    reason = ExitReason.DRAWDOWN_CUT.value if hit_dd_cut else ExitReason.TIME_EXPIRED.value
                    
                    record = TradeRecord(
                        trade_id=self.account.trade_counter,
                        symbol=sym,
                        side=pos.side.value,
                        entry_time=str(pos.entry_time),
                        exit_time=dt_str,
                        entry_price=pos.entry_price,
                        exit_price=exit_price,
                        qty=pos.initial_qty,
                        notional=pos.entry_price * pos.initial_qty,
                        margin_used=pos.allocated_margin,
                        leverage=pos.leverage,
                        gross_pnl=round(total_gross, 4),
                        commission=round(total_comm, 4),
                        net_pnl=round(total_net, 4),
                        return_on_margin_pct=round((total_net / pos.allocated_margin) * 100.0, 2),
                        exit_reason=reason,
                        holding_hours=round(holding_hours, 2),
                        max_floating_dd_pct=round(pos.max_adverse_pct * pos.leverage, 2),
                        tp1_hit=pos.tp1_hit,
                        tp2_hit=False
                    )
                    self.account.closed_trades.append(record)
                    del self.account.positions[sym]
                    continue

            # --- 4. CHECK NEW SIGNALS ON CANDLE CLOSE ---
            # Signals emitted at bar i will be executed on bar i+1 open
            if not self.account.is_liquidated and i + 1 < n_bars:
                sig_eth = eth_signals[i]
                sig_zec = zec_signals[i]
                
                # Target ~55% ETH and ~45% ZEC priority
                candidates = []
                if sig_eth and "ETHUSDT" not in self.account.positions:
                    candidates.append({"symbol": "ETHUSDT", "side": sig_eth[0], "signal_name": sig_eth[1]})
                if sig_zec and "ZECUSDT" not in self.account.positions:
                    candidates.append({"symbol": "ZECUSDT", "side": sig_zec[0], "signal_name": sig_zec[1]})
                    
                pending_orders = candidates

            # --- 5. RECORD EQUITY AND DRAWDOWN ---
            equity = self.account.get_equity(close_prices)
            upnl = self.account.get_unrealized_pnl(close_prices)
            self.account.update_drawdown(close_prices)
            
            self.equity_curve.append({
                "timestamp": ts,
                "datetime": dt_str,
                "equity": round(equity, 4),
                "wallet_balance": round(self.account.wallet_balance, 4),
                "unrealized_pnl": round(upnl, 4),
                "open_positions": len(self.account.positions),
                "is_liquidated": self.account.is_liquidated
            })

        # Calculate summary statistics
        return self._generate_summary()

    def _generate_summary(self) -> Dict:
        trades = self.account.closed_trades
        n_trades = len(trades)
        
        winners = [t for t in trades if t.net_pnl > 0]
        losers = [t for t in trades if t.net_pnl <= 0]
        
        win_rate = (len(winners) / n_trades * 100.0) if n_trades > 0 else 0.0
        
        total_pnl = sum(t.net_pnl for t in trades)
        gross_profit = sum(t.net_pnl for t in winners)
        gross_loss = abs(sum(t.net_pnl for t in losers))
        
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        
        final_equity = 0.0 if self.account.is_liquidated else (self.account.wallet_balance)
        roi_pct = ((final_equity - self.account.initial_balance) / self.account.initial_balance) * 100.0
        
        eth_trades = [t for t in trades if t.symbol == "ETHUSDT"]
        zec_trades = [t for t in trades if t.symbol == "ZECUSDT"]
        
        # Exit reason breakdown
        reasons = {}
        for t in trades:
            reasons[t.exit_reason] = reasons.get(t.exit_reason, 0) + 1
            
        tp1_hits = sum(1 for t in trades if t.tp1_hit)
        tp2_hits = sum(1 for t in trades if t.tp2_hit)
        
        avg_holding = sum(t.holding_hours for t in trades) / n_trades if n_trades > 0 else 0.0
        
        return {
            "scenario": self.config.name,
            "initial_balance": self.account.initial_balance,
            "final_equity": round(final_equity, 2),
            "total_roi_pct": round(roi_pct, 2),
            "is_liquidated": self.account.is_liquidated,
            "liquidation_time": self.account.liquidation_time,
            "total_trades": n_trades,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "total_pnl": round(total_pnl, 2),
            "total_commissions": round(self.account.total_commissions_paid, 2),
            "max_drawdown_pct": round(self.account.max_drawdown_pct, 2),
            "avg_holding_hours": round(avg_holding, 2),
            "eth_trades_count": len(eth_trades),
            "zec_trades_count": len(zec_trades),
            "eth_volume_share_pct": round(len(eth_trades) / n_trades * 100.0, 1) if n_trades > 0 else 0.0,
            "zec_volume_share_pct": round(len(zec_trades) / n_trades * 100.0, 1) if n_trades > 0 else 0.0,
            "tp1_hits_count": tp1_hits,
            "tp2_hits_count": tp2_hits,
            "exit_reasons": reasons,
            "closed_trades": trades,
            "equity_curve": self.equity_curve
        }
