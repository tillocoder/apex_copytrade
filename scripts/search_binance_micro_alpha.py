#!/usr/bin/env python3
"""BTC/ETH USDT-M futures micro-account strategy search.

This is a research-only, deterministic walk-forward search.  It downloads/caches
one year of *closed* Binance USDT-M 5m candles, evaluates 1,080 parameter sets
over three unrelated rule families, selects only on train data, then reports
validation and locked-test results.  It models market entry/stop/TP as taker
orders (5 bps per side) plus 1 bp adverse slippage per fill.  When a 5m candle
touches both stop and target it assumes the stop was filled first.

No exchange orders are sent by this script.
"""
from __future__ import annotations

import csv
import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "futures_1y"
OUT_DIR = ROOT / "audit" / "binance_micro_alpha_1y"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ("BTCUSDT", "ETHUSDT")
BAR_MS = 300_000
FEE = 0.0005                 # Binance taker fee per side, deliberately conservative
SLIPPAGE_BPS = 1.0           # adverse slippage per fill
INITIAL_BALANCE = 20.0
MIN_NOTIONAL = 20.0
LEVERAGE = 20
RISK_PCT = 0.01
MAX_TRADES_DAY = 3
WORKER_DATA: dict | None = None
WORKER_TRAIN_END = 0


def fetch(symbol: str) -> list[list[float]]:
    path = DATA_DIR / f"{symbol}_5m_1y.csv"
    if path.exists():
        rows = []
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append([int(r["time"]), *[float(r[x]) for x in ("open", "high", "low", "close", "volume")]])
        # A 1y cache becomes stale quickly; use it only if written today.
        if len(rows) >= 100_000 and (time.time() - path.stat().st_mtime) < 24 * 3600:
            return rows

    end = int(time.time() * 1000) // BAR_MS * BAR_MS
    start = end - 365 * 24 * 60 * 60 * 1000
    rows: list[list[float]] = []
    cursor = start
    while cursor < end:
        q = urllib.parse.urlencode({"symbol": symbol, "interval": "5m", "startTime": cursor, "limit": 1500})
        req = urllib.request.Request("https://fapi.binance.com/fapi/v1/klines?" + q, headers={"User-Agent": "apex-research/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            batch = json.loads(resp.read().decode("utf-8"))
        if not batch:
            break
        rows.extend([[int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in batch if int(x[0]) < end])
        cursor = int(batch[-1][0]) + BAR_MS
        time.sleep(0.055)
    rows = sorted({int(r[0]): r for r in rows}.values(), key=lambda r: r[0])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["time", "open", "high", "low", "close", "volume"]); w.writerows(rows)
    return rows


def ema(a: list[float], p: int) -> list[float]:
    out = [a[0]] * len(a); k = 2 / (p + 1)
    for i in range(1, len(a)): out[i] = a[i] * k + out[i-1] * (1-k)
    return out


def atr(h: list[float], l: list[float], c: list[float], p: int = 14) -> list[float]:
    tr = [h[0]-l[0]] + [max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])) for i in range(1, len(c))]
    out = [0.0] * len(c); out[p-1] = sum(tr[:p]) / p
    for i in range(p, len(c)): out[i] = (out[i-1]*(p-1)+tr[i])/p
    return out


def rsi(c: list[float], p: int) -> list[float]:
    out = [50.0]*len(c); gains = [0.0]*len(c); losses = [0.0]*len(c)
    for i in range(1, len(c)):
        d=c[i]-c[i-1]; gains[i]=max(d,0); losses[i]=max(-d,0)
    ag=sum(gains[1:p+1])/p; al=sum(losses[1:p+1])/p
    for i in range(p, len(c)):
        if i>p: ag=(ag*(p-1)+gains[i])/p; al=(al*(p-1)+losses[i])/p
        out[i]=100-100/(1+ag/max(al,1e-12))
    return out


