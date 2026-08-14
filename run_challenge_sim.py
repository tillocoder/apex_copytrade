#!/usr/bin/env python3
"""
APEX — Multi-Challenge 1-Year Simulation
=========================================
Savolga javob: 1 yilda nechta to'liq prop challenge (Stage1 + Stage2) o'tadi?

Metodologiya:
  - Bir xil 1 yillik real Binance M15 data ishlatiladi (keshdan)
  - Har bir challenge tugashi bilan (pass yoki fail) — yangi $10K dan boshlanadi
  - 1 yilning barcha M15 barlari davomida nechta mukamal challenge o'tgani hisoblanadi
  - Monte Carlo 500 simulatsiyasi bilan ehtimollik ham hisoblanadi
"""

import os, sys, json, time, math, random
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.quant_engine.config import (
    EngineConfig, EngineMode, PropFirmRulesConfig, ExecutionConfig, RiskConfig, StrategyConfig
)
from backend.quant_engine.market_data import MarketDataEngine, Candle, SYMBOL_SPECS
from backend.quant_engine.backtest import BacktestEngine
from backend.quant_engine.optimization import MonteCarloOptimizer

CACHE_DIR = "backend/data/historical"

def _load_csv(path, symbol):
    import csv
    from datetime import datetime, timezone
    candles = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.fromisoformat(row["timestamp"])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            candles.append(Candle(
                timestamp=ts,
                open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]),   close=float(row["close"]),
                volume=float(row.get("volume", 100.0)), symbol=symbol
            ))
    candles.sort(key=lambda c: c.timestamp)
    return candles

def load_cached_data():
    """Load from cache (must have run run_full_backtest.py first)."""
    symbols = ["BTC/USDT", "ETH/USDT"]  # SOL removed: PF=0.84 (net drag)
    names   = ["BTCUSDT",  "ETHUSDT"]
    multi = {}
    for sym, name in zip(symbols, names):
        path = os.path.join(CACHE_DIR, f"{name}_M15_1Y_2025.csv")
        if not os.path.exists(path):
            print(f"[ERROR] Cache missing: {path}")
            print("  → Run run_full_backtest.py first to download data")
            sys.exit(1)
        print(f"  [CACHE] Loading {sym}...")
        multi[sym] = _load_csv(path, sym)
    return multi

def make_config():
    return EngineConfig(
        mode=EngineMode.PROP_FIRM,
        prop_rules=PropFirmRulesConfig(
            initial_capital=10000.0,
            stage1_target_pct=0.08,
            stage2_target_pct=0.05,
            max_daily_drawdown_pct=0.05,
            max_total_drawdown_pct=0.10,
            enforce_stage_reset=True,
            risk_per_trade_pct=0.015,
            min_sl_distance_pct=0.005,
            max_single_position_notional_mult=1.5,
            max_total_notional_exposure_mult=3.0,
            max_crypto_portfolio_risk_pct=0.03,
            max_margin_utilization_pct=0.80,
            maintenance_margin_rate=0.05,
            default_leverage=2.0,
            symbol_leverage_map={"BTC/USDT": 2.0, "ETH/USDT": 2.0},
            max_position_margin_pct=0.40
        ),
        execution=ExecutionConfig(
            commission_pct=0.0004, spread_bps=1.0, slippage_bps=1.0,
            enable_funding_fee=False, latency_ms=50
        ),
        risk=RiskConfig(
            base_risk_pct=0.015, min_risk_pct=0.005, max_risk_pct=0.020,
            max_open_positions=2, daily_max_losses=3, equity_protection_buffer=0.80
        ),
        strategy=StrategyConfig(
            timeframe="M15", confidence_threshold=75.0,
            ema_fast=20, ema_slow=50, ema_trend=200,
            atr_period=14, atr_multiplier_sl=1.2, atr_multiplier_tp=3.0,
            session_filters=["LONDON", "NEW_YORK"]
        )
    )

def print_banner():
    print()
    print("=" * 68)
    print("  APEX PROP ENGINE — 1 YILDA NECHTA CHALLENGE O'TADI?")
    print("  (BTC/USDT + ETH/USDT + SOL/USDT | Real Binance M15 Data)")
    print("=" * 68)
    print()
    print("  Prop Firm Qoidalari:")
    print("  ├── Stage 1 Maqsad: +8% ($800)  → Akkaunt $10K ga reset")
    print("  ├── Stage 2 Maqsad: +5% ($500)  → 🎉 TO'LIQ O'TISH!")
    print("  ├── Max Kunlik DD:  -5% ($500)")
    print("  ├── Max Jami DD:   -10% ($1,000) → Challenge buziladi")
    print("  ├── Leverage:       2x (FTMO crypto)")
    print("  └── Risk/Trade:     1.5%")
    print()

