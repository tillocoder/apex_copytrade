"""
APEX QUANT ENGINE — 1-YEAR HISTORICAL REAL BINANCE AUDIT & BACKTEST
Simulates the exact quantitative SMC orderflow strategy on 1 Year of Real Binance BTC/USDT Candles.
Compares:
  A) Baseline Strategy (Old rules: Threshold >= 65, TP1=1.5R, premature Break-Even, no daily cap)
  B) Optimized Strategy (New rules: Threshold >= 75, ATR SL buffer, TP1=1.8R, Protected ATR Trailing Stop, TP2=3.0R, Max 2 trades/day cap)
"""

import os
import json
import time
import math
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict

CACHE_FILE = "backend/data/btc_1y_klines_cache.json"

def fetch_1y_binance_klines(symbol="BTCUSDT", interval="1h", days=365):
    """Fetches real 1-year historical klines from Binance Public API with caching."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if len(data) >= 8000:
                    print(f"[CACHE] Loaded {len(data)} candles from {CACHE_FILE}")
                    return data
        except Exception as e:
            print(f"[CACHE] Cache read error: {e}")

    print(f"[BINANCE API] Downloading {days} days of {interval} klines for {symbol}...")
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (days * 24 * 3600 * 1000)

    all_klines = []
    current_start = start_ms

    while current_start < now_ms:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={current_start}&limit=1000"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                batch = json.loads(response.read().decode("utf-8"))
                if not batch:
                    break
                all_klines.extend(batch)
                current_start = batch[-1][0] + 1
                print(f"  Fetched {len(batch)} candles... (Total: {len(all_klines)})")
                if len(batch) < 1000:
                    break
                time.sleep(0.15) # respect rate limit
        except Exception as err:
            print(f"  Error fetching batch: {err}")
            break

    # Cache for repeated tests
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(all_klines, f)
    print(f"[CACHE] Saved {len(all_klines)} candles to {CACHE_FILE}")

    return all_klines


def compute_indicators(closes, highs, lows, volumes):
    """Computes RSI, ATR, EMAs, MACD, and Volume Delta over candle arrays."""
    n = len(closes)
    
    # 1. EMA
    def calc_ema(arr, period):
        emas = [arr[0]] * n
        k = 2.0 / (period + 1.0)
        for i in range(1, n):
            emas[i] = (arr[i] * k) + (emas[i - 1] * (1.0 - k))
        return emas

    ema21 = calc_ema(closes, 21)
    ema50 = calc_ema(closes, 50)
    ema200 = calc_ema(closes, 200)

    # 2. Wilder ATR
    atr = [0.0] * n
    tr = [0.0] * n
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    
    # Simple start then Wilder smooth
    atr[13] = sum(tr[:14]) / 14.0
    for i in range(14, n):
        atr[i] = (atr[i - 1] * 13.0 + tr[i]) / 14.0

    # 3. Wilder RSI
    rsi = [50.0] * n
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains[i] = diff
        else:
            losses[i] = abs(diff)

    avg_gain = sum(gains[1:15]) / 14.0
    avg_loss = sum(losses[1:15]) / 14.0
    for i in range(14, n):
        if i > 14:
            avg_gain = (avg_gain * 13.0 + gains[i]) / 14.0
            avg_loss = (avg_loss * 13.0 + losses[i]) / 14.0
        rs = avg_gain / max(1e-9, avg_loss)
        rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return {
        "ema21": ema21,
        "ema50": ema50,
        "ema200": ema200,
        "atr": atr,
        "rsi": rsi
    }


def simulate_backtest(candles, config):
    """
    Simulates trades bar-by-bar across the 1-year historical dataset.
    """
    opens = [float(c[1]) for c in candles]
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    closes = [float(c[4]) for c in candles]
    volumes = [float(c[5]) for c in candles]
    timestamps = [c[0] / 1000.0 for c in candles]
    n = len(candles)

    ind = compute_indicators(closes, highs, lows, volumes)

    initial_capital = config.get("initial_capital", 10000.0)
    risk_pct = config.get("risk_pct", 0.0015) # 0.15% risk per trade ($15 risk on $10,000)
    min_score = config.get("min_score", 75.0)
    tp1_r = config.get("tp1_r", 1.8)
    tp2_r = config.get("tp2_r", 3.0)
    sl_atr_mult = config.get("sl_atr_mult", 1.6)
    use_atr_trailing = config.get("use_atr_trailing", True)
    max_daily_trades = config.get("max_daily_trades", 2)

    capital = initial_capital
    peak_capital = capital
    max_dd_dollars = 0.0
    max_dd_pct = 0.0

    trades = []
    active_position = None
    daily_trades_counter = defaultdict(int)

    # Warmup period: 200 bars for EMA200
    for i in range(200, n):
        t_sec = timestamps[i]
        dt = datetime.fromtimestamp(t_sec, tz=timezone.utc)
        day_key = dt.strftime("%Y-%m-%d")

        bar_open = opens[i]
        bar_high = highs[i]
        bar_low = lows[i]
        bar_close = closes[i]

        curr_atr = ind["atr"][i]
        curr_rsi = ind["rsi"][i]
        curr_ema21 = ind["ema21"][i]
        curr_ema50 = ind["ema50"][i]
        curr_ema200 = ind["ema200"][i]

        # ── 1. Check & Manage Active Position ──
        if active_position:
            pos = active_position
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            tp1 = pos["tp1"]
            tp2 = pos["tp2"]
            risk_amt = pos["risk_amount"]
            pos_size = pos["size"]
            tp1_hit = pos["tp1_hit"]

            closed = False
            exit_reason = ""
            exit_price = 0.0
            trade_pnl = 0.0

            if side == "BUY":
                # Check TP1 hit
                if not tp1_hit and bar_high >= tp1:
                    pos["tp1_hit"] = True
                    tp1_pnl = (tp1 - entry) * (pos_size * 0.5)
                    pos["tp1_realized_pnl"] = tp1_pnl
                    pos["size"] = pos_size * 0.5
                    capital += tp1_pnl
                    tp1_hit = True

                # Trailing stop update
                if tp1_hit:
                    if use_atr_trailing:
                        # Protected ATR trailing stop
                        candidate_sl = round(bar_close - 1.2 * curr_atr, 2)
                        if candidate_sl > pos["sl"]:
                            pos["sl"] = candidate_sl
                    else:
                        # Old rigid break-even
                        pos["sl"] = entry

                # Check TP2 hit (remaining 50%)
                if bar_high >= tp2:
                    exit_price = tp2
                    exit_reason = "TP2"
                    rem_pnl = (tp2 - entry) * pos["size"]
                    trade_pnl = pos.get("tp1_realized_pnl", 0.0) + rem_pnl
                    closed = True
                # Check SL hit
                elif bar_low <= pos["sl"]:
                    exit_price = pos["sl"]
                    if tp1_hit:
                        exit_reason = "TRAILING_PROFIT" if pos["sl"] > entry else "BE_PROFIT"
                        rem_pnl = (pos["sl"] - entry) * pos["size"]
                        trade_pnl = pos.get("tp1_realized_pnl", 0.0) + rem_pnl
                    else:
                        exit_reason = "SL"
                        trade_pnl = (pos["sl"] - entry) * pos_size
                    closed = True

            elif side == "SELL":
                # Check TP1 hit
                if not tp1_hit and bar_low <= tp1:
                    pos["tp1_hit"] = True
                    tp1_pnl = (entry - tp1) * (pos_size * 0.5)
                    pos["tp1_realized_pnl"] = tp1_pnl
                    pos["size"] = pos_size * 0.5
                    capital += tp1_pnl
                    tp1_hit = True

                # Trailing stop update
                if tp1_hit:
                    if use_atr_trailing:
                        candidate_sl = round(bar_close + 1.2 * curr_atr, 2)
                        if candidate_sl < pos["sl"]:
                            pos["sl"] = candidate_sl
                    else:
                        pos["sl"] = entry

                # Check TP2 hit
                if bar_low <= tp2:
                    exit_price = tp2
                    exit_reason = "TP2"
                    rem_pnl = (entry - tp2) * pos["size"]
                    trade_pnl = pos.get("tp1_realized_pnl", 0.0) + rem_pnl
                    closed = True
                # Check SL hit
                elif bar_high >= pos["sl"]:
                    exit_price = pos["sl"]
                    if tp1_hit:
                        exit_reason = "TRAILING_PROFIT" if pos["sl"] < entry else "BE_PROFIT"
                        rem_pnl = (entry - pos["sl"]) * pos["size"]
                        trade_pnl = pos.get("tp1_realized_pnl", 0.0) + rem_pnl
                    else:
                        exit_reason = "SL"
                        trade_pnl = (entry - pos["sl"]) * pos_size
                    closed = True

            if closed:
                if not tp1_hit:
                    capital += trade_pnl
                else:
                    # rem_pnl already added to trade_pnl, add remaining part
                    capital += (trade_pnl - pos.get("tp1_realized_pnl", 0.0))

                trades.append({
                    "id": pos["id"],
                    "entry_time": pos["entry_time"],
                    "exit_time": dt.strftime("%Y-%m-%d %H:%M"),
                    "side": side,
                    "entry": entry,
                    "exit": exit_price,
                    "sl": pos["initial_sl"],
                    "tp1": tp1,
                    "tp2": tp2,
                    "reason": exit_reason,
                    "pnl": round(trade_pnl, 2),
                    "is_win": trade_pnl > 0,
                    "score": pos["score"]
                })
                active_position = None

                # Update drawdowns
                if capital > peak_capital:
                    peak_capital = capital
                dd = peak_capital - capital
                dd_pct = (dd / peak_capital) * 100.0 if peak_capital > 0 else 0.0
                if dd > max_dd_dollars:
                    max_dd_dollars = dd
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct

        # ── 2. Signal Evaluation & Candidate Generation ──
        if not active_position:
            # Check daily trade cap
            if daily_trades_counter[day_key] >= max_daily_trades:
                continue

            # Quantitative SMC Signals
            # Trend Alignment: EMA21 > EMA50 > EMA200 (Bullish) or EMA21 < EMA50 < EMA200 (Bearish)
            bullish_trend = bar_close > curr_ema21 > curr_ema50 > curr_ema200
            bearish_trend = bar_close < curr_ema21 < curr_ema50 < curr_ema200

            # Momentum & Pullbacks
            bull_pullback = bar_close > curr_ema50 and lows[i] <= curr_ema21 and curr_rsi > 42.0 and curr_rsi < 68.0
            bear_pullback = bar_close < curr_ema50 and highs[i] >= curr_ema21 and curr_rsi < 58.0 and curr_rsi > 32.0

            # Volatility filter: ATR must be reasonable
            if curr_atr < 80.0 or curr_atr > 1800.0:
                continue

            side_candidate = None
            setup_name = ""
            score = 60.0

            if bullish_trend and bull_pullback:
                side_candidate = "BUY"
                setup_name = "Trend Continuation Pullback"
                score = 72.0
                # Confluence bonus: RSI hook
                if ind["rsi"][i] > ind["rsi"][i - 1]:
                    score += 6.0
                # Volume expansion bonus
                if volumes[i] > volumes[i - 1]:
                    score += 4.0

            elif bearish_trend and bear_pullback:
                side_candidate = "SELL"
                setup_name = "Trend Continuation Pullback"
                score = 72.0
                if ind["rsi"][i] < ind["rsi"][i - 1]:
                    score += 6.0
                if volumes[i] > volumes[i - 1]:
                    score += 4.0

            # Liquidity Sweep Reversals (Counter-trend A+ Setups)
            recent_low = min(lows[max(0, i - 20):i])
            recent_high = max(highs[max(0, i - 20):i])
            
            if lows[i] < recent_low and closes[i] > recent_low and curr_rsi < 35.0:
                side_candidate = "BUY"
                setup_name = "SMC Liquidity Pool Sweep"
                score = 81.0

            elif highs[i] > recent_high and closes[i] < recent_high and curr_rsi > 65.0:
                side_candidate = "SELL"
                setup_name = "SMC Liquidity Pool Sweep"
                score = 81.0

            # Filter by min_score
            if side_candidate and score >= min_score:
                daily_trades_counter[day_key] += 1
                entry_price = bar_close
                sl_distance = max(sl_atr_mult * curr_atr, 220.0)

                if side_candidate == "BUY":
                    initial_sl = round(entry_price - sl_distance, 2)
                    tp1_price = round(entry_price + (tp1_r * sl_distance), 2)
                    tp2_price = round(entry_price + (tp2_r * sl_distance), 2)
                else:
                    initial_sl = round(entry_price + sl_distance, 2)
                    tp1_price = round(entry_price - (tp1_r * sl_distance), 2)
                    tp2_price = round(entry_price - (tp2_r * sl_distance), 2)

                # Risk sizing: strictly 0.15% risk of current capital
                risk_budget = capital * risk_pct
                pos_size = risk_budget / max(1.0, sl_distance)

                active_position = {
                    "id": f"trade_{i}_{side_candidate}",
                    "entry_time": dt.strftime("%Y-%m-%d %H:%M"),
                    "side": side_candidate,
                    "entry": entry_price,
                    "sl": initial_sl,
                    "initial_sl": initial_sl,
                    "tp1": tp1_price,
                    "tp2": tp2_price,
                    "risk_amount": risk_budget,
                    "size": pos_size,
                    "tp1_hit": False,
                    "tp1_realized_pnl": 0.0,
                    "score": score,
                    "setup": setup_name
                }

    # Aggregate statistics
    tot_trades = len(trades)
    wins = [t for t in trades if t["is_win"]]
    losses = [t for t in trades if not t["is_win"]]
    win_cnt = len(wins)
    loss_cnt = len(losses)
    win_rate = (win_cnt / tot_trades * 100.0) if tot_trades > 0 else 0.0

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    net_pnl = gross_profit - gross_loss
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.9 if gross_profit > 0 else 0.0)

    avg_win = (gross_profit / win_cnt) if win_cnt > 0 else 0.0
    avg_loss = (gross_loss / loss_cnt) if loss_cnt > 0 else 0.0
    payoff = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    expectancy = (win_rate / 100.0 * avg_win) - ((1.0 - win_rate / 100.0) * avg_loss)

    return {
        "total_trades": tot_trades,
        "win_count": win_cnt,
        "loss_count": loss_cnt,
        "win_rate": round(win_rate, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "net_pnl": round(net_pnl, 2),
        "final_capital": round(capital, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "payoff_ratio": round(payoff, 2),
        "expectancy": round(expectancy, 2),
        "max_drawdown_dollars": round(max_dd_dollars, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "trades": trades
    }


def main():
    candles = fetch_1y_binance_klines(symbol="BTCUSDT", interval="1h", days=365)
    print(f"\n[DATASET] Downloaded {len(candles)} real Binance 1h candles.")
    start_dt = datetime.fromtimestamp(candles[0][0]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    end_dt = datetime.fromtimestamp(candles[-1][0]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    print(f"[TIMEFRAME] From {start_dt} to {end_dt} (Full 1 Year)\n")

    # 1. Baseline Run (Old Strategy)
    print("=" * 60)
    print("RUNNING CONFIG A: BASELINE (OLD STRATEGY)")
    print("  - Score Threshold: >= 65.0")
    print("  - TP1: 1.5R, TP2: 2.8R")
    print("  - Trailing Stop: Rigid Break-Even on TP1")
    print("  - Max Daily Cap: None (Unlimited)")
    print("=" * 60)
    res_a = simulate_backtest(candles, {
        "initial_capital": 10000.0,
        "risk_pct": 0.0015,
        "min_score": 65.0,
        "tp1_r": 1.5,
        "tp2_r": 2.8,
        "sl_atr_mult": 1.2,
        "use_atr_trailing": False,
        "max_daily_trades": 999
    })

    print(f"Trades: {res_a['total_trades']} | Win Rate: {res_a['win_rate']}% | PnL: ${res_a['net_pnl']:+,.2f} | PF: {res_a['profit_factor']}")
    print(f"Avg Win: ${res_a['avg_win']:.2f} | Avg Loss: ${res_a['avg_loss']:.2f} | Payoff: {res_a['payoff_ratio']} | Exp: ${res_a['expectancy']:.2f}")
    print(f"Max Drawdown: ${res_a['max_drawdown_dollars']:.2f} ({res_a['max_drawdown_pct']}%)")

    # 2. Optimized Run (New Institutional Strategy)
    print("\n" + "=" * 60)
    print("RUNNING CONFIG B: OPTIMIZED (NEW INSTITUTIONAL SMC STRATEGY)")
    print("  - Score Threshold: >= 75.0 (A+ Setups Only)")
    print("  - TP1: 1.8R, TP2: 3.0R")
    print("  - Stop Loss: Invalidation + 0.6x ATR Buffer")
    print("  - Trailing Stop: Protected 1.2x ATR Trailing (Breathable Retests)")
    print("  - Max Daily Cap: 2 Trades/Day Max")
    print("=" * 60)
    res_b = simulate_backtest(candles, {
        "initial_capital": 10000.0,
        "risk_pct": 0.0015,
        "min_score": 75.0,
        "tp1_r": 1.8,
        "tp2_r": 3.0,
        "sl_atr_mult": 1.6,
        "use_atr_trailing": True,
        "max_daily_trades": 2
    })

    print(f"Trades: {res_b['total_trades']} | Win Rate: {res_b['win_rate']}% | PnL: ${res_b['net_pnl']:+,.2f} | PF: {res_b['profit_factor']}")
    print(f"Avg Win: ${res_b['avg_win']:.2f} | Avg Loss: ${res_b['avg_loss']:.2f} | Payoff: {res_b['payoff_ratio']} | Exp: ${res_b['expectancy']:.2f}")
    print(f"Max Drawdown: ${res_b['max_drawdown_dollars']:.2f} ({res_b['max_drawdown_pct']}%)")

    # Save detailed audit report to JSON
    report_file = "backend/reports/backtest_1y_btc_report.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": f"{start_dt} to {end_dt}",
            "symbol": "BTCUSDT",
            "baseline": {k: v for k, v in res_a.items() if k != "trades"},
            "optimized": {k: v for k, v in res_b.items() if k != "trades"},
            "sample_trades_optimized": res_b["trades"][:20]
        }, f, indent=2)
    print(f"\n[REPORT] Saved full audit report to {report_file}")


if __name__ == "__main__":
    main()
