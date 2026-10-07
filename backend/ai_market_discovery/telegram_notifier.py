"""
Telegram Signal Dispatcher for Autonomous AI Market Discovery Engine
Formats clean, professional alerts for LONG and SHORT setups according to Section 23 specification.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AI_TELEGRAM_NOTIFIER")


class AITelegramNotifier:
    def __init__(self, notify_no_trade: bool = False):
        self.notify_no_trade = notify_no_trade
        self.bot = None
        try:
            from backend.telegram_bot import TelegramNotifier
            self.bot = TelegramNotifier()
        except Exception:
            try:
                from telegram_bot import TelegramNotifier
                self.bot = TelegramNotifier()
            except Exception:
                logger.warning("Could not initialize base TelegramNotifier; notifications will be logged only.")

    def format_signal_message(self, signal: Dict[str, Any]) -> str:
        symbol = signal.get("symbol", "BTCUSDT")
        decision = signal.get("decision", "NO_TRADE")
        conf = signal.get("confidence", 0)
        qual = signal.get("setup_quality", 0)
        regime = signal.get("regime", "UNKNOWN")
        setup = signal.get("setup_type", "UNKNOWN")
        entry = signal.get("entry")
        sl = signal.get("stop_loss")
        tp1 = signal.get("take_profit_1")
        tp2 = signal.get("take_profit_2")
        rr = signal.get("rr_tp1", 0)
        mtf = signal.get("timeframe_analysis", {})
        reasons = signal.get("bullish_factors", []) if decision == "LONG" else signal.get("bearish_factors", [])
        inval = signal.get("invalidation", "Structure invalidation")

        reasons_text = "\n".join(f"• {r}" for r in reasons[:3]) if reasons else "• High-probability structural alignment"

        msg = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 <b>AI SIGNAL: {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>{decision}</b>\n\n"
            f"<b>Confidence:</b> {conf}%\n"
            f"<b>Setup Quality:</b> {qual}%\n"
            f"<b>Regime:</b> {regime}\n"
            f"<b>Setup:</b> {setup}\n\n"
            f"<b>Entry:</b> {entry}\n"
            f"<b>SL:</b> {sl}\n"
            f"<b>TP1:</b> {tp1}\n"
            f"<b>TP2:</b> {tp2}\n\n"
            f"<b>R:R (TP1):</b> {rr}\n\n"
            f"<b>Timeframe Hierarchy:</b>\n"
            f"H4: {mtf.get('H4', 'Neutral')}\n"
            f"H1: {mtf.get('H1', 'Neutral')}\n"
            f"M15: {mtf.get('M15', 'Neutral')}\n"
            f"M5: {mtf.get('M5', 'Neutral')}\n"
            f"M1: {mtf.get('M1', 'Confirmation')}\n\n"
            f"<b>Key Reasons:</b>\n"
            f"{reasons_text}\n\n"
            f"<b>Invalidation:</b>\n"
            f"{inval}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        return msg

    def broadcast_signal(self, signal: Dict[str, Any]):
        decision = signal.get("decision", "NO_TRADE")
        if decision == "NO_TRADE" and not self.notify_no_trade:
            return

        if not signal.get("is_validated", False):
            return  # Do not broadcast rejected signals

        text = self.format_signal_message(signal)
        if self.bot and hasattr(self.bot, "broadcast_message"):
            try:
                self.bot.broadcast_message(text)
            except Exception as e:
                logger.error(f"Failed to broadcast AI signal to Telegram: {e}")
        else:
            logger.info(f"[TELEGRAM BROADCAST SIMULATED]\n{text}")
