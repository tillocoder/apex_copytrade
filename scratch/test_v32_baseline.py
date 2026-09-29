import os
import sys
import csv
import math
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

DATA_PATH = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"

def fast_ema(arr: List[float], period: int) -> List[float]:
    n = len(arr)
    res = [0.0] * n
    if n < period:
        return res
    mult = 2.0 / (period + 1.0)
    sma = sum(arr[:period]) / period
    for i in range(period - 1):
        res[i] = arr[i]
    res[period - 1] = sma
    cur = sma
    for i in range(period, n):
        cur = (arr[i] - cur) * mult + cur
        res[i] = cur
    return res

def precalculate_all_features(raw_candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    n = len(raw_candles)
    closes = [c["close"] for c in raw_candles]
    highs = [c["high"] for c in raw_candles]
    lows = [c["low"] for c in raw_candles]
    opens = [c["open"] for c in raw_candles]
    vols = [c["volume"] for c in raw_candles]
    times = [c["time"] for c in raw_candles]

    e9 = fast_ema(closes, 9)
    e21 = fast_ema(closes, 21)
    e50 = fast_ema(closes, 50)

    tr = [0.0] * n
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
    atr = [1.20] * n
    if n >= 15:
        init_atr = sum(tr[1:15]) / 14.0
        for i in range(15):
            atr[i] = init_atr
        cur_atr = init_atr
        for i in range(15, n):
            cur_atr = (cur_atr * 13.0 + tr[i]) / 14.0
            atr[i] = round(cur_atr, 2)

    m5_bars = []
    m15_bars = []
    cur_m5 = None
    cur_m15 = None
    m1_to_completed_m5 = [-1] * n
    m1_to_completed_m15 = [-1] * n

    for i in range(n):
        t = times[i]
        c = raw_candles[i]

        m5_t = (t // 300000) * 300000
        if cur_m5 is None:
            cur_m5 = {"time": m5_t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]}
        elif cur_m5["time"] == m5_t:
            cur_m5["high"] = max(cur_m5["high"], c["high"])
            cur_m5["low"] = min(cur_m5["low"], c["low"])
            cur_m5["close"] = c["close"]
            cur_m5["volume"] += c["volume"]
        else:
            m5_bars.append(cur_m5)
            cur_m5 = {"time": m5_t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]}
        m1_to_completed_m5[i] = len(m5_bars) - 1

        m15_t = (t // 900000) * 900000
        if cur_m15 is None:
            cur_m15 = {"time": m15_t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]}
        elif cur_m15["time"] == m15_t:
            cur_m15["high"] = max(cur_m15["high"], c["high"])
            cur_m15["low"] = min(cur_m15["low"], c["low"])
            cur_m15["close"] = c["close"]
            cur_m15["volume"] += c["volume"]
        else:
            m15_bars.append(cur_m15)
            cur_m15 = {"time": m15_t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]}
        m1_to_completed_m15[i] = len(m15_bars) - 1

    m5_closes = [b["close"] for b in m5_bars]
    m5_highs = [b["high"] for b in m5_bars]
    m5_lows = [b["low"] for b in m5_bars]
    m5_e21 = fast_ema(m5_closes, 21)
    m5_e50 = fast_ema(m5_closes, 50)

    m15_closes = [b["close"] for b in m15_bars]
    m15_highs = [b["high"] for b in m15_bars]
    m15_lows = [b["low"] for b in m15_bars]
    m15_e50 = fast_ema(m15_closes, 50)

    # M15 ADX(14) and ATR(14)
    m15_len = len(m15_bars)
    m15_tr = [0.0] * m15_len
    m15_pdm = [0.0] * m15_len
    m15_mdm = [0.0] * m15_len

    for j in range(1, m15_len):
        h, l, pc = m15_highs[j], m15_lows[j], m15_closes[j-1]
        m15_tr[j] = max(h - l, abs(h - pc), abs(l - pc))
        up = h - m15_highs[j-1]
        down = m15_lows[j-1] - l
        if up > down and up > 0:
            m15_pdm[j] = up
        if down > up and down > 0:
            m15_mdm[j] = down

    p = 14
    smooth_tr = [0.0] * m15_len
    smooth_pdm = [0.0] * m15_len
    smooth_mdm = [0.0] * m15_len
    m15_adx = [0.0] * m15_len
    m15_atr = [1.50] * m15_len

    if m15_len >= p + 1:
        smooth_tr[p] = sum(m15_tr[1:p+1])
        smooth_pdm[p] = sum(m15_pdm[1:p+1])
        smooth_mdm[p] = sum(m15_mdm[1:p+1])
        m15_atr[p] = smooth_tr[p] / p
        dx = [0.0] * m15_len

        for j in range(p + 1, m15_len):
            smooth_tr[j] = smooth_tr[j-1] - (smooth_tr[j-1] / p) + m15_tr[j]
            smooth_pdm[j] = smooth_pdm[j-1] - (smooth_pdm[j-1] / p) + m15_pdm[j]
            smooth_mdm[j] = smooth_mdm[j-1] - (smooth_mdm[j-1] / p) + m15_mdm[j]
            m15_atr[j] = smooth_tr[j] / p

            pdi = 100.0 * (smooth_pdm[j] / max(1e-6, smooth_tr[j]))
            mdi = 100.0 * (smooth_mdm[j] / max(1e-6, smooth_tr[j]))
            sum_di = pdi + mdi
            dx[j] = 100.0 * abs(pdi - mdi) / max(1e-6, sum_di)

        start_adx = 2 * p
        if m15_len >= start_adx:
            m15_adx[start_adx] = sum(dx[p+1:start_adx+1]) / p
            for j in range(start_adx + 1, m15_len):
                m15_adx[j] = (m15_adx[j-1] * (p - 1) + dx[j]) / p

    m15_atr_ema50 = fast_ema(m15_atr, 50)
    m15_vol_ratio = [0.0] * m15_len
    for j in range(m15_len):
        base_a = m15_atr_ema50[j] if m15_atr_ema50[j] > 0 else 1.0
        m15_vol_ratio[j] = round(m15_atr[j] / base_a, 2)

    features = []
    for i in range(n):
        t = times[i]
        c = raw_candles[i]
        dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
        day_str = dt.strftime('%Y-%m-%d')
        hr = dt.hour + dt.minute / 60.0

        if 13.5 <= hr < 16.5:
            sess_name = "LONDON_NY_OVERLAP"
        elif 16.5 <= hr < 21.0:
            sess_name = "NEW_YORK"
        elif 8.0 <= hr < 13.5:
            sess_name = "LONDON"
        elif 0.0 <= hr < 8.0:
            sess_name = "ASIA"
        else:
            sess_name = "OUT_OF_SESSION"

        m15_idx = m1_to_completed_m15[i]
        m15_ctx = "NEUTRAL"
        m15_adx_val = 20.0
        m15_vr = 1.0
        if m15_idx >= 50:
            m15_ema = m15_e50[m15_idx]
            if c["close"] > m15_ema:
                m15_ctx = "BULLISH"
            elif c["close"] < m15_ema:
                m15_ctx = "BEARISH"
            m15_adx_val = round(m15_adx[m15_idx], 1)
            m15_vr = m15_vol_ratio[m15_idx]

        m5_idx = m1_to_completed_m5[i]
        m5_ctx = "NONE"
        m5_last_swing_low = lows[i]
        m5_last_swing_high = highs[i]
        if m5_idx >= 50:
            if m5_e21[m5_idx] > m5_e50[m5_idx]:
                m5_ctx = "M5_BULL_TREND"
            elif m5_e21[m5_idx] < m5_e50[m5_idx]:
                m5_ctx = "M5_BEAR_TREND"
            m5_last_swing_low = min(m5_lows[max(0, m5_idx-5):m5_idx+1])
            m5_last_swing_high = max(m5_highs[max(0, m5_idx-5):m5_idx+1])

        recent_low = min(lows[max(0, i-11):i]) if i >= 11 else lows[i]
        recent_high = max(highs[max(0, i-11):i]) if i >= 11 else highs[i]
        swept_low = (lows[i] <= recent_low or (i > 0 and lows[i-1] <= recent_low))
        swept_high = (highs[i] >= recent_high or (i > 0 and highs[i-1] >= recent_high))

        prior_high_15 = max(highs[max(0, i-14):max(0, i-1)]) if i >= 15 else highs[i]
        prior_low_15 = min(lows[max(0, i-14):max(0, i-1)]) if i >= 15 else lows[i]

        vol_avg_10 = (sum(vols[max(0, i-9):i]) / 9.0) if i >= 10 else vols[i]
        vol_avg_5 = (sum(vols[max(0, i-5):i]) / 5.0) if i >= 6 else vols[i]

        loc_high_20 = max(highs[max(0, i-19):i]) if i >= 20 else highs[i]
        loc_low_20 = min(lows[max(0, i-19):i]) if i >= 20 else lows[i]
        range_span = max(0.50, loc_high_20 - loc_low_20)
        midpoint = (loc_high_20 + loc_low_20) / 2.0
        dist_from_mid = abs(c["close"] - midpoint) / range_span

        curr_price = c["close"]
        curr_body = abs(c["close"] - c["open"])
        atr_val = atr[i]
        e9_val = e9[i]
        e21_val = e21[i]

        cand_side = None
        cand_module = ""
        cand_base_score = 0

        # Module A: Sweep & Reclaim
        if swept_low and curr_price > recent_low and c["close"] >= c["open"]:
            cand_side = "LONG"
            cand_module = "MODULE_A_SWEEP_RECLAIM"
            cand_base_score = 40
        elif swept_high and curr_price < recent_high and c["close"] <= c["open"]:
            cand_side = "SHORT"
            cand_module = "MODULE_A_SWEEP_RECLAIM"
            cand_base_score = 40

        # Module B: Breakout & Retest
        if not cand_side and i >= 16:
            r_width = prior_high_15 - prior_low_15
            if r_width <= 2.2 * atr_val:
                if curr_price > prior_high_15 and c["close"] > c["open"]:
                    cand_side = "LONG"
                    cand_module = "MODULE_B_BREAKOUT"
                    cand_base_score = 35
                elif curr_price < prior_low_15 and c["close"] < c["open"]:
                    cand_side = "SHORT"
                    cand_module = "MODULE_B_BREAKOUT"
                    cand_base_score = 35

        # Module C: EMA Pullback
        if not cand_side and i >= 25:
            if e9_val > e21_val and c["low"] <= e9_val * 1.0008 and curr_price >= e21_val * 0.9995:
                if c["close"] >= c["open"]:
                    cand_side = "LONG"
                    cand_module = "MODULE_C_EMA_PULLBACK"
                    cand_base_score = 30
            elif e9_val < e21_val and c["high"] >= e9_val * 0.9992 and curr_price <= e21_val * 1.0005:
                if c["close"] <= c["open"]:
                    cand_side = "SHORT"
                    cand_module = "MODULE_C_EMA_PULLBACK"
                    cand_base_score = 30

        # Module D: Momentum Impulse
        if not cand_side and i >= 11:
            if c["volume"] >= 1.25 * vol_avg_10 and curr_body >= 0.70 * atr_val:
                if c["close"] > c["open"] and e9_val > e21_val:
                    cand_side = "LONG"
                    cand_module = "MODULE_D_MOMENTUM_IMPULSE"
                    cand_base_score = 30
                elif c["close"] < c["open"] and e9_val < e21_val:
                    cand_side = "SHORT"
                    cand_module = "MODULE_D_MOMENTUM_IMPULSE"
                    cand_base_score = 30

        # Module E: M5 Structure + M1 Trigger
        if not cand_side and m5_ctx != "NONE" and i >= 25:
            if m5_ctx == "M5_BULL_TREND" and curr_price > e21_val and c["close"] > c["open"]:
                cand_side = "LONG"
                cand_module = "MODULE_E_M5_M1_HYBRID"
                cand_base_score = 35
            elif m5_ctx == "M5_BEAR_TREND" and curr_price < e21_val and c["close"] < c["open"]:
                cand_side = "SHORT"
                cand_module = "MODULE_E_M5_M1_HYBRID"
                cand_base_score = 35

        features.append({
            "idx": i,
            "time": t,
            "day_str": day_str,
            "session": sess_name,
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
            "body": curr_body,
            "atr": atr_val,
            "e9": e9_val,
            "e21": e21_val,
            "e50": e50[i],
            "m15_context": m15_ctx,
            "m15_adx": m15_adx_val,
            "m15_vol_ratio": m15_vr,
            "m5_setup": m5_ctx,
            "m5_swing_low": m5_last_swing_low,
            "m5_swing_high": m5_last_swing_high,
            "recent_low": recent_low,
            "recent_high": recent_high,
            "dist_from_mid": dist_from_mid,
            "vol_expansion": (c["volume"] > vol_avg_5),
            "cand_side": cand_side,
            "cand_module": cand_module,
            "cand_base_score": cand_base_score
        })

    return features

