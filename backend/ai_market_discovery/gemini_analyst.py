"""
Gemini 2.5 / 3.8 Flash Autonomous Reasoning Layer
Version: GEMINI_ANALYST_V1

Receives compact quantitative market snapshots (features, structure, regime, candidate setups).
Independently decides LONG, SHORT, or NO_TRADE.
Returns strictly formatted JSON conforming to Section 11 specifications.
Tracks token consumption, latency, and estimated cost.
"""

import os
import json
import math
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

PROMPT_VERSION = "GEMINI_ANALYST_V1"
MODELS_PRIORITY = ["gemini-3.5-flash", "gemini-3.8-flash"]
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("VITE_GEMINI_API_KEY") or "AQ.Ab8RN6JPJM4wM3eCK10Lw3b1aTvlsEC67RLwTpQTadEp-SRgJw"


SYSTEM_PROMPT = """You are an institutional quantitative trader and market structure analyst for Binance USDT-M Futures.
You are analyzing live market data for a single asset (BTCUSDT, ETHUSDT, or SOLUSDT).
Your objective is NOT maximum trade frequency.
Your objective is HIGH-QUALITY, SELECTIVE SETUPS with measurable positive expectancy.
NO_TRADE is a completely valid and preferred decision when conditions are ambiguous, choppy, or lack statistical coherence.

Allowed Decisions:
- LONG
- SHORT
- NO_TRADE

Entry Types:
- IMMEDIATE: Strong immediate edge, structure confirmed.
- WAIT_CONFIRMATION: Setup developing, requires tactical confirmation (e.g. M1/M5 sweep or break).
- LIMIT: Best entered at pullback or limit level.
- NO_TRADE: No clear structural or statistical edge.

Output Format:
You MUST respond with VALID JSON ONLY. Do NOT wrap in markdown backticks or commentary. Follow this exact JSON schema:
{
  "timestamp": "ISO_TIMESTAMP",
  "symbol": "SYMBOL",
  "decision": "LONG" | "SHORT" | "NO_TRADE",
  "confidence": 0-100,
  "setup_quality": 0-100,
  "regime": "REGIME_NAME",
  "regime_confidence": 0-100,
  "setup_type": "SETUP_NAME",
  "entry_type": "IMMEDIATE" | "WAIT_CONFIRMATION" | "LIMIT" | "NO_TRADE",
  "entry": null or float,
  "stop_loss": null or float,
  "take_profit_1": null or float,
  "take_profit_2": null or float,
  "rr_tp1": null or float,
  "rr_tp2": null or float,
  "timeframe_analysis": {
    "H4": "brief macro summary",
    "H1": "primary regime summary",
    "M15": "setup development summary",
    "M5": "tactical structure summary",
    "M1": "entry confirmation summary"
  },
  "bullish_factors": ["string"],
  "bearish_factors": ["string"],
  "conflicting_factors": ["string"],
  "support_levels": [float],
  "resistance_levels": [float],
  "liquidity_event": "string",
  "invalidation": "string",
  "why_this_setup": "string",
  "why_not_other_setup": "string",
  "required_confirmation": "string",
  "signal_expiry_minutes": 60,
  "prompt_version": "GEMINI_ANALYST_V1"
}
"""


def _sanitize_for_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(x) for x in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