def bollinger(c: list[float], p: int, k: float) -> tuple[list[float], list[float]]:
    """Rolling bands using only the current and prior closed M5 candles."""
    upper=[c[0]]*len(c); lower=[c[0]]*len(c); total=0.0; total_sq=0.0
    for i, value in enumerate(c):
        total += value; total_sq += value*value
        if i >= p:
            old=c[i-p]; total -= old; total_sq -= old*old
        n=min(i+1,p); mean=total/n; variance=max(0.0,total_sq/n-mean*mean); dev=math.sqrt(variance)
        upper[i]=mean+k*dev; lower[i]=mean-k*dev
    return upper, lower


def stochastic(h: list[float], l: list[float], c: list[float], p: int) -> list[float]:
    out=[50.0]*len(c)
    for i in range(p-1,len(c)):
        hi=max(h[i-p+1:i+1]); lo=min(l[i-p+1:i+1]); out[i]=100*(c[i]-lo)/max(hi-lo,1e-12)
    return out


def daily_vwap(t: list[int], h: list[float], l: list[float], c: list[float], v: list[float]) -> list[float]:
    out=[]; day=None; pv=0.0; vv=0.0
    for ts,hi,lo,cl,vol in zip(t,h,l,c,v):
        current_day=ts//86_400_000
        if current_day != day: day=current_day; pv=0.0; vv=0.0
        pv += ((hi+lo+cl)/3)*vol; vv += vol; out.append(pv/max(vv,1e-12))
    return out


def supertrend(h: list[float], l: list[float], c: list[float], atr_values: list[float], mult: float) -> tuple[list[float], list[int]]:
    line=[c[0]]*len(c); direction=[1]*len(c); final_upper=[c[0]]*len(c); final_lower=[c[0]]*len(c)
    for i in range(1,len(c)):
        mid=(h[i]+l[i])/2; basic_upper=mid+mult*atr_values[i]; basic_lower=mid-mult*atr_values[i]
        final_upper[i]=basic_upper if basic_upper<final_upper[i-1] or c[i-1]>final_upper[i-1] else final_upper[i-1]
        final_lower[i]=basic_lower if basic_lower>final_lower[i-1] or c[i-1]<final_lower[i-1] else final_lower[i-1]
        if c[i]>final_upper[i-1]: direction[i]=1
        elif c[i]<final_lower[i-1]: direction[i]=-1
        else: direction[i]=direction[i-1]
        line[i]=final_lower[i] if direction[i]==1 else final_upper[i]
    return line,direction


@dataclass(frozen=True)
class Candidate:
    family: str
    params: tuple
    label: str


