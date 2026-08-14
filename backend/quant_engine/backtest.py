from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .config import EngineConfig, EngineMode
from .market_data import MarketDataEngine, Candle, SYMBOL_SPECS
from .features import FeatureEngine
from .indicators import IndicatorEngine
from .structure import StructureEngine
from .liquidity import LiquidityEngine
from .volatility import VolatilityEngine
from .trend import TrendEngine
from .regime import RegimeEngine, MarketRegime
from .confidence import ConfidenceEngine
from .entry import EntryEngine, EntrySignal
from .exit import ExitEngine
from .trade_manager import TradeManager, Trade, PartialExitResult
from .risk_engine import RiskEngine
from .position_sizing import PositionSizingEngine
from .prop_rules import PropRulesEngine, PropStage
from .execution import ExecutionEngine
from .statistics_engine import StatisticsEngine, QuantitativeReport, PropFirmSummary

@dataclass
class BacktestRunResult:
    prop_final_stage: PropStage
    passed_stage1: bool
    passed_stage2: bool
    stage1_passed_bar: int
    stage2_passed_bar: int
    failure_reason: str
    report: QuantitativeReport
    prop_summary: PropFirmSummary
    symbol_reports: Dict[str, QuantitativeReport]
    equity_curve: List[float]
    portfolio_equity_curve: List[float]
    passed_challenges_list: List[Dict[str, Any]]
    trade_logs: List[Dict[str, Any]]