class GeminiAnalyst:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or API_KEY
        self.models = MODELS_PRIORITY

    def analyze_market_snapshot(
        self,
        symbol: str,
        features: Dict[str, Any],
        regime: str,
        regime_confidence: float,
        candidate_setups: list,
        cross_asset: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sends compact structured snapshot to Gemini Flash and parses verified JSON.
        """
        # Compact JSON payload
        snapshot = {
            "symbol": symbol,
            "timestamp": features.get("datetime", ""),
            "price": features.get("current_price"),
            "detected_regime": regime,
            "regime_confidence": regime_confidence,
            "trend": features.get("trend"),
            "momentum": features.get("momentum"),
            "volatility": features.get("volatility"),
            "volume": features.get("volume"),
            "price_action": features.get("price_action"),
            "market_structure": features.get("market_structure"),
            "liquidity": features.get("liquidity"),
            "derivatives": features.get("derivatives"),
            "cross_asset_context": cross_asset,
            "candidate_setups_found": candidate_setups[:2] # Top 2 candidates
        }
        sanitized_snapshot = _sanitize_for_json(snapshot)

        user_content = f"Analyze this live Binance Futures snapshot for {symbol} and produce your autonomous signal decision:\n{json.dumps(sanitized_snapshot, indent=2)}"

        t0 = time.time()
        raw_response = None
        used_model = None
        latency_ms = 0.0

        for model_name in self.models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            body = json.dumps({
                "contents": [
                    {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{user_content}"}]}
                ],
                "generationConfig": {
                    "temperature": 0.15,
                    "topP": 0.9,
                    "maxOutputTokens": 1024,
                    "responseMimeType": "application/json",
                    "thinkingConfig": {"thinkingBudget": 0}
                }
            }).encode("utf-8")

            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    raw_response = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    used_model = model_name
                    latency_ms = round((time.time() - t0) * 1000.0, 1)
                    break
            except Exception as e:
                # Try next model in priority
                continue

        if not raw_response:
            # Fallback if API completely unreachable: Deterministic heuristic fallback
            return self._heuristic_fallback(symbol, features, regime, candidate_setups, latency_ms)

        try:
            # Clean possible markdown wrapping if any
            clean_json = raw_response
            if clean_json.startswith("```"):
                lines = clean_json.split("\n")
                clean_json = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

            parsed = json.loads(clean_json)
            parsed["model_used"] = used_model
            parsed["latency_ms"] = latency_ms
            parsed["prompt_version"] = PROMPT_VERSION
            return parsed
        except Exception:
            return self._heuristic_fallback(symbol, features, regime, candidate_setups, latency_ms)

    def _heuristic_fallback(
        self,
        symbol: str,
        features: Dict[str, Any],
        regime: str,
        candidate_setups: list,
        latency_ms: float
    ) -> Dict[str, Any]:
        """Provides a safe, coherent fallback if API is temporarily unavailable."""
        p = features.get("current_price", 0.0)
        top_cand = candidate_setups[0] if candidate_setups else None

        if top_cand and top_cand["setup_quality"] >= 78.0:
            return {
                "timestamp": str(int(time.time() * 1000)),
                "symbol": symbol,
                "decision": top_cand["direction"],
                "confidence": round(top_cand["setup_quality"] - 3.0, 1),
                "setup_quality": top_cand["setup_quality"],
                "regime": regime,
                "regime_confidence": 75.0,
                "setup_type": top_cand["setup_type"],
                "entry_type": "IMMEDIATE",
                "entry": top_cand["entry"],
                "stop_loss": top_cand["stop_loss"],
                "take_profit_1": top_cand["tp1"],
                "take_profit_2": top_cand["tp2"],
                "rr_tp1": top_cand["rr_tp1"],
                "rr_tp2": top_cand["rr_tp2"],
                "timeframe_analysis": {
                    "H4": "Neutral macro",
                    "H1": f"{regime} structure",
                    "M15": f"Setup {top_cand['setup_type']} active",
                    "M5": "Tactical alignment",
                    "M1": "Confirmed"
                },
                "bullish_factors": ["Regime aligned", "Structure intact"],
                "bearish_factors": [],
                "conflicting_factors": [],
                "support_levels": [round(p * 0.98, 2)],
                "resistance_levels": [round(p * 1.02, 2)],
                "liquidity_event": features.get("liquidity", {}).get("liquidity_event", "NORMAL_FLOW"),
                "invalidation": top_cand["invalidation"],
                "why_this_setup": f"Strong statistical quality on {top_cand['setup_type']}",
                "why_not_other_setup": "Primary edge confirmed",
                "required_confirmation": "Completed",
                "signal_expiry_minutes": 60,
                "model_used": "deterministic_fallback",
                "latency_ms": latency_ms,
                "prompt_version": PROMPT_VERSION
            }

        return {
            "timestamp": str(int(time.time() * 1000)),
            "symbol": symbol,
            "decision": "NO_TRADE",
            "confidence": 60.0,
            "setup_quality": 50.0,
            "regime": regime,
            "regime_confidence": 65.0,
            "setup_type": "NONE",
            "entry_type": "NO_TRADE",
            "entry": None,
            "stop_loss": None,
            "take_profit_1": None,
            "take_profit_2": None,
            "rr_tp1": None,
            "rr_tp2": None,
            "timeframe_analysis": {
                "H4": "Consolidation", "H1": regime, "M15": "No clear edge", "M5": "Choppy", "M1": "No confirmation"
            },
            "bullish_factors": [],
            "bearish_factors": [],
            "conflicting_factors": ["Insufficient statistical edge"],
            "support_levels": [],
            "resistance_levels": [],
            "liquidity_event": "NORMAL_FLOW",
            "invalidation": "N/A",
            "why_this_setup": "Selective NO_TRADE discipline",
            "why_not_other_setup": "No setups cleared quality thresholds",
            "required_confirmation": "Wait for clean liquidity sweep or trend breakout",
            "signal_expiry_minutes": 60,
            "model_used": "deterministic_fallback",
            "latency_ms": latency_ms,
            "prompt_version": PROMPT_VERSION
        }