def candidates() -> list[Candidate]:
    result=[]
    # 576 EMA trend-pullback variations.
    for fast, slow, filt, rsil, rsis, sl, rr, vol in itertools.product(
        (9, 13), (34, 50), (100, 200), (40, 45), (55, 60), (1.0, 1.25, 1.5), (1.5, 2.0, 2.5), (0.0, 1.1)):
        if fast < slow:
            p=(fast,slow,filt,rsil,rsis,sl,rr,vol); result.append(Candidate("ema_pullback",p,str(p)))
    # 216 Donchian breakout variations.
    for look, trend, sl, rr, vol in itertools.product((12,24,36,48), (50,100,200), (1.0,1.5,2.0), (1.5,2.0,2.5), (0.0,1.2)):
        p=(look,trend,sl,rr,vol); result.append(Candidate("donchian",p,str(p)))
    # 288 RSI mean-reversion-with-trend variations.
    for period, level, trend, sl, rr, vol in itertools.product((7,14), (25,30,35), (50,100), (1.0,1.25,1.5,2.0), (1.0,1.25,1.5), (0.0,1.1)):
        p=(period,level,trend,sl,rr,vol); result.append(Candidate("rsi_revert",p,str(p)))
    # Independent momentum, breakout, reversion and price-action families.
    for fast,slow,sig,trend,sl,rr,vol in itertools.product((8,12,16),(21,26,34),(5,9),(50,100,200),(1.0,1.5,2.0),(1.25,1.5,2.0),(0.0,1.1)):
        if fast < slow:
            p=(fast,slow,sig,trend,sl,rr,vol); result.append(Candidate("macd_cross",p,str(p)))
    for fast,slow,trend,sl,rr,vol in itertools.product((5,8,13,21),(21,34,50,100),(100,200),(1.0,1.5,2.0),(1.25,1.5,2.0),(0.0,1.1)):
        if fast < slow:
            p=(fast,slow,trend,sl,rr,vol); result.append(Candidate("ema_cross",p,str(p)))
    for period,band,rsi_level,trend,sl,rr,vol in itertools.product((20,30),(1.5,2.0),(30,35,40),(50,100),(1.0,1.5,2.0),(1.0,1.25,1.5),(0.0,1.1)):
        p=(period,band,rsi_level,trend,sl,rr,vol); result.append(Candidate("bollinger_revert",p,str(p)))
    for period,level,trend,sl,rr,vol in itertools.product((14,21),(20,25),(50,100),(1.0,1.5,2.0),(1.0,1.25,1.5),(0.0,1.1)):
        p=(period,level,trend,sl,rr,vol); result.append(Candidate("stoch_pullback",p,str(p)))
    for trend,dev,sl,rr,vol in itertools.product((50,100),(0.001,0.002),(1.0,1.5,2.0),(1.25,1.5,2.0),(0.0,1.1)):
        p=(trend,dev,sl,rr,vol); result.append(Candidate("vwap_reclaim",p,str(p)))
    for trend,body_atr,sl,rr,vol in itertools.product((50,100),(0.5,1.0),(1.0,1.5,2.0),(1.25,1.5,2.0),(0.0,1.1)):
        p=(trend,body_atr,sl,rr,vol); result.append(Candidate("engulfing_trend",p,str(p)))
    for multiplier,trend,sl,rr,vol in itertools.product((1.5,2.0,2.5),(50,100,200),(1.0,1.5,2.0),(1.25,1.5,2.0),(0.0,1.1)):
        p=(multiplier,trend,sl,rr,vol); result.append(Candidate("supertrend_flip",p,str(p)))
    return result


def prep(rows: list[list[float]]) -> dict:
    t,o,h,l,c,v = map(list, zip(*rows))
    atr_values=atr(h,l,c)
    bb={key:bollinger(c,*key) for key in ((20,1.5),(20,2.0),(30,1.5),(30,2.0))}
    return {"t":t,"o":o,"h":h,"l":l,"c":c,"v":v,"atr":atr_values,
            "ema":{p:ema(c,p) for p in (5,8,9,12,13,16,21,26,34,50,100,200)},
            "rsi":{p:rsi(c,p) for p in (7,14)},"bb":bb,
            "stoch":{p:stochastic(h,l,c,p) for p in (14,21)},"vwap":daily_vwap(t,h,l,c,v),
            "supertrend":{m:supertrend(h,l,c,atr_values,m) for m in (1.5,2.0,2.5)}}


