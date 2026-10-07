"""
Autonomous AI Market Discovery Service
Master Orchestrator for:
- Data Ingestion (BTCUSDT, ETHUSDT, SOLUSDT)
- Multi-Timeframe Feature Engineering (100-300+ features)
- Regime & Setup Discovery
- Gemini 2.5/3.8 Flash Autonomous Reasoning
- Deterministic Validation & Risk Separation
- Paper Tracking & Performance Analytics
- Hourly Scheduler & Telegram Dispatcher
"""

import os
import math
import time
import json
import logging
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .binance_feed import BinanceFeed
from .features import FeatureEngine
from .regime import MarketRegimeEngine
from .setups import SetupDiscoveryEngine
from .gemini_analyst import GeminiAnalyst
from .validator import DeterministicValidator
from .risk_engine import RiskEngine
from .paper_tracker import PaperTracker
from .telegram_notifier import AITelegramNotifier

logger = logging.getLogger("AI_MARKET_DISCOVERY_SERVICE")

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "ai_market_discovery")


class AIMarketDiscoveryService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        os.makedirs(STORAGE_DIR, exist_ok=True)
        self.feed = BinanceFeed()
        self.feature_engine = FeatureEngine()
        self.regime_engine = MarketRegimeEngine()
        self.setup_engine = SetupDiscoveryEngine()
        self.analyst = GeminiAnalyst()
        self.validator = DeterministicValidator()
        self.risk_engine = RiskEngine(mode="PAPER", risk_per_trade_pct=0.01, leverage=15.0)
        self.tracker = PaperTracker()
        self.notifier = AITelegramNotifier(notify_no_trade=False)

        self.last_cycle_timestamp = 0
        self.last_processed_h1_ts = 0
        self.is_running = False
        self.cycle_lock = threading.Lock()

        # Cached state for instant API retrieval
        self.latest_cards: Dict[str, Any] = self._load_persisted_cards()
        self._scheduler_thread = None

    def _clean_json_obj(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._clean_json_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_json_obj(x) for x in obj]
        elif isinstance(obj, float):
            return None if math.isnan(obj) or math.isinf(obj) else obj
        return obj

    def _load_persisted_cards(self) -> Dict[str, Any]:
        path = os.path.join(STORAGE_DIR, "latest_cards.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return self._clean_json_obj(json.load(f))
            except Exception:
                pass
        return {}

    def _save_persisted_cards(self):
        path = os.path.join(STORAGE_DIR, "latest_cards.json")
        try:
            self.latest_cards = self._clean_json_obj(self.latest_cards)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.latest_cards, f, indent=2)
        except Exception as e:
            logger.error(f"Error persisting latest cards: {e}")

    def run_full_analysis_cycle(self, force: bool = False) -> Dict[str, Any]:
        """
        Executes one complete autonomous analysis cycle for BTCUSDT, ETHUSDT, SOLUSDT.
        """
        with self.cycle_lock:
            t0 = time.time()
            now_iso = datetime.now(timezone.utc).isoformat()
            logger.info("Starting Autonomous AI Market Discovery Cycle...")

            # 1. Fetch live multi-timeframe market data & derivatives
            bundle = self.feed.fetch_universe_bundle()

            # Update open paper trades with current high/low/close
            live_candle_map = {}
            for sym, b in bundle.items():
                m15 = b.get("timeframes", {}).get("15m", [])
                if m15:
                    live_candle_map[sym] = m15[-1]
            self.tracker.update_open_trades(live_candle_map)

            # 2. Compute 100-300+ features per asset
            features_map = {}
            for sym, b in bundle.items():
                features_map[sym] = self.feature_engine.compute_symbol_features(b)

            # 3. Cross-Asset Intelligence
            cross_asset = self.feature_engine.compute_cross_asset_features(features_map)

            results = {}

            # 4. Independent asset analysis in parallel
            from concurrent.futures import ThreadPoolExecutor

            def _analyze_single_symbol(sym: str) -> Optional[Dict[str, Any]]:
                feat = features_map.get(sym, {})
                if not feat or "error" in feat:
                    return None

                curr_p = bundle[sym].get("current_price", 0.0)
                regime, reg_conf, compatible_setups = self.regime_engine.classify_regime(feat)
                candidates = self.setup_engine.evaluate_setups(feat, regime, cross_asset)

                # Call Gemini Autonomous Reasoning
                raw_sig = self.analyst.analyze_market_snapshot(
                    symbol=sym,
                    features=feat,
                    regime=regime,
                    regime_confidence=reg_conf,
                    candidate_setups=candidates,
                    cross_asset=cross_asset
                )

                # Deterministic Validation
                is_valid, reason, validated_sig = self.validator.validate_signal(raw_sig, curr_p)

                # Sizing & Risk calculation
                position_profile = self.risk_engine.calculate_position(validated_sig, account_balance=20.0)

                # Record in paper tracker and notify if signal is actionable
                if validated_sig.get("decision") in ("LONG", "SHORT") and is_valid:
                    self.tracker.record_signal(validated_sig, position_profile)
                    self.notifier.broadcast_signal(validated_sig)

                # Assemble complete dashboard card
                card = {
                    "symbol": sym,
                    "price": curr_p,
                    "analyzed_at": now_iso,
                    "data_quality_score": bundle[sym].get("data_quality_score", 100.0),
                    "api_latency_ms": bundle[sym].get("avg_api_latency_ms", 0.0),
                    "gemini_latency_ms": validated_sig.get("latency_ms", 0.0),
                    "model_used": validated_sig.get("model_used", "gemini-3.5-flash"),
                    "prompt_version": validated_sig.get("prompt_version", "GEMINI_ANALYST_V1"),
                    "regime": regime,
                    "regime_confidence": reg_conf,
                    "decision": validated_sig.get("decision", "NO_TRADE"),
                    "is_valid": is_valid,
                    "rejection_reason": reason if not is_valid else None,
                    "confidence": validated_sig.get("confidence", 0),
                    "setup_quality": validated_sig.get("setup_quality", 0),
                    "setup_type": validated_sig.get("setup_type", "NONE"),
                    "entry_type": validated_sig.get("entry_type", "NO_TRADE"),
                    "entry": validated_sig.get("entry"),
                    "stop_loss": validated_sig.get("stop_loss"),
                    "take_profit_1": validated_sig.get("take_profit_1"),
                    "take_profit_2": validated_sig.get("take_profit_2"),
                    "rr_tp1": validated_sig.get("rr_tp1"),
                    "rr_tp2": validated_sig.get("rr_tp2"),
                    "timeframe_analysis": validated_sig.get("timeframe_analysis", {}),
                    "bullish_factors": validated_sig.get("bullish_factors", []),
                    "bearish_factors": validated_sig.get("bearish_factors", []),
                    "conflicting_factors": validated_sig.get("conflicting_factors", []),
                    "support_levels": validated_sig.get("support_levels", []),
                    "resistance_levels": validated_sig.get("resistance_levels", []),
                    "liquidity_event": validated_sig.get("liquidity_event", "NORMAL_FLOW"),
                    "invalidation": validated_sig.get("invalidation", ""),
                    "why_this_setup": validated_sig.get("why_this_setup", ""),
                    "required_confirmation": validated_sig.get("required_confirmation", ""),
                    "signal_expiry_minutes": validated_sig.get("signal_expiry_minutes", 60),
                    "position_sizing": position_profile,
                    "factor_groups": {
                        "trend": feat.get("trend"),
                        "momentum": feat.get("momentum"),
                        "volatility": feat.get("volatility"),
                        "volume": feat.get("volume"),
                        "structure": feat.get("market_structure"),
                        "liquidity": feat.get("liquidity"),
                        "derivatives": feat.get("derivatives"),
                        "cross_asset": cross_asset
                    }
                }
                return card

            target_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            with ThreadPoolExecutor(max_workers=len(target_symbols)) as executor:
                futures = {executor.submit(_analyze_single_symbol, s): s for s in target_symbols}
                for fut in futures:
                    sym = futures[fut]
                    try:
                        c = fut.result()
                        if c:
                            results[sym] = c
                    except Exception as e:
                        logger.error(f"Error analyzing {sym}: {e}")

            self.latest_cards = results
            self.last_cycle_timestamp = int(time.time() * 1000)
            self._save_persisted_cards()

            elapsed = round(time.time() - t0, 2)
            logger.info(f"AI Market Discovery Cycle completed in {elapsed}s.")
            return {
                "status": "SUCCESS",
                "timestamp": self.last_cycle_timestamp,
                "elapsed_seconds": elapsed,
                "cross_asset": cross_asset,
                "cards": results
            }

    def start_hourly_scheduler(self):
        """Starts background loop executing once every hour on confirmed H1 candle."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return

        def _loop():
            self.is_running = True
            logger.info("Autonomous AI Market Discovery hourly scheduler started.")
            while self.is_running:
                try:
                    # Check if at least 50 minutes passed since last cycle
                    now_ts = time.time()
                    if (now_ts - self.last_cycle_timestamp / 1000.0) >= 3000.0 or not self.latest_cards:
                        self.run_full_analysis_cycle()
                except Exception as e:
                    logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)

        self._scheduler_thread = threading.Thread(target=_loop, daemon=True, name="AI_Market_Discovery_Scheduler")
        self._scheduler_thread.start()

    def get_cards(self) -> Dict[str, Any]:
        if not self.latest_cards:
            self.run_full_analysis_cycle()
        return self._clean_json_obj(self.latest_cards)

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.tracker.get_recent_history(limit)

    def get_analytics(self) -> Dict[str, Any]:
        return self.tracker.get_analytics()