raw_candles = []
with open(DATA_PATH, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        raw_candles.append({
            "time": int(r["time"]),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r["volume"])
        })

print(f"Loaded {len(raw_candles)} candles.")
features = precalculate_all_features(raw_candles)
print("Features precalculated.")

idx_train_end = int(len(features) * 0.60)
idx_val_end = int(len(features) * 0.80)
n_candles = len(features)

from run_v32_forensic_suite import run_simulation_v32_fast

res_cand_a = run_simulation_v32_fast(features, score_threshold=80, exit_model="G", chase_atr_multiplier=2.5, fee_risk_gate_ratio=0.25, session_mode="MAJOR_ONLY", initial_balance=1000.0)
print(f"Cand A Baseline: Trades={res_cand_a['total_trades']}, WR={res_cand_a['win_rate_pct']}%, Gross PF={res_cand_a['gross_pf']}, Net PF={res_cand_a['net_pf']}, PnL=${res_cand_a['net_pnl']}, Max DD={res_cand_a['max_drawdown_pct']}%, Fees=${res_cand_a['total_fees']}")

res_cand_a_oos = run_simulation_v32_fast(features[idx_val_end:], score_threshold=80, exit_model="G", chase_atr_multiplier=2.5, fee_risk_gate_ratio=0.25, session_mode="MAJOR_ONLY", initial_balance=1000.0)
print(f"Cand A OOS Baseline: Trades={res_cand_a_oos['total_trades']}, WR={res_cand_a_oos['win_rate_pct']}%, Gross PF={res_cand_a_oos['gross_pf']}, Net PF={res_cand_a_oos['net_pf']}, PnL=${res_cand_a_oos['net_pnl']}")