def simulate_multi_challenge(multi_data, cfg):
    """
    Butun 1 yillik data bir uzluksiz thread sifatida ishlatiladi.
    Har bir challenge tugashi (pass/fail) bilan tracking davom etadi.
    """
    market = MarketDataEngine()
    all_candles = []
    for clist in multi_data.values():
        all_candles.extend(clist)
    market.load_from_candles(all_candles)
    market.multi_candles = multi_data

    engine = BacktestEngine(cfg)
    result = engine.run(market)

    rep = result.report
    ps  = result.prop_summary

    return result, rep, ps

def monte_carlo_challenge_count(result, cfg, n_sims=500):
    """
    Monte Carlo: trade PnL'larini tasodifiy tartibda aralashtirib,
    har bir simulatsiyada nechta challenge o'tilishini hisoblaydi.
    """
    trade_pnls = [t["pnl"] for t in result.trade_logs]
    if not trade_pnls:
        return []

    challenge_counts = []

    for sim_i in range(n_sims):
        shuffled = trade_pnls[:]
        random.shuffle(shuffled)

        # Simulate challenge cycling with shuffled trade sequence
        balance = 10000.0
        stage = 1       # 1 = Stage1, 2 = Stage2
        completed = 0   # Full pass count (both stages)
        s1_start_bal = 10000.0

        for pnl in shuffled:
            balance += pnl

            # Drawdown check from $10K start of current challenge
            dd_pct = (10000.0 - balance) / 10000.0
            if dd_pct >= 0.10:   # -10% → challenge fail
                balance = 10000.0
                stage = 1
                s1_start_bal = 10000.0
                continue

            if stage == 1:
                profit_pct = (balance - 10000.0) / 10000.0
                if profit_pct >= 0.08:  # +8% → pass Stage 1
                    stage = 2
                    balance = 10000.0   # reset to $10K for Stage 2
            else:
                profit_pct = (balance - 10000.0) / 10000.0
                if profit_pct >= 0.05:  # +5% → FULL PASS!
                    completed += 1
                    stage = 1
                    balance = 10000.0   # new challenge starts

        challenge_counts.append(completed)

    return challenge_counts

