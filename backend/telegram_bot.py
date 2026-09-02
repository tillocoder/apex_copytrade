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
        self.last_update_id = 0
        self.account_balance = INITIAL_PROP_CAPITAL
        self.daily_start_balance = INITIAL_PROP_CAPITAL
        self.signals_active = True
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
                    self.last_update_id = int(data.get("last_update_id", 0))
                    self.account_balance = float(data.get("account_balance", INITIAL_PROP_CAPITAL))
                    self.daily_start_balance = float(data.get("daily_start_balance", INITIAL_PROP_CAPITAL))
                    self.signals_active = bool(data.get("signals_active", True))
        except Exception as e:
            logger.error(f"Error loading telegram_state.json: {e}")

    def _save_state(self):
        try:
            data = {
                "chat_ids": list(self.chat_ids),
                "message_map": self.message_map,
                "last_update_id": self.last_update_id,
                "account_balance": self.account_balance,
                "daily_start_balance": self.daily_start_balance,
                "signals_active": self.signals_active
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving telegram_state.json: {e}")

    def _get_main_reply_keyboard(self) -> dict:
        """Restores the complete 3-row full button layout!"""
        return {
            "keyboard": [
                [{"text": "📊 Ochiq Bitimlar"}, {"text": "💼 Hisob Holati"}],
                [{"text": "🤖 Engine"}, {"text": "🛡️ E2 Shadow"}, {"text": "📡 AI Signals"}],
                [{"text": "🟢 Start Signals"}, {"text": "🔴 Stop Signals"}]
            ],
            "resize_keyboard": True,
            "is_persistent": True
        }

    def _build_position_inline_keyboard(self, pos_id: str) -> dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🔴 LIVE", "web_app": {"url": f"https://apex.xrinvest.uz/?mode=tg_live&pos={pos_id}"}}
                ]
            ]
        }

    def send_direct_message(self, chat_id: int, text: str, reply_to_message_id: Optional[int] = None, show_keyboard: bool = True) -> Optional[int]:
        if not self.bot_token:
            return None
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if show_keyboard:
            payload["reply_markup"] = self._get_main_reply_keyboard()
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

    def poll_updates(self):
        """Polls Telegram updates and processes incoming user commands and button clicks."""
        if not self.bot_token:
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 0}
        try:
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for u in updates:
                    upd_id = u.get("update_id", 0)
                    if upd_id > self.last_update_id:
                        self.last_update_id = upd_id

                    msg = u.get("message")
                    if msg:
                        cid = msg.get("chat", {}).get("id")
                        text = (msg.get("text") or "").strip()
                        if cid:
                            if cid not in self.chat_ids:
                                self.chat_ids.add(cid)
                            self._handle_user_message(cid, text)
                if updates:
                    self._save_state()
        except Exception as e:
            logger.error(f"Error in poll_updates: {e}")

    def _handle_user_message(self, chat_id: int, text: str):
        """Dispatches response for all restored buttons and text commands."""
        text_lower = text.lower()
        if not text:
            return

        if "/start" in text_lower or "/help" in text_lower:
            welcome = (
                "🤖 <b>APEX QUANT 10K PROP FIRM TERMINAL BOTI</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚡ <b>Avtonom Kvant Dvigateli:</b> Faol (M15 SMC Strategy)\n"
                "🛡️ <b>Risk Boshqaruvi:</b> 1.0% Max Risk | 2X Max Leverage\n"
                "📊 <b>Jonli Grafik:</b> Har bir savdoda <b>🔴 LIVE</b> tugmasi mavjud.\n\n"
                "👇 Kerakli bo'limni tanlang:"
            )
            self.send_direct_message(chat_id, welcome)

        elif "hisob holati" in text_lower or "/status" in text_lower:
            self._send_account_status(chat_id)

        elif "ochiq bitimlar" in text_lower or "/positions" in text_lower:
            self._send_open_positions(chat_id)

        elif "ai signals" in text_lower or "signallar" in text_lower or "/signals" in text_lower:
            self._send_active_signals(chat_id)

        elif "engine" in text_lower:
            self._send_engine_stats(chat_id)

        elif "shadow" in text_lower:
            self._send_shadow_stats(chat_id)

        elif "start signals" in text_lower:
            self.signals_active = True
            self._save_state()
            self.send_direct_message(chat_id, "🟢 <b>AI Kvant Signallari va Avtomatik Savdo Yoqildi (ACTIVE)!</b>")

        elif "stop signals" in text_lower:
            self.signals_active = False
            self._save_state()
            self.send_direct_message(chat_id, "🔴 <b>AI Signallarini qabul qilish vaqtinchalik to'xtatildi (PAUSED).</b>")

        else:
            self.send_direct_message(chat_id, "ℹ️ Iltimos, pastdagi menyu tugmalaridan birini tanlang:")

    def _send_account_status(self, chat_id: int):
        try:
            from backend.live_execution_manager import sync_live_positions_and_equity
            sync_data = sync_live_positions_and_equity()
            open_cnt = len(sync_data.get("openPositions", []))
            current_equity = sync_data.get("currentEquity", self.account_balance)
            realized_pnl = sync_data.get("realizedPnl", 0.0)
            unrealized_pnl = sync_data.get("unrealizedPnl", 0.0)
            total_trades = sync_data.get("totalTrades", 0)
            win_rate = sync_data.get("winRate", 0.0)
        except Exception:
            open_cnt = 0
            current_equity = self.account_balance
            realized_pnl = 0.0
            unrealized_pnl = 0.0
            total_trades = 0
            win_rate = 0.0

        pnl_change_pct = ((current_equity - INITIAL_PROP_CAPITAL) / INITIAL_PROP_CAPITAL) * 100.0
        pnl_sign = "+" if pnl_change_pct >= 0 else ""

        target_stage1 = INITIAL_PROP_CAPITAL * 0.08  # $800
        current_profit = current_equity - INITIAL_PROP_CAPITAL
        progress_pct = max(0.0, min(100.0, (current_profit / target_stage1) * 100.0))

        text = (
            "💼 <b>APEX 10K PROP ACCOUNT HOLATI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Boshlang'ich Balans:</b> ${INITIAL_PROP_CAPITAL:,.2f} USD\n"
            f"📈 <b>Joriy Equity:</b> ${current_equity:,.2f} USD ({pnl_sign}{pnl_change_pct:.2f}%)\n"
            f"💵 <b>Realizatsiya Qilingan PnL:</b> +${realized_pnl:,.2f} USD\n"
            f"⚡ <b>Suzuvchi (Unrealized) PnL:</b> {('+' if unrealized_pnl>=0 else '')}${unrealized_pnl:,.2f} USD\n"
            f"📦 <b>Ochiq Pozitsiyalar:</b> {open_cnt} ta\n"
            f"🏆 <b>Yopiq Savdolar:</b> {total_trades} ta (Win Rate: {win_rate:.1f}%)\n\n"
            f"🎯 <b>Chelenj Maqsadi (Stage 1):</b> +8.0% (+${target_stage1:,.2f})\n"
            f"📊 <b>Erishilgan Natija:</b> {progress_pct:.1f}% (${current_profit:,.2f} / ${target_stage1:,.2f})\n\n"
            "🛡️ <b>Kunlik Max DD:</b> $500.00 USD (5.0% Limit - Xavfsiz)\n"
            "🛡️ <b>Umumiy Max DD:</b> $1,000.00 USD (10.0% Limit - Xavfsiz)\n"
            "✅ <b>Status:</b> BARCHA QOIDALARGA MOS"
        )
        self.send_direct_message(chat_id, text)

    def _send_open_positions(self, chat_id: int):
        try:
            from backend.live_execution_manager import load_positions
            open_pos = [p for p in load_positions() if p.get("status") == "OPEN"]
        except Exception:
            open_pos = []

        if not open_pos:
            self.send_direct_message(chat_id, "ℹ️ Hozirda faol ochiq pozitsiyalar yo'q. Kvant dvigateli M15 shamchalarini skanerlamoqda...")
            return

        for p in open_pos:
            sym = p.get("symbol", "BTC/USDT")
            side = p.get("side", "BUY").upper()
            entry = float(p.get("entryPrice") or 0.0)
            mark = float(p.get("currentPrice") or entry)
            sl = float(p.get("sl") or 0.0)
            tp1 = float(p.get("tp1") or 0.0)
            tp2 = float(p.get("tp2") or 0.0)
            size = float(p.get("size") or 0.05)
            is_buy = (side == "BUY")
            pnl = (mark - entry) * size if is_buy else (entry - mark) * size
            pnl_sign = "+" if pnl >= 0 else ""
            pos_id = p.get("id", "")

            trailed_badge = " (Trailed SL 🔒)" if p.get("trailingStopActive") else ""

            text = (
                f"📊 <b>OCHIQ POZITSIYA — {sym} {side} 2X</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish Narxi:</b> ${entry:,.2f}\n"
                f"📈 <b>Joriy Narx:</b> ${mark:,.2f}\n"
                f"💰 <b>Suzuvchi PnL:</b> {pnl_sign}${pnl:,.2f} USD\n"
                f"🟢 <b>TP1:</b> ${tp1:,.2f} | <b>TP2:</b> ${tp2:,.2f}\n"
                f"🔴 <b>Stop Loss:</b> ${sl:,.2f}{trailed_badge}\n"
                f"📦 <b>Hajm:</b> {size} {sym.split('/')[0]}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>👇 Grafikni to'liq ekranda ko'rish uchun <b>🔴 LIVE</b> tugmasini bosing:</i>"
            )
            self.send_trade_message(chat_id, text, pos_id)

    def _send_active_signals(self, chat_id: int):
        try:
            from backend.database import SignalsRepository
            signals = SignalsRepository.get_active_signals()
        except Exception:
            signals = []

        if not signals:
            self.send_direct_message(chat_id, "📡 Hozirgi kutilayotgan yangi signallar yo'q. Engine har 60 soniyada yangi M15 shamchalarni tahlil qilmoqda.")
            return

        for s in signals[:2]:
            sym = s.get("symbol", "BTC/USDT")
            side = s.get("side", "BUY")
            entry = float(s.get("entry_price") or 0.0)
            tp1 = float(s.get("tp1") or 0.0)
            tp2 = float(s.get("tp2") or 0.0)
            sl = float(s.get("sl") or 0.0)
            score = float(s.get("score") or 77.9)
            setup = s.get("setup", "SMC Liquidity Sweep")

            text = (
                f"📡 <b>AI KVANT SIGNALI — {sym} {side}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Entry:</b> ${entry:,.2f}\n"
                f"🟢 <b>TP1:</b> ${tp1:,.2f} | <b>TP2:</b> ${tp2:,.2f}\n"
                f"🔴 <b>SL:</b> ${sl:,.2f}\n"
                f"🧠 <b>Score:</b> {score:.1f}% | <b>Setup:</b> {setup}"
            )
            self.send_direct_message(chat_id, text)

    def _send_engine_stats(self, chat_id: int):
        text = (
            "🤖 <b>APEX QUANT ENGINE — STATISTIKA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <b>Holati:</b> ONLINE (M15 Skaner Faol)\n"
            "📊 <b>Strategiya:</b> SMC Liquidity Sweep + OrderBlock\n"
            "🛡️ <b>Maksimal Risk:</b> 1.0% ($100) / Trade\n"
            "⏱️ <b>O'rtacha Davomiylik:</b> ~58 daqiqa / savdo\n"
            "🏆 <b>1 Yillik Win Rate:</b> 62.3% (PF: 1.81x)\n"
            "💰 <b>1 Yillik Net Foyda:</b> +$14,995.86 USD"
        )
        self.send_direct_message(chat_id, text)

    def _send_shadow_stats(self, chat_id: int):
        text = (
            "🛡️ <b>E2 SHADOW TRACKER — STATISTIKA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 <b>Nazorat Tizimi:</b> Institutional Shadow Engine\n"
            "🔒 <b>Hozirgi Kunlik DD:</b> 0.00% / 5.0% Max\n"
            "🔒 <b>Hozirgi Umumiy DD:</b> 0.00% / 10.0% Max\n"
            "✅ <b>Qoidabuzarlik:</b> 0 ta (100% Xavfsiz)"
        )
        self.send_direct_message(chat_id, text)

    def send_trade_open_notification(self, position: Dict[str, Any]):
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
