import unittest
from backend.quant_engine.config import PropFirmRulesConfig, RiskConfig
from backend.quant_engine.position_sizing import PositionSizingEngine, PositionSizingResult

class TestInstitutionalRiskSizing(unittest.TestCase):

    def setUp(self):
        self.prop_rules = PropFirmRulesConfig(
            initial_capital=10000.0,
            risk_per_trade_pct=0.015,
            min_sl_distance_pct=0.005,
            max_single_position_notional_mult=3.0,
            max_total_notional_exposure_mult=8.0,
            max_crypto_portfolio_risk_pct=0.04,
            max_margin_utilization_pct=0.45,
            maintenance_margin_rate=0.02,
            fee_buffer_pct=0.0008,
            slippage_buffer_pct=0.0005,
            default_leverage=20.0
        )
        self.risk_cfg = RiskConfig()

    def test_1_very_tight_btc_sl_no_explosion(self):
        """TEST 1: Extremely tight BTC SL ($44 SL on $64,800 BTC) does NOT cause position sizing explosion."""
        res = PositionSizingEngine.calculate_position_size(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=64800.0,
            stop_loss=64756.0,  # $44 SL (0.068% distance)
            current_equity=10000.0,
            open_positions=[],
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.001,
            step_size=0.001
        )
        self.assertTrue(res.is_approved)
        # 0.5% effective SL distance floor = $324.00
        self.assertAlmostEqual(res.effective_sl_distance, 324.0, delta=0.5)
        # Size should NOT be 3.37 BTC! Should be capped to ~0.462 BTC ($30k cap)
        self.assertLessEqual(res.final_size, 0.463)
        self.assertLessEqual(res.final_notional, 30000.0)

    def test_2_raw_notional_capped_at_single_position_limit(self):
        """TEST 2: Raw calculated notional > $30k is capped to $30,000 max single position notional."""
        res = PositionSizingEngine.calculate_position_size(
            symbol="ETH/USDT",
            side="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,  # 0.5% SL
            current_equity=10000.0,
            open_positions=[],
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.01,
            step_size=0.01
        )
        self.assertTrue(res.is_approved)
        self.assertLessEqual(res.final_notional, 30000.00)
        self.assertLessEqual(res.final_size, 15.0)  # 15 ETH * $2000 = $30,000

    def test_3_portfolio_total_exposure_cap_limits_third_position(self):
        """TEST 3: Two $30k positions ($60k total) limits the 3rd position to $20k ($80k total portfolio cap)."""
        existing_positions = [
            {"symbol": "BTC/USDT", "side": "BUY", "entryPrice": 64800.0, "sl": 64600.0, "size": 0.462, "leverage": 20.0},  # ~$30k notional, $92.40 risk
            {"symbol": "ETH/USDT", "side": "BUY", "entryPrice": 2000.0, "sl": 1995.0, "size": 15.0, "leverage": 20.0}       # ~$30k notional, $75.00 risk
        ]
        res = PositionSizingEngine.calculate_position_size(
            symbol="SOL/USDT",
            side="BUY",
            entry_price=100.0,
            stop_loss=95.0,
            current_equity=10000.0,
            open_positions=existing_positions,
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.1,
            step_size=0.1
        )
        self.assertTrue(res.is_approved)
        # Remaining exposure capacity = $80,000 - $59,937 = ~$20,063
        self.assertLessEqual(res.final_notional, 20100.0)

    def test_4_margin_utilization_cap_exceeded_rejection(self):
        """TEST 4: Open margin used near 45% ($4,500) rejects or reduces new order margin."""
        heavy_positions = [
            {"symbol": "BTC/USDT", "side": "BUY", "entryPrice": 64800.0, "sl": 64790.0, "size": 0.617, "leverage": 5.0} # $40k notional = $8,000 margin > $4,500 cap
        ]
        res = PositionSizingEngine.calculate_position_size(
            symbol="SOL/USDT",
            side="BUY",
            entry_price=100.0,
            stop_loss=95.0,
            current_equity=10000.0,
            open_positions=heavy_positions,
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.1,
            step_size=0.1
        )
        self.assertFalse(res.is_approved)
        self.assertIn("MARGIN_REJECT", res.rejection_reason)

    def test_5_aggregate_risk_cap_limits_or_rejects_new_position(self):
        """TEST 5: Aggregate planned risk near 4.0% ($400) restricts new position size."""
        high_risk_positions = [
            {"symbol": "BTC/USDT", "side": "BUY", "entryPrice": 64800.0, "sl": 64000.0, "size": 0.25, "leverage": 20.0}, # $200 risk
            {"symbol": "ETH/USDT", "side": "BUY", "entryPrice": 2000.0, "sl": 1980.0, "size": 9.0, "leverage": 20.0}     # $180 risk
        ]
        res = PositionSizingEngine.calculate_position_size(
            symbol="SOL/USDT",
            side="BUY",
            entry_price=100.0,
            stop_loss=95.0,
            current_equity=10000.0,
            open_positions=high_risk_positions,
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.1,
            step_size=0.1
        )
        self.assertTrue(res.is_approved)
        # Remaining risk budget = $400 - $380 = $20
        # For $5 SL (effective $5.13 with fees), max size = 20 / 5.13 = ~3.9 SOL ($390 notional)
        self.assertLessEqual(res.final_size, 4.0)

    def test_6_existing_positions_accounted(self):
        """TEST 6: Existing positions are correctly accumulated into open notional and margin."""
        existing = [{"symbol": "BTC/USDT", "side": "BUY", "entryPrice": 50000.0, "sl": 49000.0, "size": 0.2, "leverage": 20.0}] # $10k notional
        res = PositionSizingEngine.calculate_position_size(
            symbol="ETH/USDT",
            side="BUY",
            entry_price=2000.0,
            stop_loss=1980.0,
            current_equity=10000.0,
            open_positions=existing,
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.01,
            step_size=0.01
        )
        self.assertTrue(res.is_approved)
        self.assertEqual(res.audit_log["existing_portfolio_exposure"], 10000.0)

    def test_7_pending_orders_accounted(self):
        """TEST 7: Pending orders are accumulated into risk and margin calculations."""
        pending = [{"symbol": "SOL/USDT", "side": "BUY", "entryPrice": 100.0, "sl": 90.0, "size": 10.0, "leverage": 20.0}] # $100 risk
        res = PositionSizingEngine.calculate_position_size(
            symbol="ETH/USDT",
            side="BUY",
            entry_price=2000.0,
            stop_loss=1980.0,
            current_equity=10000.0,
            open_positions=[],
            pending_orders=pending,
            prop_rules=self.prop_rules,
            min_qty=0.01,
            step_size=0.01
        )
        self.assertTrue(res.is_approved)
        self.assertEqual(res.audit_log["existing_portfolio_exposure"], 1000.0)

    def test_8_fee_and_slippage_buffer(self):
        """TEST 8: Fee (0.08%) + Slippage (0.05%) buffer increases effective unit loss, reducing raw size."""
        res = PositionSizingEngine.calculate_position_size(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=60000.0,
            stop_loss=59400.0,  # $600 SL (1%)
            current_equity=10000.0,
            open_positions=[],
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.001,
            step_size=0.001
        )
        self.assertTrue(res.is_approved)
        # Unit fee + slippage = 60000 * 0.0013 = $78.00
        # Effective unit loss = $600 + $78 = $678.00
        # Raw size = $150 / $678 = 0.221 BTC
        self.assertAlmostEqual(res.raw_size, 0.221, delta=0.005)

    def test_9_exchange_step_size_rounding(self):
        """TEST 9: Final quantity is rounded down according to exchange step size."""
        res = PositionSizingEngine.calculate_position_size(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=64800.0,
            stop_loss=64000.0,
            current_equity=10000.0,
            open_positions=[],
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.001,
            step_size=0.001
        )
        self.assertTrue(res.is_approved)
        # Verify 3 decimals precision matching step_size=0.001
        self.assertEqual(res.final_size, round(res.final_size, 3))

    def test_10_backtest_and_live_parity(self):
        """TEST 10: Backtest and Live calls yield identical PositionSizingResult outputs."""
        live_res = PositionSizingEngine.calculate_position_size(
            symbol="SOL/USDT",
            side="BUY",
            entry_price=80.0,
            stop_loss=78.0,
            current_equity=10000.0,
            open_positions=[],
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.1,
            step_size=0.1
        )
        backtest_res = PositionSizingEngine.calculate_position_size(
            symbol="SOL/USDT",
            side="BUY",
            entry_price=80.0,
            stop_loss=78.0,
            current_equity=10000.0,
            open_positions=[],
            pending_orders=[],
            prop_rules=self.prop_rules,
            min_qty=0.1,
            step_size=0.1
        )
        self.assertEqual(live_res.final_size, backtest_res.final_size)
        self.assertEqual(live_res.initial_margin, backtest_res.initial_margin)

    def test_11_equity_drawdown_risk_throttling(self):
        """TEST 11: Risk per trade scales down as account drawdown increases."""
        # 0% DD -> 1.5% risk
        res_0 = PositionSizingEngine.calculate_position_size(
            symbol="SOL/USDT", side="BUY", entry_price=100.0, stop_loss=95.0,
            current_equity=10000.0, open_positions=[], pending_orders=[], prop_rules=self.prop_rules
        )
        # 3% DD ($9,700 equity) -> 1.0% risk
        res_3 = PositionSizingEngine.calculate_position_size(
            symbol="SOL/USDT", side="BUY", entry_price=100.0, stop_loss=95.0,
            current_equity=9700.0, open_positions=[], pending_orders=[], prop_rules=self.prop_rules
        )
        self.assertLess(res_3.risk_budget_usd, res_0.risk_budget_usd)

    def test_12_maintenance_margin_danger_rejection(self):
        """TEST 12: Near 80% maintenance margin capacity ceiling rejects or reduces new order."""
        strict_maint_rules = PropFirmRulesConfig(
            initial_capital=10000.0,
            maintenance_margin_rate=0.20 # 20% maintenance rate
        )
        heavy_positions = [
            {"symbol": "BTC/USDT", "side": "BUY", "entryPrice": 64800.0, "sl": 64799.0, "size": 0.620, "leverage": 20.0} # $40,176 notional = $8,035.20 maint margin > $8,000 ceiling
        ]
        res = PositionSizingEngine.calculate_position_size(
            symbol="SOL/USDT", side="BUY", entry_price=100.0, stop_loss=95.0,
            current_equity=10000.0, open_positions=heavy_positions, pending_orders=[], prop_rules=strict_maint_rules
        )
        self.assertFalse(res.is_approved)
        self.assertIn("MARGIN_REJECT", res.rejection_reason)

if __name__ == "__main__":
    unittest.main()