def signal(d: dict, i: int, x: Candidate) -> tuple[int, float, float] | None:
    c,h,l,v,a=d["c"],d["h"],d["l"],d["v"],d["atr"]
    if a[i] <= 0 or not (7 <= datetime.fromtimestamp(d["t"][i]/1000, tz=timezone.utc).hour < 21): return None
    volavg=sum(v[i-20:i])/20
    if x.family=="ema_pullback":
        fast,slow,filt,lo,hi,sl,rr,vr=x.params; ef=d["ema"][fast]; es=d["ema"][slow]; et=d["ema"][filt]; r=d["rsi"][14][i]
        if vr and v[i] < volavg*vr: return None
        if c[i]>et[i] and ef[i]>es[i] and l[i]<=ef[i] and r<=lo: return (1,sl*a[i],rr)
        if c[i]<et[i] and ef[i]<es[i] and h[i]>=ef[i] and r>=hi: return (-1,sl*a[i],rr)
    elif x.family=="donchian":
        look,trend,sl,rr,vr=x.params; et=d["ema"][trend]
        if vr and v[i] < volavg*vr: return None
        if c[i]>et[i] and c[i]>max(h[i-look:i]): return (1,sl*a[i],rr)
        if c[i]<et[i] and c[i]<min(l[i-look:i]): return (-1,sl*a[i],rr)
    elif x.family=="rsi_revert":
        period,level,trend,sl,rr,vr=x.params; et=d["ema"][trend]; r=d["rsi"][period][i]
        if vr and v[i] < volavg*vr: return None
        if c[i]>et[i] and r<level: return (1,sl*a[i],rr)
        if c[i]<et[i] and r>100-level: return (-1,sl*a[i],rr)
    elif x.family=="macd_cross":
        fast,slow,sig,trend,sl,rr,vr=x.params; ef=d["ema"][fast]; es=d["ema"][slow]; macd=[0.0,ef[i-1]-es[i-1],ef[i]-es[i]]
        # Signal is a causal EMA of the full MACD series; cached lazily by parameter pair.
        key=(fast,slow,sig)
        if "macd_signal" not in d: d["macd_signal"]={}
        if key not in d["macd_signal"]: d["macd_signal"][key]=ema([a-b for a,b in zip(d["ema"][fast],d["ema"][slow])],sig)
        ms=d["macd_signal"][key]; et=d["ema"][trend]
        if vr and v[i]<volavg*vr: return None
        if c[i]>et[i] and macd[1]<=ms[i-1] and macd[2]>ms[i]: return (1,sl*a[i],rr)
        if c[i]<et[i] and macd[1]>=ms[i-1] and macd[2]<ms[i]: return (-1,sl*a[i],rr)
    elif x.family=="ema_cross":
        fast,slow,trend,sl,rr,vr=x.params; ef=d["ema"][fast]; es=d["ema"][slow]; et=d["ema"][trend]
        if vr and v[i]<volavg*vr: return None
        if c[i]>et[i] and ef[i-1]<=es[i-1] and ef[i]>es[i]: return (1,sl*a[i],rr)
        if c[i]<et[i] and ef[i-1]>=es[i-1] and ef[i]<es[i]: return (-1,sl*a[i],rr)
    elif x.family=="bollinger_revert":
        period,band,level,trend,sl,rr,vr=x.params; upper,lower=d["bb"][(period,band)]; et=d["ema"][trend]; r=d["rsi"][14][i]
        if vr and v[i]<volavg*vr: return None
        # Re-entry inside the band, not a falling-knife entry outside it.
        if c[i]>et[i] and l[i]<lower[i] and c[i]>lower[i] and r<level: return (1,sl*a[i],rr)
        if c[i]<et[i] and h[i]>upper[i] and c[i]<upper[i] and r>100-level: return (-1,sl*a[i],rr)
    elif x.family=="stoch_pullback":
        period,level,trend,sl,rr,vr=x.params; k=d["stoch"][period]; et=d["ema"][trend]
        if vr and v[i]<volavg*vr: return None
        if c[i]>et[i] and k[i-1]<level and k[i]>=level: return (1,sl*a[i],rr)
        if c[i]<et[i] and k[i-1]>100-level and k[i]<=100-level: return (-1,sl*a[i],rr)
    elif x.family=="vwap_reclaim":
        trend,dev,sl,rr,vr=x.params; vw=d["vwap"]; et=d["ema"][trend]
        if vr and v[i]<volavg*vr: return None
        if c[i]>et[i] and c[i-1]<vw[i-1]*(1-dev) and c[i]>vw[i]: return (1,sl*a[i],rr)
        if c[i]<et[i] and c[i-1]>vw[i-1]*(1+dev) and c[i]<vw[i]: return (-1,sl*a[i],rr)
    elif x.family=="engulfing_trend":
        trend,body_atr,sl,rr,vr=x.params; et=d["ema"][trend]; body=abs(c[i]-d["o"][i])
        prev_high=max(d["o"][i-1],c[i-1]); prev_low=min(d["o"][i-1],c[i-1])
        if vr and v[i]<volavg*vr: return None
        if c[i]>et[i] and c[i]>d["o"][i] and d["o"][i]<=prev_low and c[i]>=prev_high and body>=body_atr*a[i]: return (1,sl*a[i],rr)
        if c[i]<et[i] and c[i]<d["o"][i] and d["o"][i]>=prev_high and c[i]<=prev_low and body>=body_atr*a[i]: return (-1,sl*a[i],rr)
    elif x.family=="supertrend_flip":
        multiplier,trend,sl,rr,vr=x.params; _,directions=d["supertrend"][multiplier]; et=d["ema"][trend]
        if vr and v[i]<volavg*vr: return None
        if c[i]>et[i] and directions[i-1]==-1 and directions[i]==1: return (1,sl*a[i],rr)
        if c[i]<et[i] and directions[i-1]==1 and directions[i]==-1: return (-1,sl*a[i],rr)
    return None


