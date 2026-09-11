from typing import Optional, Tuple



class CandidateA:
    name = 'A - EMA Trend Pullback'
    @staticmethod
    def evaluate(i, data, cfg):
        if i < 250: return None
        c = data.closes[i]
        atr = data.atr_1h[i]
        atr_pct = (atr / c) * 100.0 if c > 0 else 0.0
        if atr_pct < 0.15 or atr_pct > 4.0: return None
        rsi = data.rsi_1h[i]
        v = data.volumes[i]
        vol_ma = data.vol_ma20[i]
        idx_4h = max(0, data.map_1h_to_4h[i] - 1)  # STRICTLY prev 4H
        if idx_4h < 50: return None
        cl_4h = data.closes_4h[idx_4h]
        e50_4h = data.ema50_4h[idx_4h]
        if v < 1.1 * vol_ma: return None
        if cl_4h > e50_4h and rsi < 45 and c > data.ema50_1h[i]:
            return ('BUY', 1.5, 2.0, 3.0)
        if cl_4h < e50_4h and rsi > 55 and c < data.ema50_1h[i]:
            return ('SELL', 1.5, 2.0, 3.0)
        return None


class CandidateB:
    name = 'B - Donchian 48H Breakout + 4H HTF (Strict prev 4H)'
    @staticmethod
    def evaluate(i, data, cfg):
        if i < 250: return None
        c = data.closes[i]
        atr = data.atr_1h[i]
        atr_pct = (atr / c) * 100.0 if c > 0 else 0.0
        if atr_pct < 0.15 or atr_pct > 4.0: return None
        o = data.opens[i]
        v = data.volumes[i]
        vol_ma = data.vol_ma20[i]
        idx_4h = max(0, data.map_1h_to_4h[i] - 1)  # STRICTLY prev completed 4H
        if idx_4h < 50: return None
        cl_4h = data.closes_4h[idx_4h]
        e50_4h = data.ema50_4h[idx_4h]

        lb = getattr(cfg, 'breakout_lookback_bars', 48) if cfg else 48
        vm = getattr(cfg, 'volume_expansion_multiplier', 1.35) if cfg else 1.35
        sl_m = getattr(cfg, 'sl_atr_multiplier', 1.8) if cfg else 1.8
        tp1_m = getattr(cfg, 'tp1_r_multiple', 3.0) if cfg else 3.0
        tp2_m = getattr(cfg, 'tp2_r_multiple', 4.5) if cfg else 4.5

        if i < lb: return None
        hh = max(data.highs[i - lb:i])
        ll = min(data.lows[i - lb:i])
        if v < vm * vol_ma: return None
        if c > hh and c > o and cl_4h > e50_4h:
            return ('BUY', sl_m, tp1_m, tp2_m)
        if c < ll and c < o and cl_4h < e50_4h:
            return ('SELL', sl_m, tp1_m, tp2_m)
        return None


class CandidateC:
    name = 'C - SMC Liquidity Sweep + MSS'
    @staticmethod
    def evaluate(i, data, cfg):
        if i < 25: return None
        c = data.closes[i]
        atr = data.atr_1h[i]
        atr_pct = (atr / c) * 100.0 if c > 0 else 0.0
        if atr_pct < 0.15 or atr_pct > 4.0: return None
        lookback = 20
        swing_high = max(data.highs[i - lookback:i])
        swing_low = min(data.lows[i - lookback:i])
        o = data.opens[i]
        h = data.highs[i]
        l = data.lows[i]
        prev_close = data.closes[i - 1]
        candle_range = h - l
        if candle_range < 0.001: return None
        # Bullish MSS: wick sweeps below swing low, closes above prev
        if l < swing_low and c > o and c > prev_close and (c - l) > 1.5 * (h - c):
            return ('BUY', 1.2, 2.5, 4.0)
        # Bearish MSS: wick sweeps above swing high, closes below prev
        if h > swing_high and c < o and c < prev_close and (h - c) > 1.5 * (c - l):
            return ('SELL', 1.2, 2.5, 4.0)
        return None


class CandidateD:
    name = 'D - BB/KC Squeeze Expansion'
    @staticmethod
    def evaluate(i, data, cfg):
        if i < 60: return None
        c = data.closes[i]
        atr = data.atr_1h[i]
        atr_pct = (atr / c) * 100.0 if c > 0 else 0.0
        if atr_pct < 0.15 or atr_pct > 4.0: return None
        period = 20
        closes_slice = data.closes[i - period:i + 1]
        mid = sum(closes_slice) / len(closes_slice)
        variance = sum((x - mid) ** 2 for x in closes_slice) / len(closes_slice)
        std = variance ** 0.5
        bb_upper = mid + 2.0 * std
        bb_lower = mid - 2.0 * std
        kc_mid = data.ema21_1h[i]
        kc_upper = kc_mid + 1.5 * atr
        kc_lower = kc_mid - 1.5 * atr
        # Previous bar squeeze check
        prev_closes = data.closes[i - period - 1:i]
        prev_mid = sum(prev_closes) / len(prev_closes)
        prev_std = (sum((x - prev_mid) ** 2 for x in prev_closes) / len(prev_closes)) ** 0.5
        prev_bb_upper = prev_mid + 2.0 * prev_std
        prev_kc_upper = data.ema21_1h[i - 1] + 1.5 * data.atr_1h[i - 1]
        was_squeezed = prev_bb_upper < prev_kc_upper
        if not was_squeezed: return None
        if bb_upper > kc_upper and data.closes[i] > mid:
            return ('BUY', 1.5, 2.5, 4.0)
        if bb_lower < kc_lower and data.closes[i] < mid:
            return ('SELL', 1.5, 2.5, 4.0)
        return None


class CandidateE:
    name = 'E - Regime-Adaptive Asymmetric (4H EMA200)'
    @staticmethod
    def evaluate(i, data, cfg):
        if i < 250: return None
        c = data.closes[i]
        atr = data.atr_1h[i]
        atr_pct = (atr / c) * 100.0 if c > 0 else 0.0
        if atr_pct < 0.15 or atr_pct > 4.0: return None
        idx_4h = max(0, data.map_1h_to_4h[i] - 1)
        if idx_4h < 200: return None
        cl_4h = data.closes_4h[idx_4h]
        e200_4h = data.ema200_4h[idx_4h]
        c = data.closes[i]
        rsi = data.rsi_1h[i]
        v = data.volumes[i]
        vol_ma = data.vol_ma20[i]
        if v < 1.2 * vol_ma: return None
        if cl_4h > e200_4h and rsi > 55 and rsi < 75 and c > data.ema50_1h[i]:
            return ('BUY', 1.8, 2.5, 4.0)
        if cl_4h < e200_4h and rsi < 45 and rsi > 25 and c < data.ema50_1h[i]:
            return ('SELL', 1.8, 2.5, 4.0)
        return None


class CandidateF:
    name = 'F - Ensemble (B+C Agreement)'
    @staticmethod
    def evaluate(i, data, cfg):
        sig_b = CandidateB.evaluate(i, data, cfg)
        sig_c = CandidateC.evaluate(i, data, cfg)
        if sig_b is None or sig_c is None: return None
        if sig_b[0] == sig_c[0]:
            return (sig_b[0], 1.8, 3.0, 4.5)
        return None


CANDIDATES = [CandidateA, CandidateB, CandidateC, CandidateD, CandidateE, CandidateF]
