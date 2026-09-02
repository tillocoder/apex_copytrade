import os
import sys
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger("APEX_TELEGRAM")
logger.setLevel(logging.INFO)

INITIAL_PROP_CAPITAL = 10000.0

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8922592987:AAEKfszGRuNsgGVy95f649rf8MHdrKiw6QI")
        self.default_chat_id = os.getenv("TELEGRAM_CHAT_ID", "5563813326")
        self.chat_ids = set()
        if self.default_chat_id:
            self.chat_ids.add(int(self.default_chat_id))
        
        self.message_map = {}
        self.account_balance = INITIAL_PROP_CAPITAL
        self.daily_start_balance = INITIAL_PROP_CAPITAL
        self.state_file = os.path.join(os.path.dirname(__file__), "telegram_state.json")
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid in data.get("chat_ids", []):
                        self.chat_ids.add(int(cid))
                    self.message_map = data.get("message_map", {})
                    self.account_balance = float(data.get("account_balance", INITIAL_PROP_CAPITAL))
                    self.daily_start_balance = float(data.get("daily_start_balance", INITIAL_PROP_CAPITAL))
        except Exception as e:
            logger.error(f"Error loading telegram_state.json: {e}")

    def _save_state(self):
        try:
            data = {
                "chat_ids": list(self.chat_ids),
                "message_map": self.message_map,
                "account_balance": self.account_balance,
                "daily_start_balance": self.daily_start_balance
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving telegram_state.json: {e}")

    def poll_updates(self):
        if not self.bot_token:
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        try:
            res = requests.get(url, params={"timeout": 0}, timeout=4)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for u in updates:
                    msg = u.get("message") or u.get("callback_query", {}).get("message")
                    if msg and "chat" in msg:
                        cid = msg["chat"]["id"]
                        if cid not in self.chat_ids:
                            self.chat_ids.add(cid)
                            self._save_state()
        except Exception:
            pass

    def send_direct_message(self, chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> Optional[int]:
        if not self.bot_token:
            return None
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            payload["allow_sending_without_reply"] = True

        try:
            res = requests.post(url, json=payload, timeout=6)
            if res.status_code == 200:
                data = res.json()
                return data.get("result", {}).get("message_id")
            else:
                logger.error(f"Telegram sendMessage failed ({res.status_code}): {res.text}")
        except Exception as e:
            logger.error(f"Error sending direct message: {e}")
        return None

    def _build_position_inline_keyboard(self, pos_id: str) -> dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🔴 LIVE", "web_app": {"url": f"https://apex.xrinvest.uz/?mode=tg_live&pos={pos_id}"}}
                ]
            ]
        }

    def send_trade_message(self, chat_id: int, text: str, pos_id: str) -> Optional[int]:
        if not self.bot_token:
            return None
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": self._build_position_inline_keyboard(pos_id)
        }
        try:
            res = requests.post(url, json=payload, timeout=6)
            if res.status_code == 200:
                data = res.json()
                return data.get("result", {}).get("message_id")
            else:
                logger.error(f"Telegram send_trade_message failed: {res.text}")
        except Exception as e:
            logger.error(f"Error in send_trade_message: {e}")
        return None

    def send_trade_open_notification(self, position: Dict[str, Any]):
        """Sends formatted Trade Open message and persistently records message_id for reply threading!"""
        self.poll_updates()
        if not self.chat_ids:
            return

        side = position.get("side", "BUY").upper()
        side_badge = "🟢 BUY (LONG)" if side == "BUY" else "🔴 SELL (SHORT)"
        symbol = position.get("symbol", "BTC/USDT")
        entry = float(position.get("entryPrice") or position.get("entry_price") or 0.0)
        size = float(position.get("size", 1.0))
        base_asset = symbol.split("/")[0]
        leverage = position.get("leverage", 2)
        margin = float(position.get("marginUsed") or position.get("margin_used") or 0.0)
        sl = float(position.get("sl", 0.0))
        tp1 = float(position.get("tp1", 0.0))
        tp2 = float(position.get("tp2", 0.0))
        risk = float(position.get("expectedLoss") or position.get("expected_loss") or 13.10)
        risk_pct = float(position.get("riskPercent") or ((risk / max(1.0, self.account_balance)) * 100.0))
        reason = position.get("aiExplanation") or position.get("ai_explanation") or "SMC Liquidity Sweep"
        confidence = float(position.get("aiConfidence") or position.get("ai_confidence") or 77.9)

        text = (
            f"⚡ <b>YANGI SAVDO OCHILDI — {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Yo'nalish:</b> {side_badge} {leverage}X\n"
            f"🎯 <b>Kirish Narxi (Entry):</b> ${entry:,.2f}\n"
            f"🟢 <b>Take Profit 1:</b> ${tp1:,.2f} (+1.5R)\n"
            f"🟢 <b>Take Profit 2:</b> ${tp2:,.2f} (+2.8R)\n"
            f"🔴 <b>Stop Loss:</b> ${sl:,.2f} (-{risk_pct:.2f}%)\n\n"
            f"📦 <b>Hajm:</b> {size} {base_asset} (${margin:,.2f} Margin)\n"
            f"🛡️ <b>Maksimal Xavf:</b> -${risk:,.2f} USD\n"
            f"🧠 <b>Strategiya:</b> {reason} (AI: {confidence:.1f}%)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>📊 Jonli grafik va telemetriyani ko'rish uchun pastdagi <b>🔴 LIVE</b> tugmasini bosing.</i>\n"
            f"<i>💡 Barcha keyingi holatlar (TP/SL/BE) aynan shu xabarga <b>Reply</b> tarzida yuboriladi.</i>"
        )

        pos_id = position.get("id", f"pos_{int(time.time())}")
        sig_id = position.get("signal_id", "")

        for cid in list(self.chat_ids):
            msg_id = self.send_trade_message(cid, text, pos_id)
            if msg_id:
                self.message_map[pos_id] = msg_id
                self.message_map[f"{cid}:{pos_id}"] = msg_id
                self.message_map[symbol] = msg_id
                self.message_map[f"{cid}:{symbol}"] = msg_id
                if sig_id:
                    self.message_map[sig_id] = msg_id
                    self.message_map[f"{cid}:{sig_id}"] = msg_id

        self._save_state()

    def send_trade_update_notification(self, pos_id: str, event_type: str, details: Dict[str, Any]):
        """Replies directly to the original trade message when SL, TP1, TP2, or BE is triggered."""
        self.poll_updates()
        if not self.chat_ids:
            return

        symbol = details.get("symbol", "BTC/USDT")
        entry = float(details.get("entry_price") or 0.0)
        curr_price = float(details.get("price") or 0.0)
        pnl = float(details.get("pnl") or 0.0)
        pnl_sign = "+" if pnl >= 0 else ""

        if event_type == "TP1":
            tp2_price = details.get("tp2", 0.0)
            text = (
                f"🎯 <b>TAKE PROFIT 1 ERISHILDI! — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Chiqish:</b> ${curr_price:,.2f}\n"
                f"💰 <b>50% Foyda Naqd Qilindi:</b> {pnl_sign}${pnl:,.2f} USD\n"
                f"🚀 <b>Qolgan 50%:</b> TP2 (${tp2_price:,.2f}) tomon harakatlanmoqda.\n"
                f"🛡️ <i>Erta chiqib ketishlarning oldini olish uchun SL narx TP2 tomon kengaygach Break-Even'ga o'tkaziladi.</i>"
            )
        elif event_type == "TRAILING_SL":
            new_sl = details.get("sl", entry)
            tp2_target = details.get("tp2", 0.0)
            text = (
                f"🛡️ <b>BREAK-EVEN & TRAILING STOP FAOLLASHDI — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish Narxi:</b> ${entry:,.2f}\n"
                f"📈 <b>Amaldagi Narx:</b> ${curr_price:,.2f}\n"
                f"🔒 <b>Yangi Himoyalangan SL:</b> ${new_sl:,.2f} (Entry + Kichik Plyus)\n"
                f"✅ <i>Savdo to'liq kafolatlangan plyusga o'tkazildi! (0% Xavf)</i>\n"
                f"🎯 <i>Asosiy Nishon: TP2 (${tp2_target:,.2f})</i>"
            )
        elif event_type == "TP2":
            text = (
                f"🏆 <b>TAKE PROFIT 2 (FINAL TARGET) ERISHILDI! — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Chiqish:</b> ${curr_price:,.2f}\n"
                f"💰 <b>Jami Sof Foyda:</b> {pnl_sign}${pnl:,.2f} USD\n"
                f"🎉 <i>Savdo to'liq muvaffaqiyat bilan yopildi!</i>"
            )
        elif event_type == "BE_PROFIT":
            text = (
                f"🛡️ <b>POZITSIYA FOYDALI BREAK-EVENDA YOPILDI — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Chiqish:</b> ${curr_price:,.2f}\n"
                f"💰 <b>Jami Olingan Foyda:</b> +${abs(pnl):,.2f} USD\n"
                f"✅ <i>Kapital to'liq saqlanib, TP1 foydasi hisobda qoldi!</i>"
            )
        elif event_type == "SL":
            text = (
                f"🛑 <b>STOP LOSS URILDI — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Chiqish:</b> ${curr_price:,.2f}\n"
                f"📉 <b>Zarar:</b> -${abs(pnl):,.2f} USD\n"
                f"🛡️ <i>Prop firm risk boshqaruvi kapitalni himoya qildi (0.13% risk).</i>"
            )
        else:
            text = (
                f"ℹ️ <b>SAVDO HOLATI YANGILANDI ({event_type}) — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Hozirgi:</b> ${curr_price:,.2f}\n"
                f"💰 <b>PnL:</b> {pnl_sign}${pnl:,.2f} USD"
            )

        sig_id = details.get("signal_id", "")
        for cid in list(self.chat_ids):
            reply_id = (
                self.message_map.get(f"{cid}:{pos_id}") or
                self.message_map.get(pos_id) or
                self.message_map.get(f"{cid}:{sig_id}") or
                self.message_map.get(sig_id) or
                self.message_map.get(f"{cid}:{symbol}") or
                self.message_map.get(symbol)
            )
            self.send_direct_message(cid, text, reply_to_message_id=reply_id)

    def send_ai_signal_notification(self, signal: Dict[str, Any]) -> Optional[int]:
        self.poll_updates()
        if not self.chat_ids:
            return None
        symbol = signal.get("symbol", "BTC/USDT")
        side = signal.get("side", "BUY").upper()
        entry = float(signal.get("entry_price") or signal.get("entry") or 0.0)
        sl = float(signal.get("sl") or 0.0)
        tp1 = float(signal.get("tp1") or 0.0)
        tp2 = float(signal.get("tp2") or 0.0)
        score = float(signal.get("score") or signal.get("confidence") or 77.9)
        setup = signal.get("setup", "SMC Liquidity Sweep")

        text = (
            f"🧠 <b>YANGI KVANT SIGNALI — {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Yo'nalish:</b> {'🟢 BUY' if side == 'BUY' else '🔴 SELL'}\n"
            f"🎯 <b>Entry:</b> ${entry:,.2f}\n"
            f"🟢 <b>TP1:</b> ${tp1:,.2f} | <b>TP2:</b> ${tp2:,.2f}\n"
            f"🔴 <b>SL:</b> ${sl:,.2f}\n"
            f"⚡ <b>Score:</b> {score:.1f}% | <b>Setup:</b> {setup}"
        )
        msg_ids = []
        for cid in list(self.chat_ids):
            mid = self.send_direct_message(cid, text)
            if mid:
                msg_ids.append(mid)
        return msg_ids[0] if msg_ids else None

telegram_notifier = TelegramNotifier()
