# RISK MANAGEMENT REPORT — APEX QUANT ENGINE

**Date:** 2026-08-16T07:09:08.379548+00:00

## Risk Scaling & Cap Findings

- **Tested Risk Levels:** 0.25%, 0.50%, 0.75%, 1.00%, 1.25%, 1.50%, 2.00%
- **Cap Analysis:**
  - **CAP_TRIGGERED:** True
  - **CAP_VALUE:** $3,000.00 Position Notional Cap (15% Max Position Margin at 2.0x Leverage)
  - **CAP_REASON:** PositionSizingEngine cap6_size enforced prop_rules.max_position_margin_pct (0.15) to prevent over-margining tight SL trades.

## Portfolio Exposure Compatibility Proof

- **BTC/USDT Max Leverage:** 2.0x
- **ETH/USDT Max Leverage:** 2.0x
- **Portfolio Exposure Limit:** 3.0x Equity ($30,000 on $10,000 account)
- **Mathematical Compatibility:**  
  When 1 BTC position ($3,000 notional) and 1 ETH position ($3,000 notional) are open simultaneously, aggregate notional is $6,000 (0.6x Portfolio Exposure), which strictly respects the 3.0x Portfolio Cap ($30,000). Compatibility is mathematically proven.
