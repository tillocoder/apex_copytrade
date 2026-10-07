# APEX Autonomous AI Market Discovery — Historical Replay Forensic Audit

## 1. Executive Summary
- **Production Classification:** `NOT_SUPPORTED_BY_DATA`
- **Classification Rationale:** Net expectancy (-0.339R) after friction does not demonstrate repeatable mathematical edge.
- **Sample Size Rating:** `ADEQUATE_SAMPLE` (Total Executed: 109)
- **Total Hourly Analyses:** 1440
- **Selective NO_TRADE Count:** 1331 (92.4%)
- **Total Signals Discovered:** 109

## 2. Mathematical Expectancy & Friction Cost
- **Net Expectancy per Trade:** `-0.339R` (Gross: `-0.019R`)
- **95% Bootstrap Expectancy CI:** `[-0.516R, -0.164R]`
- **Win Rate:** `29.357798165137616%` (95% CI: `[21.1% - 37.6%]`)
- **Profit Factor (Net):** `0.38`
- **Total Realized Net R:** `-36.93R`
- **Max Drawdown:** `38.95R` (Average DD: `15.11R`)
- **Average MFE / MAE:** `0.7R` / `0.64R`
- **Average Holding Time:** `50.8 minutes`

## 3. Confidence Calibration (Does AI Confidence Predict Outcome?)
- **Status:** `UNRELIABLE_OR_INVERTED`
| Confidence Bucket | Signals | Win Rate | Net Expectancy | Total Net R |
| :--- | :--- | :--- | :--- | :--- |
| **50-60** | 0 | 0.0% | +0.000R | +0.00R |
| **60-70** | 0 | 0.0% | +0.000R | +0.00R |
| **70-75** | 0 | 0.0% | +0.000R | +0.00R |
| **75-80** | 50 | 26.0% | -0.242R | -12.12R |
| **80-85** | 34 | 20.6% | -0.639R | -21.74R |
| **85-90** | 25 | 48.0% | -0.123R | -3.07R |
| **90-95** | 0 | 0.0% | +0.000R | +0.00R |
| **95-100** | 0 | 0.0% | +0.000R | +0.00R |

## 4. Setup-Type Contribution
| Setup Family | Signals | Win Rate | Net Expectancy | Total Net R |
| :--- | :--- | :--- | :--- | :--- |
| **LIQUIDITY_SWEEP_REVERSAL** | 59 | 32.2% | -0.421R | -24.81R |
| **PULLBACK** | 6 | 33.3% | -0.338R | -2.03R |
| **TREND_CONTINUATION** | 44 | 25.0% | -0.229R | -10.09R |

## 5. Market Regime Matrix
| Market Regime | Signals | Win Rate | Net Expectancy | Total Net R |
| :--- | :--- | :--- | :--- | :--- |
| **REVERSAL** | 60 | 31.7% | -0.415R | -24.89R |
| **LOW_VOLATILITY** | 5 | 40.0% | -0.391R | -1.95R |
| **TRENDING_UP** | 22 | 22.7% | -0.329R | -7.24R |
| **TRENDING_DOWN** | 22 | 27.3% | -0.130R | -2.85R |

## 6. Symbol & Direction Matrix
| Asset / Direction | Signals | Win Rate | Net Expectancy | Total Net R |
| :--- | :--- | :--- | :--- | :--- |
| **BTCUSDT** | 109 | 29.4% | -0.339R | -36.93R |
| **ETHUSDT** | 0 | 0.0% | +0.000R | +0.00R |
| **SOLUSDT** | 0 | 0.0% | +0.000R | +0.00R |
| **Direction: LONG** | 59 | 30.5% | -0.376R | -22.20R |
| **Direction: SHORT** | 50 | 28.0% | -0.295R | -14.73R |

## 7. Baseline Strategy Comparison
| Strategy / Model | Win Rate | Net Expectancy | Profit Factor |
| :--- | :--- | :--- | :--- |
| **Autonomous Gemini Discovery** | **{summ.get('win_rate_pct')}%** | **{summ.get('avg_net_r', 0.0):+.3f}R** | **{summ.get('profit_factor')}** |
| Old Deterministic Engine | 25.2% | -0.220R | 0.74 |
| Buy-and-Hold Benchmark | 50.0% | -0.020R | 0.98 |
| Random Direction Benchmark | 48.0% | -0.080R | 0.89 |
| Simple EMA Trend Benchmark | 38.5% | -0.040R | 0.95 |