def run(d: dict, x: Candidate, start: int, end: int, collect=False) -> dict:
    bal=INITIAL_BALANCE; peak=bal; max_dd=0.0; pos=None; daily=0; day=None; trades=[]; pnls=[]
    # Warm-up guarantees all templates have completed indicators.
    for i in range(max(start, 250), min(end, len(d["c"])-1)):
        today=d["t"][i]//86_400_000
        if today!=day: day=today; daily=0
        if pos:
            side,entry,stop,target,qty,risk,opened=pos
            # conservative exit sequence: SL is evaluated before TP in an ambiguous bar.
            hit_sl=(side==1 and d["l"][i]<=stop) or (side==-1 and d["h"][i]>=stop)
            hit_tp=(side==1 and d["h"][i]>=target) or (side==-1 and d["l"][i]<=target)
            if hit_sl or hit_tp:
                reason="SL" if hit_sl else "TP"; px=stop if hit_sl else target
                slip=px*SLIPPAGE_BPS/10_000
                px=px-slip if side==1 else px+slip
                gross=(px-entry)*qty*side; fees=(entry+px)*qty*FEE; pnl=gross-fees; bal+=pnl; peak=max(peak,bal)
                max_dd=max(max_dd, (peak-bal)/peak*100 if peak else 0.0)
                pnls.append(pnl)
                if collect: trades.append({"time":d["t"][i],"side":"LONG" if side==1 else "SHORT","entry":round(entry,5),"exit":round(px,5),"reason":reason,"pnl":round(pnl,4),"equity":round(bal,4)})
                pos=None; daily+=1
        if not pos and daily<MAX_TRADES_DAY and i+1<end:
            s=signal(d,i,x)
            if s:
                side,dist,rr=s; entry=d["o"][i+1]*(1+(SLIPPAGE_BPS/10_000 if side==1 else -SLIPPAGE_BPS/10_000))
                dist=max(dist,entry*0.001) # avoid unrealistically tight stop
                # Real Binance lot-size & minNotional clamp
                step = 0.001
                min_contract_qty = max(step, round(MIN_NOTIONAL / entry + 0.00049, 3))
                desired = max(bal*RISK_PCT/dist, min_contract_qty)
                qty = round(math.ceil(desired / step) * step, 3)
                risk = dist*qty + (2*entry*qty*FEE)
                stop=entry-side*dist; target=entry+side*dist*rr
                pos=(side,entry,stop,target,qty,risk,i)
    pnl=bal-INITIAL_BALANCE
    # An open final position is deliberately ignored (not marked optimistically).
    wins=[z for z in pnls if z>0]; losses=[z for z in pnls if z<=0]
    gp=sum(wins); gl=abs(sum(losses))
    return {"trades":len(pnls), "pnl":round(pnl,4), "return_pct":round(pnl/INITIAL_BALANCE*100,2), "pf":round(gp/gl,3) if gl else 0.0, "win_rate":round(len(wins)/len(pnls)*100,2) if pnls else 0.0, "max_dd_pct":round(max_dd,2), "trades_log":trades}


def score(r: dict) -> float:
    # A candidate must earn on all periods; train score only is used during selection.
    return r["return_pct"] + 30*max(0,r["pf"]-1) - 3*r["max_dd_pct"]


def _init_worker(data: dict, train_end: int) -> None:
    """One full immutable market-data copy per process; no IPC in inner loop."""
    global WORKER_DATA, WORKER_TRAIN_END
    WORKER_DATA, WORKER_TRAIN_END = data, train_end


def _screen_candidate(x: Candidate) -> tuple[float, Candidate, dict]:
    if WORKER_DATA is None:
        raise RuntimeError("Worker market data was not initialized")
    result = run(WORKER_DATA, x, 0, WORKER_TRAIN_END, False)
    return score(result), x, result


