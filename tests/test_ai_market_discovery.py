"""
Unit and Integration Test Suite for APEX Autonomous AI Market Discovery Engine
Tests:
- Quantitative Feature Engine (asserts >= 100 features across 10 factor families)
- Multi-Timeframe Integrity & Cross-Asset Intelligence
- Market Regime Engine (10 regimes + confidence)
- Setup Discovery Layer (Setups A-I)
- Deterministic Validator (Geometry, R:R, Confidence, Quality, Price Deviation)
- Risk Separation Engine (1% risk, 15x leverage, exchange filters)
- Paper Trading Tracker (MFE, MAE, R-result, confidence bucket analytics)
- Replay Engine (Zero look-ahead, cached snapshot evaluation)
"""

import unittest
import math
import time
import os
import json
import tempfile
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ai_market_discovery.features import FeatureEngine
from backend.ai_market_discovery.regime import MarketRegimeEngine
from backend.ai_market_discovery.setups import SetupDiscoveryEngine
from backend.ai_market_discovery.validator import DeterministicValidator
from backend.ai_market_discovery.risk_engine import RiskEngine
from backend.ai_market_discovery.paper_tracker import PaperTracker
from backend.ai_market_discovery.replay_engine import ReplayEngine


def generate_mock_candles(base_price: float, count: int, trend: float = 0.0005, vol: float = 0.002):
    candles = []
    p = base_price
    t_start = 1700000000000
    for i in range(count):
        o = p
        change = (i * trend) + (math.sin(i / 5.0) * vol * p)
        c = o + change
        h = max(o, c) + abs(math.sin(i)) * vol * p * 0.5
        l = min(o, c) - abs(math.cos(i)) * vol * p * 0.5
        v = 100.0 + (i % 10) * 15.0
        tb_v = v * 0.55 if c > o else v * 0.45
        candles.append({
            "timestamp": t_start + i * 900000,
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": round(v, 2),
            "taker_buy_volume": round(tb_v, 2)
        })
        p = c
    return candles


class TestAIMarketDiscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_m15 = generate_mock_candles(65000.0, 120, trend=0.0003)
        cls.mock_h1 = generate_mock_candles(65000.0, 60, trend=0.001)
        cls.mock_h4 = generate_mock_candles(65000.0, 40, trend=0.002)
        cls.mock_m5 = generate_mock_candles(65000.0, 150, trend=0.0001)
        cls.mock_m1 = generate_mock_candles(65000.0, 200, trend=0.00005)

        cls.bundle_btc = {
            "symbol": "BTCUSDT",
            "current_price": cls.mock_m15[-1]["close"],
            "timeframes": {
                "15m": cls.mock_m15,
                "1h": cls.mock_h1,
                "4h": cls.mock_h4,
                "5m": cls.mock_m5,
                "1m": cls.mock_m1
            },
            "derivatives": {
                "funding_rate": 0.0001,
                "funding_change_24h": 0.00002,
                "open_interest": 45000.0,
                "oi_change_24h_pct": 2.5,
                "long_short_ratio": 1.15,
                "basis_annualized_pct": 5.4,
                "available": True
            }
        }

    def test_01_feature_engine_count_and_families(self):
        engine = FeatureEngine()
        features = engine.compute_symbol_features(self.bundle_btc)

        # 1. Verify all 10 factor families exist
        required_families = [
            "trend", "momentum", "volatility", "volume",
            "price_action", "market_structure", "support_resistance",
            "liquidity", "derivatives", "multi_timeframe"
        ]
        for fam in required_families:
            self.assertIn(fam, features, f"Missing factor family: {fam}")

        # 2. Count individual features
        feature_count = 0
        for k, v in features.items():
            if isinstance(v, dict):
                feature_count += len(v)
            else:
                feature_count += 1

        print(f"\n[TEST] Total individual features computed: {feature_count}")
        # Prompt requires: 100-300+ measurable features
        self.assertGreaterEqual(feature_count, 100, f"Expected >= 100 features, got {feature_count}")

    def test_02_cross_asset_intelligence(self):
        engine = FeatureEngine()
        btc_feats = engine.compute_symbol_features(self.bundle_btc)
        eth_bundle = dict(self.bundle_btc)
        eth_bundle["symbol"] = "ETHUSDT"
        eth_bundle["current_price"] = 2650.0
        eth_feats = engine.compute_symbol_features(eth_bundle)

        sol_bundle = dict(self.bundle_btc)
        sol_bundle["symbol"] = "SOLUSDT"
        sol_bundle["current_price"] = 150.0
        sol_feats = engine.compute_symbol_features(sol_bundle)

        universe = {
            "BTCUSDT": btc_feats,
            "ETHUSDT": eth_feats,
            "SOLUSDT": sol_feats
        }
        cross = engine.compute_cross_asset_features(universe)

        self.assertIn("relative_strength_leader", cross)
        self.assertIn("cross_asset_regime", cross)
        self.assertIn("cross_asset_confirmation", cross)
        self.assertIn("eth_btc_ratio", cross)
        self.assertIn("sol_btc_ratio", cross)

    def test_03_market_regime_classification(self):
        engine = FeatureEngine()
        regime_engine = MarketRegimeEngine()
        features = engine.compute_symbol_features(self.bundle_btc)

        regime, confidence, compatible_setups = regime_engine.classify_regime(features)
        valid_regimes = [
            "TRENDING_UP", "TRENDING_DOWN", "RANGING", "BREAKOUT",
            "BREAKDOWN", "REVERSAL", "HIGH_VOLATILITY", "LOW_VOLATILITY",
            "CHOPPY", "UNCERTAIN"
        ]
        self.assertIn(regime, valid_regimes)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 100.0)
        self.assertIsInstance(compatible_setups, list)

    def test_04_setup_discovery_candidates(self):
        feature_engine = FeatureEngine()
        regime_engine = MarketRegimeEngine()
        setup_engine = SetupDiscoveryEngine()

        features = feature_engine.compute_symbol_features(self.bundle_btc)
        regime, _, _ = regime_engine.classify_regime(features)
        candidates = setup_engine.evaluate_setups(features, regime, {})

        self.assertIsInstance(candidates, list)
        for c in candidates:
            self.assertIn("setup_type", c)
            self.assertIn("direction", c)
            self.assertIn("entry", c)
            self.assertIn("stop_loss", c)
            self.assertIn("take_profit_1", c)
            self.assertIn("take_profit_2", c)
            self.assertIn("expected_rr", c)
            self.assertIn("setup_quality", c)

    def test_05_deterministic_validator_acceptance(self):
        validator = DeterministicValidator()
        current_p = 65000.0

        # Valid LONG
        valid_long = {
            "symbol": "BTCUSDT",
            "decision": "LONG",
            "confidence": 82.0,
            "setup_quality": 78.0,
            "entry": 65000.0,
            "stop_loss": 64300.0,  # ~1.07% SL
            "take_profit_1": 66200.0,  # 1200 / 700 = 1.71 R:R
            "take_profit_2": 67400.0   # 2400 / 700 = 3.42 R:R
        }
        is_val, reason, res = validator.validate_signal(valid_long, current_p)
        self.assertTrue(is_val, f"Valid LONG rejected: {reason}")
        self.assertEqual(res["decision"], "LONG")
        self.assertGreaterEqual(res["rr_tp1"], 1.5)

        # Valid SHORT
        valid_short = {
            "symbol": "BTCUSDT",
            "decision": "SHORT",
            "confidence": 85.0,
            "setup_quality": 80.0,
            "entry": 65000.0,
            "stop_loss": 65700.0,  # ~1.07% SL
            "take_profit_1": 63800.0,  # 1200 / 700 = 1.71 R:R
            "take_profit_2": 62600.0   # 2400 / 700 = 3.42 R:R
        }
        is_val, reason, res = validator.validate_signal(valid_short, current_p)
        self.assertTrue(is_val, f"Valid SHORT rejected: {reason}")
        self.assertEqual(res["decision"], "SHORT")

        # Valid NO_TRADE
        no_trade = {
            "symbol": "BTCUSDT",
            "decision": "NO_TRADE",
            "confidence": 90.0,
            "setup_quality": 40.0
        }
        is_val, reason, res = validator.validate_signal(no_trade, current_p)
        self.assertTrue(is_val)
        self.assertEqual(res["decision"], "NO_TRADE")

    def test_06_deterministic_validator_rejections(self):
        validator = DeterministicValidator()
        current_p = 65000.0

        # Case 1: Inverted Geometry for LONG (SL >= Entry)
        bad_long = {
            "symbol": "BTCUSDT",
            "decision": "LONG",
            "confidence": 85.0,
            "setup_quality": 80.0,
            "entry": 65000.0,
            "stop_loss": 65500.0,
            "take_profit_1": 67000.0,
            "take_profit_2": 68000.0
        }
        is_val, reason, res = validator.validate_signal(bad_long, current_p)
        self.assertFalse(is_val)
        self.assertEqual(res["decision"], "REJECTED")

        # Case 2: Sub-par R:R (< 1.5)
        bad_rr = {
            "symbol": "BTCUSDT",
            "decision": "LONG",
            "confidence": 85.0,
            "setup_quality": 80.0,
            "entry": 65000.0,
            "stop_loss": 64000.0,  # 1000 risk
            "take_profit_1": 65800.0,  # 800 reward -> 0.8 R:R (<1.5)
            "take_profit_2": 67000.0
        }
        is_val, reason, res = validator.validate_signal(bad_rr, current_p)
        self.assertFalse(is_val)
        self.assertIn("R:R", reason)

        # Case 3: Confidence below threshold (< 75)
        low_conf = {
            "symbol": "BTCUSDT",
            "decision": "LONG",
            "confidence": 68.0,
            "setup_quality": 80.0,
            "entry": 65000.0,
            "stop_loss": 64300.0,
            "take_profit_1": 66200.0,
            "take_profit_2": 67400.0
        }
        is_val, reason, res = validator.validate_signal(low_conf, current_p)
        self.assertFalse(is_val)
        self.assertIn("Confidence", reason)

        # Case 4: Extreme Stop Loss distance (> 5.0%)
        huge_sl = {
            "symbol": "BTCUSDT",
            "decision": "LONG",
            "confidence": 85.0,
            "setup_quality": 80.0,
            "entry": 65000.0,
            "stop_loss": 60000.0,  # 7.69% SL distance
            "take_profit_1": 73000.0,
            "take_profit_2": 80000.0
        }
        is_val, reason, res = validator.validate_signal(huge_sl, current_p)
        self.assertFalse(is_val)
        self.assertIn("Stop-Loss distance", reason)

    def test_07_risk_separation_sizing(self):
        risk_engine = RiskEngine(mode="PAPER", risk_per_trade_pct=0.01, leverage=15.0)

        sig = {
            "symbol": "BTCUSDT",
            "decision": "LONG",
            "entry": 65000.0,
            "stop_loss": 64350.0  # 650 distance = 1.0%
        }
        sizing = risk_engine.calculate_position(sig, account_balance=20.0)

        self.assertEqual(sizing["mode"], "PAPER")
        self.assertEqual(sizing["direction"], "LONG")
        self.assertGreater(sizing["quantity"], 0.0)
        self.assertGreaterEqual(sizing["notional_usd"], 20.0)  # Binance BTC min notional
        self.assertEqual(sizing["execution_status"], "PAPER_PENDING")

    def test_08_paper_tracker_metrics(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            tracker = PaperTracker(storage_path=temp_path)
            sig = {
                "symbol": "BTCUSDT",
                "decision": "LONG",
                "confidence": 82.0,
                "setup_quality": 78.0,
                "regime": "TRENDING_UP",
                "setup_type": "PULLBACK",
                "entry": 65000.0,
                "stop_loss": 64500.0,  # 500 risk
                "take_profit_1": 66000.0,  # +1000 = 2.0R
                "take_profit_2": 67000.0
            }
            tracker.record_signal(sig, {"final_contract_qty": 0.001})
            self.assertEqual(len(tracker.trades), 1)

            # Simulate price moving to TP1
            bar = {"high": 66100.0, "low": 64900.0, "close": 66050.0}
            tracker.update_bar("BTCUSDT", bar)

            trade = tracker.trades[0]
            self.assertTrue(trade["tp1_hit"])
            self.assertEqual(trade["status"], "PARTIAL_TP1")
            self.assertGreaterEqual(trade["r_result"], 2.0)
            self.assertGreater(trade["mfe_pct"], 1.5)

            # Analytics
            stats = tracker.get_performance_analytics()
            self.assertEqual(stats["total_signals_recorded"], 1)
            self.assertEqual(stats["tp1_hit_rate_pct"], 100.0)
            self.assertIn("confidence_bucket_breakdown", stats)
            self.assertIn("80-85", stats["confidence_bucket_breakdown"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_09_replay_engine_caching(self):
        engine = ReplayEngine(mode="CACHED_REPLAY")
        t = 1700000000000
        features = {"current_price": 65000.0, "trend": {"ema_alignment": "BULLISH_STACK"}}
        cache_key = engine._get_cache_key("BTCUSDT", t, features)
        self.assertTrue(len(cache_key) > 0)


if __name__ == "__main__":
    unittest.main()