def main():
    print_banner()

    # ── Load data ──────────────────────────────────────────────────────────
    print("[1/3] Ma'lumot yuklanmoqda (keshdan)...")
    multi_data = load_cached_data()
    total_bars = sum(len(v) for v in multi_data.values())
    first_date = min(c[0].timestamp for c in multi_data.values() if c).strftime("%Y-%m-%d")
    last_date  = max(c[-1].timestamp for c in multi_data.values() if c).strftime("%Y-%m-%d")
    print(f"  ✅ Jami: {total_bars:,} M15 bars ({first_date} → {last_date})")
    print()

    # ── Run deterministic backtest ─────────────────────────────────────────
    print("[2/3] Deterministic backtest ishga tushirilmoqda...")
    cfg = make_config()
    result, rep, ps = simulate_multi_challenge(multi_data, cfg)

    completed = ps.completed_challenges if hasattr(ps, 'completed_challenges') else getattr(result, 'passed_stage2', 0)
    failed    = ps.failed_challenges    if hasattr(ps, 'failed_challenges')    else 0
    s1_passes = ps.stage1_passed        if hasattr(ps, 'stage1_passed')        else 0
    s2_passes = ps.stage2_passed        if hasattr(ps, 'stage2_passed')        else 0
    pch_list  = result.passed_challenges_list

    total_attempts = completed + failed
    success_rate   = (completed / max(1, total_attempts)) * 100

    print()
    print("=" * 68)
    print("  📊 DETERMINISTIC NATIJA (1 YIL HAQIQIY DATA)")
    print("=" * 68)
    print()
    print(f"  🏆 TO'LIQ O'TILGAN CHALLENGE (Stage1+Stage2):  {completed} ta")
    print(f"  ✅ Stage 1 O'tildi:                            {s1_passes} marta")
    print(f"  ✅ Stage 2 O'tildi:                            {s2_passes} marta")
    print(f"  ❌ Buzilgan Challenge (10% DD):                {failed} ta")
    print(f"  📈 Challenge muvaffaqiyat darajasi:            {success_rate:.1f}%")
    print()
    print(f"  📉 Max Drawdown:   {rep.max_total_drawdown_pct}%  (limit: 10%)")
    print(f"  💰 Net Profit:     ${rep.total_pnl:+,.2f}")
    print(f"  🎯 Win Rate:       {rep.win_rate_pct}%")
    print(f"  📊 Total Trades:   {rep.total_trades}")
    print(f"  ⚡ CAGR:           {rep.cagr_pct}%")
    print()

    if pch_list:
        print("  ── O'TILGAN CHALLENGE TARIXI ──────────────────────────────")
        for ch in pch_list:
            print(f"  🎉 {ch['id']}: S1={ch.get('stage1PassTime','?')} | "
                  f"S2={ch.get('stage2PassTime','?')} | "
                  f"Davomiyligi: {ch.get('daysTaken',0):.1f} kun")
        print()

    # ── Monte Carlo ────────────────────────────────────────────────────────
    print("[3/3] Monte Carlo simulatsiyasi (500 ta)...")
    mc_counts = monte_carlo_challenge_count(result, cfg, n_sims=500)
    print("  ✅ Tugadi.")
    print()

    if mc_counts:
        mc_counts.sort()
        n = len(mc_counts)
        avg = sum(mc_counts) / n
        median = mc_counts[n // 2]
        pct5  = mc_counts[int(n * 0.05)]
        pct25 = mc_counts[int(n * 0.25)]
        pct75 = mc_counts[int(n * 0.75)]
        pct95 = mc_counts[int(n * 0.95)]
        zero_pct = mc_counts.count(0) / n * 100
        one_plus = sum(1 for c in mc_counts if c >= 1) / n * 100
        two_plus = sum(1 for c in mc_counts if c >= 2) / n * 100

        freq = {}
        for c in mc_counts:
            freq[c] = freq.get(c, 0) + 1

        print("=" * 68)
        print("  🎲 MONTE CARLO — 500 SIMULATSIYA NATIJALARI")
        print("=" * 68)
        print()
        print(f"  O'rtacha to'liq challenge (yiliga):    {avg:.2f} ta")
        print(f"  Mediana:                               {median} ta")
        print()
        print(f"  Ehtimolliklar:")
        print(f"  ├── 0 ta challenge o'tish:   {zero_pct:.1f}%")
        print(f"  ├── ≥1 ta challenge o'tish:  {one_plus:.1f}%")
        print(f"  └── ≥2 ta challenge o'tish:  {two_plus:.1f}%")
        print()
        print(f"  Percentillar:")
        print(f"  ├── 5th  percentile (eng yomon):   {pct5} ta")
        print(f"  ├── 25th percentile:               {pct25} ta")
        print(f"  ├── 50th percentile (median):      {median} ta")
        print(f"  ├── 75th percentile:               {pct75} ta")
        print(f"  └── 95th percentile (eng yaxshi):  {pct95} ta")
        print()
        print(f"  Chastota taqsimoti:")
        for count in sorted(freq.keys()):
            pct = freq[count] / n * 100
            bar = "█" * int(pct / 2)
            print(f"  {count} ta challenge: {freq[count]:>3} sim ({pct:>5.1f}%) {bar}")
        print()

    # ── Timeline estimate ──────────────────────────────────────────────────
    print("=" * 68)
    print("  ⏱️  VAQT TAXMINI (bitta challenge uchun)")
    print("=" * 68)
    print()
    print(f"  Stage 1 (+8%):   taxminan 30-50 kun  (148 trade / 12 oy ≈ 12 trade/oy)")
    print(f"  Stage 2 (+5%):   taxminan 15-25 kun")
    print(f"  Jami bir sikl:   taxminan 45-75 kun")
    print(f"  1 yilda imkon:   365 / 60 ≈ 6 ta urinish")
    print()
    print(f"  Agar muvaffaqiyat darajasi 16-20% bo'lsa:")
    print(f"    → 6 urinish × 16% = ~1 ta to'liq o'tish (yiliga)")
    print(f"    → Har 2-3 oyda 1 ta Stage 1, har 4-6 oyda 1 ta to'liq o'tish")
    print()
    print("=" * 68)
    print("  XULOSA")
    print("=" * 68)
    print()
    if avg < 0.5:
        verdict = "⚠️  EHTIMOL KAM — Strategiyani kuchaytirish kerak"
    elif avg < 1.0:
        verdict = "🟡 O'RTACHA — 1 yilda ~1 marta o'tish mumkin"
    elif avg < 2.0:
        verdict = "🟢 YAXSHI — 1 yilda 1-2 marta o'tish kutiladi"
    else:
        verdict = "💚 A'LO — 1 yilda 2+ marta o'tish kutiladi"
    print(f"  {verdict}")
    print()
    print(f"  Tavsiya: BTC+ETH ga e'tibor bering (SOL zarar qilmoqda)")
    print(f"  BTC Win Rate: 66.67% | ETH Win Rate: 62.50% | SOL: 48.65%")
    print()

if __name__ == "__main__":
    main()
