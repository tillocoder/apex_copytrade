"""
Deterministic Python Validator
Ensures Gemini signals comply with strict quantitative and geometrical constraints:
- Symbol & Timestamp freshness
- Strict Long/Short Geometry:
  * LONG:  SL < entry < TP1 < TP2
  * SHORT: SL > entry > TP1 > TP2
- Minimum R:R >= 1.5
- Realistic Stop-Loss distance (0.2% to 5.0%)
- Quality Thresholds: AI_MIN_CONFIDENCE (75), AI_MIN_SETUP_QUALITY (70)
- Explicit REJECTED state when invalid (never repairs silently).
"""

from typing import Dict, Any, Tuple

AI_MIN_CONFIDENCE = 75.0
AI_MIN_SETUP_QUALITY = 70.0
AI_MIN_RR = 1.5
VALID_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}


class DeterministicValidator:
    def __init__(
        self,
        min_confidence: float = AI_MIN_CONFIDENCE,
        min_setup_quality: float = AI_MIN_SETUP_QUALITY,
        min_rr: float = AI_MIN_RR
    ):
        self.min_confidence = min_confidence
        self.min_setup_quality = min_setup_quality
        self.min_rr = min_rr

    def validate_signal(self, raw_signal: Dict[str, Any], current_market_price: float) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates the raw signal produced by Gemini.
        Returns: (is_valid: bool, rejection_reason: str, validated_signal: dict)
        """
        validated = dict(raw_signal)

        # 1. Symbol check
        sym = validated.get("symbol", "").upper().replace("/", "")
        if sym not in VALID_SYMBOLS:
            return False, f"Invalid symbol: {sym}", self._reject(validated, f"Invalid symbol: {sym}")

        decision = validated.get("decision", "NO_TRADE").upper()
        if decision == "NO_TRADE":
            validated["is_validated"] = True
            validated["rejection_reason"] = None
            return True, "PASSED_NO_TRADE", validated

        if decision not in ("LONG", "SHORT"):
            return False, f"Unrecognized decision: {decision}", self._reject(validated, f"Unrecognized decision: {decision}")

        # 2. Quality and Confidence thresholds
        conf = float(validated.get("confidence", 0.0) or 0.0)
        qual = float(validated.get("setup_quality", 0.0) or 0.0)

        if conf < self.min_confidence:
            return False, f"Confidence {conf} below threshold {self.min_confidence}", self._reject(validated, f"Confidence {conf} < {self.min_confidence}")

        if qual < self.min_setup_quality:
            return False, f"Setup quality {qual} below threshold {self.min_setup_quality}", self._reject(validated, f"Setup quality {qual} < {self.min_setup_quality}")

        # 3. Numeric price validation
        try:
            entry = float(validated.get("entry") or 0.0)
            sl = float(validated.get("stop_loss") or 0.0)
            tp1 = float(validated.get("take_profit_1") or 0.0)
            tp2 = float(validated.get("take_profit_2") or 0.0)
        except (ValueError, TypeError) as e:
            return False, f"Malformed price levels: {e}", self._reject(validated, "Non-numeric price levels")

        if entry <= 0 or sl <= 0 or tp1 <= 0 or tp2 <= 0:
            return False, "Price levels must be positive non-zero", self._reject(validated, "Zero or negative price levels")

        # 4. Entry proximity to current market price (must be within 1.5% of live market price)
        if current_market_price > 0:
            dev_pct = abs(entry - current_market_price) / current_market_price * 100.0
            if dev_pct > 1.5:
                return False, f"Entry {entry} deviates {dev_pct:.2f}% from market price {current_market_price}", self._reject(validated, f"Stale entry price (>{dev_pct:.2f}% dev)")

        # 5. Long / Short Geometry
        if decision == "LONG":
            if not (sl < entry < tp1 < tp2):
                return False, f"Invalid LONG geometry: SL({sl}) < Entry({entry}) < TP1({tp1}) < TP2({tp2}) violated", self._reject(validated, "Geometry violation (LONG)")
            risk = entry - sl
            reward1 = tp1 - entry
            reward2 = tp2 - entry
        else: # SHORT
            if not (sl > entry > tp1 > tp2):
                return False, f"Invalid SHORT geometry: SL({sl}) > Entry({entry}) > TP1({tp1}) > TP2({tp2}) violated", self._reject(validated, "Geometry violation (SHORT)")
            risk = sl - entry
            reward1 = entry - tp1
            reward2 = entry - tp2

        # 6. Stop-Loss distance reasonable check (between 0.2% and 5.0%)
        sl_dist_pct = (risk / entry) * 100.0
        if sl_dist_pct < 0.20 or sl_dist_pct > 5.0:
            return False, f"Stop-Loss distance {sl_dist_pct:.2f}% outside safe bounds (0.2% - 5.0%)", self._reject(validated, f"Unreasonable SL distance ({sl_dist_pct:.2f}%)")

        # 7. Minimum R:R check
        rr1 = reward1 / risk
        rr2 = reward2 / risk
        if rr1 < self.min_rr:
            return False, f"TP1 R:R {rr1:.2f} below minimum {self.min_rr}", self._reject(validated, f"R:R {rr1:.2f} < {self.min_rr}")

        # Update verified RR values
        validated["rr_tp1"] = round(rr1, 2)
        validated["rr_tp2"] = round(rr2, 2)
        validated["is_validated"] = True
        validated["rejection_reason"] = None
        return True, "PASSED", validated

    def _reject(self, sig: Dict[str, Any], reason: str) -> Dict[str, Any]:
        rejected = dict(sig)
        rejected["decision"] = "REJECTED"
        rejected["is_validated"] = False
        rejected["rejection_reason"] = reason
        return rejected