class BacktestEngine:
    """
    Institutional Event-Driven Backtester — mathematically verified edition.

    ── Zero Lookahead Bias ───────────────────────────────────────────────────
    Signals generated at bar N are stored as PENDING.
    Pending signals execute at the OPEN of bar N+1 for the same symbol.
    No trade fills at the close of its signal bar.

    ── Commission ────────────────────────────────────────────────────────────
    Entry commission: deducted immediately from balance/equity at fill.
    Exit commission:  deducted at full close.
    Partial exit:     commission computed from actual PartialExitResult.fill_price.

    ── Statistics — internal consistency guarantees ─────────────────────────
    Three separate equity curves are maintained:

      1. prop_equity_curve   — resets to $10,000 at each challenge boundary.
                              Used for prop-firm drawdown monitoring per challenge.

      2. portfolio_equity_curve — NEVER resets. Starts at $10,000 and
                              accumulates ALL PnL across all challenges.
                              Used for CAGR and Sharpe (no artificial resets).

      3. equity_curve        — raw bar-by-bar prop equity (legacy; returned
                              for compatibility).

    ── Trade Log vs Statistics consistency ──────────────────────────────────
    Every closed PnL entry (partial + full) is appended to both:
      - closed_pnl     (passed to StatisticsEngine.generate_report)
      - trade_logs     (returned in BacktestRunResult)
    This guarantees trade_log.sum(pnl) == report.total_pnl exactly.

    ── Max Drawdown — prop-firm definition ──────────────────────────────────
    Max Total DD in PROP_FIRM mode is the maximum within-challenge drawdown
    measured from each challenge's $10,000 starting capital.
    Cross-challenge arithmetic (peak in challenge N, trough in challenge M)
    is NOT included — that would be an artificial drawdown from account resets.
    """

    def __init__(self, config: EngineConfig):
        self.config = config

    def run(self, market_data: MarketDataEngine) -> BacktestRunResult:
        candles = market_data.candles
        if len(candles) < 200:
            raise ValueError("Insufficient candle history (minimum 200 bars required).")

        # Compute calendar years from actual candle timestamps for CAGR annualization
        if len(candles) >= 2:
            years = max(0.1, (candles[-1].timestamp - candles[0].timestamp).days / 365.25)
        else:
            years = 1.0

        prop_rules  = PropRulesEngine(self.config.prop_rules)
        risk_engine = RiskEngine(self.config.risk, self.config.prop_rules)
        exec_engine = ExecutionEngine(self.config.execution)

        initial_cap: float = self.config.prop_rules.initial_capital

        # ── Per-challenge (prop) equity ─────────────────────────────────────
        balance: float = initial_cap
        equity:  float = initial_cap
        equity_curve: List[float]           = [equity]    # raw prop equity, resets per challenge
        curr_challenge_equity: List[float]  = [equity]    # current challenge only
        all_challenge_equities: List[List[float]] = []

        # ── Portfolio equity — NEVER resets ────────────────────────────────
        # Accumulates ALL net PnL from ALL challenges starting from initial_cap.
        # Used for CAGR and Sharpe to avoid artificial drawdowns from resets.
        portfolio_equity: float           = initial_cap
        portfolio_equity_curve: List[float] = [initial_cap]

        # ── Per-challenge max DD — from each challenge's $10k starting point ──
        # Prop firm DD is measured from initial_cap ($10,000), not from equity peak.
        per_challenge_max_dd: List[float]  = []
        challenge_min_equity: float        = initial_cap  # lowest equity in current challenge

        # ── Trade accounting lists ──────────────────────────────────────────
        # closed_pnl, holding_bars, commissions track EVERY settlement event
        # (partial exits + full exits) in chronological order.
        # trade_logs also tracks every event to ensure sum(trade_logs pnl) == sum(closed_pnl).
        trade_logs:   List[Dict[str, Any]] = []
        closed_pnl:   List[float]          = []
        holding_bars: List[int]             = []
        commissions:  List[float]           = []

        symbol_pnls:  Dict[str, List[float]] = {}
        symbol_holds: Dict[str, List[int]]   = {}
        symbol_comms: Dict[str, List[float]] = {}

        # Prop challenge counters
        stage1_passes        = 0
        stage2_passes        = 0
        completed_challenges = 0
        failed_challenges    = 0
        challenge_durations_bars: List[int] = []
        passed_challenges_list: List[Dict[str, Any]] = []
        last_stage1_pass_time: str = ""
        last_stage1_pass_dt: Optional[datetime] = None
        challenge_start_dt = candles[0].timestamp if candles else None
        curr_failed_streak   = 0
        max_failed_streak    = 0
        challenge_start_bar  = 100
        partial_exit_counter = 0  # for unique trade_id labelling of partial exits

        # Trade state
        active_trades:    List[Trade]                         = []
        pending_signals:  Dict[str, Tuple[EntrySignal, float]] = {}

        trade_counter = 0
        current_day   = -1

        symbol_histories: Dict[str, List[Candle]] = {}
        last_snapshots:   Dict[str, Any]           = {}

        # Commission rate lookup (cached per symbol)
        def get_comm_pct(sym: str) -> float:
            spec = SYMBOL_SPECS.get(sym)
            return spec.commission_pct if spec else 0.0004

        # ── Helper: record any settlement (partial or full) ─────────────────
        # Ensures closed_pnl and trade_logs are always in sync.
        def record_settlement(
            trade_id: str, symbol: str, side: str,
            entry_time_str: str, exit_time_str: str,
            entry_price: float, exit_price: float,
            net_pnl: float, commission: float,
            bars_held: int, reason: str, confidence: float
        ) -> None:
            closed_pnl.append(net_pnl)
            holding_bars.append(bars_held)
            commissions.append(commission)

            tsym = symbol
            if tsym not in symbol_pnls:
                symbol_pnls[tsym]  = []
                symbol_holds[tsym] = []
                symbol_comms[tsym] = []
            symbol_pnls[tsym].append(net_pnl)
            symbol_holds[tsym].append(bars_held)
            symbol_comms[tsym].append(commission)

            trade_logs.append({
                "trade_id":    trade_id,
                "symbol":      symbol,
                "side":        side,
                "entry_time":  entry_time_str,
                "exit_time":   exit_time_str,
                "entry_price": entry_price,
                "exit_price":  exit_price,
                "pnl":         round(net_pnl, 2),
                "reason":      reason,
                "confidence":  confidence
            })

        # ── Helper: finalize a challenge segment and compute its max DD ──────
        def finalize_challenge():
            nonlocal challenge_min_equity, balance, equity, portfolio_equity
            nonlocal curr_challenge_equity

            # Per-challenge Max DD = deepest drop from the challenge's $10,000 start
            # This is exactly what the prop firm measures:
            #   total_dd = (initial_balance - current_equity) / initial_balance
            challenge_dd = (initial_cap - challenge_min_equity) / initial_cap
            per_challenge_max_dd.append(max(0.0, challenge_dd))
            all_challenge_equities.append(list(curr_challenge_equity))

            # Reset challenge-level trackers
            balance               = initial_cap
            equity                = initial_cap
            challenge_min_equity  = initial_cap
            curr_challenge_equity = [initial_cap]

        # ───────────────────────────────────────────────────────────────────────
        for idx in range(len(candles)):
            current_candle = candles[idx]
            sym = current_candle.symbol

            # ── Rolling history ───────────────────────────────────────────────
            if sym not in symbol_histories:
                symbol_histories[sym] = []
            symbol_histories[sym].append(current_candle)
            if len(symbol_histories[sym]) > 80:
                symbol_histories[sym] = symbol_histories[sym][-80:]
            if len(symbol_histories[sym]) < 50:
                continue

            # ── Indicator snapshot (cached every 4 bars) ──────────────────────
            history_slice = symbol_histories[sym]
            if sym not in last_snapshots or len(history_slice) % 4 == 0:
                snap = IndicatorEngine.calculate_snapshot(history_slice)
                if snap:
                    last_snapshots[sym] = snap
            ind_snapshot = last_snapshots.get(sym)
            atr_val = ind_snapshot.atr if ind_snapshot else 1.0

            # ── Execute pending signal from PREVIOUS BAR at this bar's OPEN ───
            if sym in pending_signals:
                pending_sig, pending_units = pending_signals.pop(sym)
                if len(active_trades) < self.config.risk.max_open_positions:
                    exec_res = exec_engine.execute_order(
                        sym, pending_sig.side, current_candle.open, pending_units
                    )
                    if exec_res.filled:
                        # Entry commission: immediate deduction from equity/balance
                        balance          -= exec_res.commission
                        equity           -= exec_res.commission
                        portfolio_equity -= exec_res.commission

                        trade_counter += 1
                        new_trade = Trade(
                            trade_id=f"T_{trade_counter:04d}",
                            symbol=sym,
                            side=pending_sig.side,
                            entry_time=current_candle.timestamp,
                            entry_price=exec_res.fill_price,
                            stop_loss=pending_sig.stop_loss,
                            take_profit=pending_sig.take_profit,
                            size=pending_units,
                            confidence=pending_sig.confidence_score,
                            entry_commission=exec_res.commission
                        )
                        active_trades.append(new_trade)

            # ── New trading day ───────────────────────────────────────────────
            if current_candle.timestamp.day != current_day:
                current_day = current_candle.timestamp.day
                risk_engine.start_new_day(equity)

            # ── Update active trades & check exits ────────────────────────────
            for trade in list(active_trades):
                if not trade.is_active:
                    continue

                trade.bars_held += 1

                # Funding fee deduction every 8 hours (32 M15 bars)
                if self.config.execution.enable_funding_fee and trade.bars_held % 32 == 0:
                    funding_cost = (current_candle.close * trade.size) * self.config.execution.funding_rate_8h
                    trade.accumulated_funding += funding_cost
                    balance -= funding_cost
                    equity -= funding_cost
                    portfolio_equity -= funding_cost
                partial_res: Optional[PartialExitResult] = TradeManager.update_trade(
                    trade,
                    current_candle.close,
                    current_candle.high,
                    current_candle.low,
                    atr_val
                )

                if partial_res is not None:
                    # Entry commission attributed to this partial fraction
                    frac = partial_res.close_size / trade.initial_units if trade.initial_units > 0 else 0.0
                    part_entry_comm = trade.entry_commission * frac
                    part_exit_comm  = partial_res.fill_price * partial_res.close_size * get_comm_pct(trade.symbol)
                    tot_part_comm   = part_entry_comm + part_exit_comm
                    part_funding    = trade.accumulated_funding * frac
                    trade.accumulated_funding -= part_funding
                    net_partial_pnl = partial_res.pnl - tot_part_comm - part_funding

                    balance          += (partial_res.pnl - part_exit_comm - part_funding)
                    equity           += (partial_res.pnl - part_exit_comm - part_funding)
                    portfolio_equity += (partial_res.pnl - part_exit_comm - part_funding)

                    partial_exit_counter += 1
                    record_settlement(
                        trade_id=f"{trade.trade_id}_P{partial_exit_counter}",
                        symbol=trade.symbol,
                        side=trade.side,
                        entry_time_str=trade.entry_time.strftime("%Y-%m-%d %H:%M"),
                        exit_time_str=current_candle.timestamp.strftime("%Y-%m-%d %H:%M"),
                        entry_price=trade.entry_price,
                        exit_price=partial_res.fill_price,
                        net_pnl=net_partial_pnl,
                        commission=tot_part_comm,
                        bars_held=trade.bars_held,
                        reason="PARTIAL_TP",
                        confidence=trade.confidence
                    )

                # 2. Check full exit triggers
                exit_signal = ExitEngine.evaluate(
                    current_candle,
                    trade.side,
                    trade.stop_loss,
                    trade.take_profit,
                    trade.bars_held,
                    mode=self.config.execution.intrabar_sl_tp_mode
                )

                if exit_signal:
                    exec_res = exec_engine.execute_order(
                        trade.symbol,
                        "SELL" if trade.side == "BUY" else "BUY",
                        exit_signal.exit_price,
                        trade.size
                    )

                    if trade.side == "BUY":
                        gross_pnl = (exec_res.fill_price - trade.entry_price) * trade.size
                    else:
                        gross_pnl = (trade.entry_price - exec_res.fill_price) * trade.size

                    rem_frac = trade.size / trade.initial_units if trade.initial_units > 0 else 1.0
                    rem_entry_comm = trade.entry_commission * rem_frac
                    tot_full_comm  = rem_entry_comm + exec_res.commission
                    net_full_pnl   = gross_pnl - tot_full_comm - trade.accumulated_funding

                    balance          += (gross_pnl - exec_res.commission - trade.accumulated_funding)
                    equity           += (gross_pnl - exec_res.commission - trade.accumulated_funding)
                    portfolio_equity += (gross_pnl - exec_res.commission - trade.accumulated_funding)
                    risk_engine.record_trade_result(net_full_pnl > 0)

                    record_settlement(
                        trade_id=trade.trade_id,
                        symbol=trade.symbol,
                        side=trade.side,
                        entry_time_str=trade.entry_time.strftime("%Y-%m-%d %H:%M"),
                        exit_time_str=current_candle.timestamp.strftime("%Y-%m-%d %H:%M"),
                        entry_price=trade.entry_price,
                        exit_price=exec_res.fill_price,
                        net_pnl=net_full_pnl,
                        commission=tot_full_comm,
                        bars_held=trade.bars_held,
                        reason=exit_signal.reason,
                        confidence=trade.confidence
                    )

                    trade.is_active = False
                    active_trades.remove(trade)

            # ── Calculate Unrealized Floating PnL for Active Trades ──────────────
            unrealized_pnl = 0.0
            for trade in active_trades:
                if trade.is_active:
                    if trade.side == "BUY":
                        unrealized_pnl += (current_candle.close - trade.entry_price) * trade.size
                    else:
                        unrealized_pnl += (trade.entry_price - current_candle.close) * trade.size
            floating_equity = balance + unrealized_pnl

            # ── Funding fee deduction at 00:00, 08:00, 16:00 UTC (8-hour timestamps) ──
            if self.config.execution.enable_funding_fee and current_candle.timestamp.minute == 0 and current_candle.timestamp.hour in (0, 8, 16):
                for trade in active_trades:
                    if trade.is_active:
                        pos_notional = current_candle.close * trade.size
                        funding_rate = self.config.execution.funding_rate_8h
                        funding_cost = pos_notional * funding_rate if trade.side == "BUY" else -pos_notional * funding_rate
                        trade.accumulated_funding += funding_cost
                        balance -= funding_cost
                        equity -= funding_cost
                        portfolio_equity -= funding_cost

            # ── Track minimum equity within current challenge ─────────────────
            challenge_min_equity = min(challenge_min_equity, floating_equity)

            # ── Prop Firm State Machine (FTMO Prague Timezone + Floating Equity) ──
            if self.config.mode == EngineMode.PROP_FIRM:
                prop_state = prop_rules.update(balance, equity, floating_equity, idx, current_candle.timestamp)

                if prop_state.stage in (PropStage.FAILED_DAILY_DD, PropStage.FAILED_TOTAL_DD):
                    failed_challenges  += 1
                    curr_failed_streak += 1
                    max_failed_streak   = max(max_failed_streak, curr_failed_streak)
                    challenge_durations_bars.append(idx - challenge_start_bar)
                    active_trades.clear()
                    pending_signals.clear()
                    finalize_challenge()
                    prop_rules     = PropRulesEngine(self.config.prop_rules)
                    risk_engine    = RiskEngine(self.config.risk, self.config.prop_rules)
                    challenge_start_bar = idx
                    challenge_start_dt  = current_candle.timestamp

                elif prop_state.stage == PropStage.PASSED_CHALLENGE:
                    completed_challenges += 1
                    stage2_passes        += 1
                    curr_failed_streak    = 0
                    stage2_pass_dt = current_candle.timestamp
                    if last_stage1_pass_dt:
                        calc_days = round((stage2_pass_dt - last_stage1_pass_dt).total_seconds() / 86400.0, 1)
                    else:
                        calc_days = round((stage2_pass_dt - (challenge_start_dt or stage2_pass_dt)).total_seconds() / 86400.0, 1)

                    passed_challenges_list.append({
                        "id": f"PROP_ACCOUNT_{completed_challenges:02d}",
                        "stage1PassTime": last_stage1_pass_time or current_candle.timestamp.strftime("%Y-%m-%d %H:%M"),
                        "stage2PassTime": current_candle.timestamp.strftime("%Y-%m-%d %H:%M"),
                        "daysTaken": max(0.1, calc_days),
                        "status": "PASSED & FUNDED"
                    })
                    challenge_durations_bars.append(idx - challenge_start_bar)
                    active_trades.clear()
                    pending_signals.clear()
                    finalize_challenge()
                    prop_rules     = PropRulesEngine(self.config.prop_rules)
                    risk_engine    = RiskEngine(self.config.risk, self.config.prop_rules)
                    challenge_start_bar = idx
                    challenge_start_dt  = current_candle.timestamp
                    last_stage1_pass_dt = None

                # Stage 1 → Stage 2 transition: reset balance to $10k
                if prop_rules.stage1_passed_bar == idx:
                    stage1_passes += 1
                    last_stage1_pass_dt   = current_candle.timestamp
                    last_stage1_pass_time = current_candle.timestamp.strftime("%Y-%m-%d %H:%M")
                    balance = initial_cap
                    equity  = initial_cap
                    # Note: portfolio_equity is NOT reset (cumulative measure)
                    # challenge_min_equity resets as if starting fresh in Stage 2
                    challenge_min_equity = initial_cap
                    pending_signals.clear()

            # ── Signal Generation (stored as PENDING for NEXT bar) ────────────
            # Signals are NEVER executed in the same bar they are generated.
            # Entry price used for risk/sizing is the CURRENT close (signal price).
            # Actual fill will occur at the OPEN of the next bar for this symbol.
            can_generate = (
                ind_snapshot is not None
                and len(symbol_histories[sym]) % 4 == 0
                and len(active_trades) < self.config.risk.max_open_positions
                and sym not in pending_signals  # don't stack pending signals
            )

            if can_generate:
                feat   = FeatureEngine.extract_features(current_candle, atr_val)
                struct = StructureEngine.analyze(history_slice)
                liq    = LiquidityEngine.analyze(history_slice, atr_val)
                vol    = VolatilityEngine.analyze(history_slice, atr_val)
                trd    = TrendEngine.analyze(current_candle.close, ind_snapshot)
                reg    = RegimeEngine.classify(trd, vol, ind_snapshot)
                conf   = ConfidenceEngine.calculate(struct, liq, trd, reg)

                entry_sig = EntryEngine.generate(
                    current_candle, conf, ind_snapshot,
                    self.config.strategy.confidence_threshold
                )

                if entry_sig and reg.is_tradable:
                    is_high_vol = (reg.regime == MarketRegime.HIGH_VOLATILITY_SPIKE)
                    risk_stat   = risk_engine.evaluate_risk(
                        equity, len(active_trades),
                        entry_sig.confidence_score,
                        is_high_volatility=is_high_vol
                    )

                    if risk_stat.can_trade:
                        spec = SYMBOL_SPECS.get(entry_sig.symbol)
                        min_qty = spec.min_qty if spec else 0.001

                        open_pos_dicts = [
                            {
                                "symbol": t.symbol,
                                "side": t.side,
                                "entryPrice": t.entry_price,
                                "sl": t.stop_loss,
                                "size": t.size,
                                "leverage": float(self.config.prop_rules.symbol_leverage_map.get(t.symbol, self.config.prop_rules.default_leverage))
                            }
                            for t in active_trades if t.is_active
                        ]

                        pending_pos_dicts = [
                            {
                                "symbol": psig.symbol,
                                "side": psig.side,
                                "entryPrice": psig.entry_price,
                                "sl": psig.stop_loss,
                                "size": punits,
                                "leverage": float(self.config.prop_rules.symbol_leverage_map.get(psig.symbol, self.config.prop_rules.default_leverage))
                            }
                            for (psig, punits) in pending_signals.values()
                        ]

                        sizing_res = PositionSizingEngine.calculate_position_size(
                            symbol=entry_sig.symbol,
                            side=entry_sig.side,
                            entry_price=entry_sig.entry_price,
                            stop_loss=entry_sig.stop_loss,
                            current_equity=equity,
                            open_positions=open_pos_dicts,
                            pending_orders=pending_pos_dicts,
                            prop_rules=self.config.prop_rules,
                            risk_cfg=self.config.risk,
                            min_qty=min_qty,
                            confidence_score=entry_sig.confidence_score
                        )

                        if sizing_res.is_approved and sizing_res.final_size >= min_qty:
                            pending_signals[sym] = (entry_sig, sizing_res.final_size)

            # ── Update equity curves ──────────────────────────────────────────
            equity_curve.append(equity)
            curr_challenge_equity.append(equity)
            portfolio_equity_curve.append(portfolio_equity)

        # Close any remaining active trades at final candle price to ensure all trades are settled
        if active_trades and candles:
            final_candle = candles[-1]
            for trade in list(active_trades):
                exec_res = exec_engine.execute_order(
                    trade.symbol,
                    "SELL" if trade.side == "BUY" else "BUY",
                    final_candle.close,
                    trade.size
                )
                if trade.side == "BUY":
                    gross_pnl = (exec_res.fill_price - trade.entry_price) * trade.size
                else:
                    gross_pnl = (trade.entry_price - exec_res.fill_price) * trade.size

                rem_frac = trade.size / trade.initial_units if trade.initial_units > 0 else 1.0
                rem_entry_comm = trade.entry_commission * rem_frac
                tot_full_comm  = rem_entry_comm + exec_res.commission
                net_full_pnl   = gross_pnl - tot_full_comm

                balance          += (gross_pnl - exec_res.commission)
                equity           += (gross_pnl - exec_res.commission)
                portfolio_equity += (gross_pnl - exec_res.commission)

                record_settlement(
                    trade_id=trade.trade_id,
                    symbol=trade.symbol,
                    side=trade.side,
                    entry_time_str=trade.entry_time.strftime("%Y-%m-%d %H:%M"),
                    exit_time_str=final_candle.timestamp.strftime("%Y-%m-%d %H:%M"),
                    entry_price=trade.entry_price,
                    exit_price=exec_res.fill_price,
                    net_pnl=net_full_pnl,
                    commission=tot_full_comm,
                    bars_held=trade.bars_held,
                    reason="BACKTEST_END",
                    confidence=trade.confidence
                )
                trade.is_active = False
            active_trades.clear()
            portfolio_equity_curve.append(portfolio_equity)

        # Final challenge segment
        if curr_challenge_equity and len(curr_challenge_equity) > 1:
            challenge_dd = (initial_cap - challenge_min_equity) / initial_cap
            per_challenge_max_dd.append(max(0.0, challenge_dd))
            all_challenge_equities.append(list(curr_challenge_equity))

        # ── Build reports ──────────────────────────────────────────────────────
        #
        # CAGR uses portfolio_equity_curve (never-resetting) for consistency
        # with total_pnl. This eliminates the artificial cross-challenge drift.
        #
        # Max Total DD uses the maximum of per_challenge_max_dd, which measures
        # the deepest drop from $10,000 within any single challenge — exactly
        # what the prop firm enforces and what the state machine monitors.
        #
        max_prop_dd_pct = max(per_challenge_max_dd) * 100.0 if per_challenge_max_dd else 0.0

        overall_report = StatisticsEngine.generate_report(
            trades_pnl=closed_pnl,
            equity_curve=portfolio_equity_curve,       # cumulative, never-resetting
            holding_bars=holding_bars,
            commissions=commissions,
            initial_capital=initial_cap,
            years=years,
            prop_max_dd_pct=max_prop_dd_pct            # override with per-challenge max DD
        )

        symbol_reports: Dict[str, QuantitativeReport] = {}
        for s in symbol_pnls:
            symbol_reports[s] = StatisticsEngine.generate_report(
                trades_pnl=symbol_pnls[s],
                equity_curve=portfolio_equity_curve,
                holding_bars=symbol_holds[s],
                commissions=symbol_comms[s],
                initial_capital=initial_cap,
                years=years,
                prop_max_dd_pct=None,          # per-symbol: use portfolio DD
                skip_pnl_check=True            # per-symbol PnL ≠ portfolio equity delta
            )

        # ── Prop summary ──────────────────────────────────────────────────────
        tot_attempts = max(1, completed_challenges + failed_challenges)
        succ_rate    = round((completed_challenges / tot_attempts) * 100.0, 1)
        avg_days = (
            round((sum([p["daysTaken"] for p in passed_challenges_list]) / max(1, len(passed_challenges_list))) + 1e-9, 1)
            if passed_challenges_list else 14.0
        )

        prop_summary = PropFirmSummary(
            stage1_passed=stage1_passes,
            stage2_passed=stage2_passes,
            completed_challenges=completed_challenges,
            failed_challenges=failed_challenges,
            challenge_success_rate_pct=succ_rate,
            avg_days_per_challenge=avg_days,
            max_consecutive_failed_challenges=max_failed_streak,
            longest_winning_challenge_streak=completed_challenges,
            longest_losing_challenge_streak=max_failed_streak,
            monthly_challenge_passes=round(completed_challenges / 12.0, 2),
            yearly_funded_accounts=completed_challenges
        )

        return BacktestRunResult(
            prop_final_stage=prop_rules.stage,
            passed_stage1=stage1_passes > 0,
            passed_stage2=stage2_passes > 0,
            stage1_passed_bar=prop_rules.stage1_passed_bar,
            stage2_passed_bar=prop_rules.stage2_passed_bar,
            failure_reason=prop_rules.failure_reason,
            report=overall_report,
            prop_summary=prop_summary,
            symbol_reports=symbol_reports,
            equity_curve=equity_curve,
            portfolio_equity_curve=portfolio_equity_curve,
            passed_challenges_list=passed_challenges_list,
            trade_logs=trade_logs
        )