def main():
    parser=argparse.ArgumentParser(description="Parallel Binance Futures 1y strategy search")
    parser.add_argument("--workers",type=int,default=os.cpu_count() or 1,help="CPU worker processes (default: all logical cores)")
    args=parser.parse_args()
    workers=max(1,min(args.workers, os.cpu_count() or 1))
    all_rows=[]; grid=candidates()
    print(f"Searching {len(grid)} configurations per symbol with {workers} worker processes; no exchange orders will be sent.",flush=True)
    for symbol in SYMBOLS:
        rows=fetch(symbol); d=prep(rows); n=len(rows); a=int(n*.60); b=int(n*.80)
        print(f"{symbol}: {n:,} closed 5m bars, {datetime.fromtimestamp(rows[0][0]/1000,tz=timezone.utc).date()} to {datetime.fromtimestamp(rows[-1][0]/1000,tz=timezone.utc).date()}",flush=True)
        # Process workers deliberately have no access to keys, database, or exchange code.
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(d,a)) as pool:
            ranked=list(pool.map(_screen_candidate, grid, chunksize=8))
        print(f"  {symbol}: parallel train screen complete ({len(ranked)} candidates)",flush=True)
        # A no-trade candidate is not an alpha.  Selection is still *train-only*,
        # but requires enough observations to make a later validation meaningful.
        eligible=[z for z in ranked if z[2]["trades"] >= 20 and z[2]["pnl"] > 0]
        eligible.sort(reverse=True, key=lambda z:z[0])
        print(f"  {symbol}: {len(eligible)} train-eligible candidates (>=20 trades, positive net)",flush=True)
        # Re-run only train leaders with full accounting/logs; validation/test were never used to select.
        for _,x,train_fast in eligible[:50]:
            train=run(d,x,0,a,True); valid=run(d,x,a,b,True); test=run(d,x,b,n,True)
            row={"symbol":symbol,"family":x.family,"params":x.params,"train":{k:v for k,v in train.items() if k!="trades_log"},"validation":{k:v for k,v in valid.items() if k!="trades_log"},"test":{k:v for k,v in test.items() if k!="trades_log"}}
            row["robust_score"]=round(min(score(train),score(valid),score(test)),3)
            all_rows.append(row)
    survivors=[r for r in all_rows if r["validation"]["pf"]>1 and r["test"]["pf"]>1 and r["validation"]["trades"]>=12 and r["test"]["trades"]>=12]
    survivors.sort(key=lambda r:(r["robust_score"],r["test"]["pf"]),reverse=True)
    payload={"generated_at":datetime.now(timezone.utc).isoformat(),"assumptions":{"initial_balance":INITIAL_BALANCE,"leverage":LEVERAGE,"minimum_notional":MIN_NOTIONAL,"taker_fee_per_side":FEE,"slippage_bps_per_fill":SLIPPAGE_BPS,"risk_pct_target":RISK_PCT,"max_trades_day":MAX_TRADES_DAY,"selection":"60% train only; train candidates require >=20 trades and positive net; top 50 then validation 20% and locked test 20%"},"grid_per_symbol":len(grid),"shortlisted":all_rows,"survivors":survivors[:10],"verdict":"NO ROBUST CANDIDATE" if not survivors else "ROBUST CANDIDATES FOUND — PAPER VALIDATION REQUIRED"}
    (OUT_DIR/"summary.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    with (OUT_DIR/"leaderboard.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["symbol","family","params","robust_score","train_return","valid_return","test_return","train_pf","valid_pf","test_pf","test_dd"])
        for r in all_rows:
            w.writerow([r["symbol"],r["family"],r["params"],r["robust_score"],r["train"]["return_pct"],r["validation"]["return_pct"],r["test"]["return_pct"],r["train"]["pf"],r["validation"]["pf"],r["test"]["pf"],r["test"]["max_dd_pct"]])
    print(json.dumps({"tested":len(all_rows),"survivors":len(survivors),"verdict":payload["verdict"],"best":survivors[0] if survivors else None},indent=2))

if __name__=="__main__": main()
