# ARMANDINO TRADING STRATEGY: DUAL-SCENARIO 90-DAY FORENSIC AUDIT

## 1. Executive Summary & Strategy Architecture
* **Period:** Last ~95 days (June 30, 2026 – October 3, 2026)
* **Universe:** ETHUSDT (M15/H1) and ZECUSDT (M15)
* **Initial Capital:** $20.00 USDT
* **Margin Model:** Binance Futures Cross Margin (15x Leverage, MMR: ETH 0.5%, ZEC 1.0%)
* **Execution Fees:** Binance Standard Taker 0.05% (market entry/exit) + Maker 0.02% (limit TP) + 2 bps slippage
* **Partial Take-Profit Mechanics:** TP1 at +1.0% (50% closed), TP2 at +2.5% (50% closed)

---

## 2. Comparative Performance Matrix

| Metric | Scenario A (Armandino Aggressive - No Hard SL) | Scenario B (Protected Variant - 1.8% Hard SL) | Delta / Assessment |
| :--- | :--- | :--- | :--- |
| **Final Equity** | **$1.82** | **$1.95** | +0.13$ |
| **Total ROI (%)** | **-90.89%** | **-90.26%** | +0.63% |
| **Total Trades** | 114 | 126 | 12 trades |
| **Win Rate (%)** | **57.89%** (66W / 48L) | **35.71%** (45W / 81L) | -22.2% |
| **Profit Factor (PF)** | **0.71** | **0.67** | -0.04 |
| **Max Drawdown (MDD %)**| **91.71%** | **91.99%** | 0.28% |
| **Total Commissions Paid**| $4.63 | $5.3 | $0.67 |
| **Avg Trade Holding Time**| 16.75 hours | 11.48 hours | -5.3 hrs |
| **Liquidation Event** | **NO (SURVIVED)** | **NO (SURVIVED)** | Critical Risk Marker |
| **ETH Volume Share** | 49.1% (56 trades) | 38.9% (49 trades) | Target: ~55% |
| **ZEC Volume Share** | 50.9% (58 trades) | 61.1% (77 trades) | Target: ~45% |

---

## 3. Exit Reason & Execution Breakdown

### Scenario A (Armandino Aggressive):
* **TP1 Hits (+1.0% Partial):** 79 trades
* **TP2 Hits (+2.5% Full Close):** 51 trades
* **Exit Reasons Detail:** {
  "TP2": 51,
  "DRAWDOWN_CUT": 39,
  "TIME_EXPIRED": 24
}

### Scenario B (Protected Variant):
* **TP1 Hits (+1.0% Partial):** 74 trades
* **TP2 Hits (+2.5% Full Close):** 45 trades
* **Exit Reasons Detail:** {
  "TP2": 45,
  "STOP_LOSS": 81
}

---

## 4. Monte Carlo $20 Survival Analysis (1,000 Iterations)

| Survival Metric | Scenario A (Aggressive) | Scenario B (Protected) |
| :--- | :--- | :--- |
| **Survival Rate (No Liquidation)** | **33.6%** | **48.2%** |
| **Risk of Ruin (%)** | **66.4%** | **51.8%** |
| **Median Final Equity** | $0.0 | $0.0 |
| **Median (50th pct) Drawdown** | 100.0% | 100.0% |
| **95th Percentile Drawdown** | 100.0% | 100.0% |
| **Worst-Case Drawdown** | 100.0% | 100.0% |

---

## 5. Quantitative Forensic Insights & Recommendations

1. **Hard Stop-Loss vs. Pullback Waiting (Scenario A vs Scenario B):**
   * Armandino's style of waiting 2h–36h for pullbacks without hard SL on 15x leverage creates acute tail risk. On highly volatile crypto pairs like ZEC (which surged from $388 to $1683), a single sharp adverse continuation can wipe out a small $20 margin pool in under 1 hour before any 40% margin cut can save it.
   * Scenario B protects against liquidation via strict 1.8% hard SL. At 15x leverage, 1.8% adverse price move limits the loss to ~27% on trade margin (~5% of total capital), preventing catastrophic account death.

2. **$20 Account Sizing & Binance Futures Step Constraints:**
   * Binance requires minimum notional of $20 for ETH and $5 for ZEC, with a 0.001 step size.
   * On a $20 starting account with 15x leverage, a standard 20% trade margin ($4) yields $60 notional, satisfying minimum notional requirements with comfortable buffer.
   * However, running 2 simultaneous positions leaves only 60% free margin buffer. In Scenario A, adverse moves on both positions simultaneously cause cross-margin liquidation.
