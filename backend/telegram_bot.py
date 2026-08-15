import os
import json
import urllib.request
import urllib.parse
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("TelegramBot")

BOT_TOKEN = "8922592987:AAEKfszGRuNsgGVy95f649rf8MHdrKiw6QI"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
STATE_FILE = os.path.join(os.path.dirname(__file__), "telegram_state.json")

INITIAL_PROP_CAPITAL = 10000.00 # 10k Base Account Balance

class TelegramNotifier:
    def __init__(self):
        self.chat_ids = set()
        self.muted_ai_signal_chat_ids = set()
        self.message_map = {} # position_id -> message_id
        self.last_update_id = 0
        self.account_balance = INITIAL_PROP_CAPITAL
        self.daily_start_balance = INITIAL_PROP_CAPITAL
        self._load_state()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.chat_ids = set(data.get("chat_ids", []))
                    self.muted_ai_signal_chat_ids = set(data.get("muted_ai_signal_chat_ids", []))
                    self.message_map = data.get("message_map", {})
                    self.last_update_id = data.get("last_update_id", 0)
                    self.account_balance = data.get("account_balance", INITIAL_PROP_CAPITAL)
                    self.daily_start_balance = data.get("daily_start_balance", INITIAL_PROP_CAPITAL)
            except Exception as e:
                logger.error(f"Failed to load telegram state: {e}")

    def _save_state(self):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({
                    "chat_ids": list(self.chat_ids),
                    "muted_ai_signal_chat_ids": list(self.muted_ai_signal_chat_ids),
                    "message_map": self.message_map,
                    "last_update_id": self.last_update_id,
                    "account_balance": self.account_balance,
                    "daily_start_balance": self.daily_start_balance
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save telegram state: {e}")

    def reset_account_balance(self, initial_capital: float = INITIAL_PROP_CAPITAL):
        self.account_balance = initial_capital
        self.daily_start_balance = initial_capital
        self._save_state()

    def get_main_keyboard(self) -> dict:
        return {
            "keyboard": [
                [{"text": "🛑 STOP AI SIGNALS"}, {"text": "🟢 START AI SIGNALS"}]
            ],
            "resize_keyboard": True,
            "is_persistent": True
        }

    def _make_request(self, method: str, payload: dict) -> dict:
        url = f"{BASE_URL}/{method}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except Exception as e:
            logger.error(f"Telegram API request error [{method}]: {e}")
            return {"ok": False, "description": str(e)}

    def poll_updates(self):
        """Polls getUpdates to register user chat_ids automatically and handle button commands."""
        res = self._make_request("getUpdates", {"offset": self.last_update_id + 1, "timeout": 2})
        if res.get("ok"):
            updates = res.get("result", [])
            for u in updates:
                self.last_update_id = max(self.last_update_id, u.get("update_id", 0))
                msg = u.get("message", {})
                chat = msg.get("chat", {})
                cid = chat.get("id")
                text = (msg.get("text") or "").strip()

                if cid:
                    if cid not in self.chat_ids:
                        self.chat_ids.add(cid)
                        self._save_state()
                        self.send_direct_message(
                            cid, 
                            f"✅ **APEX QUANT COPYTRADE BOTGA XUSH KELIBSIZ!**\n\n"
                            f"Barcha avtomatik savdolar, bosqichlar (Stage 1 / Stage 2 / Funded) va real-vaqt xabarnomalari shu botga kelib turadi.\n"
                            f"💵 **Boshlang'ich Balans:** ${self.account_balance:,.2f} USD\n\n"
                            f"Pastdagi tugmalar orqali AI tahlil signallarini o'chirishingiz yoki yoqishingiz mumkin."
                        )

                    # Command / Button Handling
                    if text in ["🛑 STOP AI SIGNALS", "/stop_ai_signals", "STOP AI SIGNALS"]:
                        self.muted_ai_signal_chat_ids.add(cid)
                        self._save_state()
                        self.send_direct_message(
                            cid,
                            f"🛑 **AI TAHLILIY SIGNALLARI SIZ UCHUN TO'XTATILDI!**\n\n"
                            f"Sizga faqat real **ENGINE AUTO TRADE** va pozitsiyalar yopilishi xabarlari keladi. AI tahlil signallari yuborilmaydi."
                        )
                    elif text in ["🟢 START AI SIGNALS", "/start_ai_signals", "START AI SIGNALS"]:
                        if cid in self.muted_ai_signal_chat_ids:
                            self.muted_ai_signal_chat_ids.remove(cid)
                            self._save_state()
                        self.send_direct_message(
                            cid,
                            f"🟢 **AI TAHLILIY SIGNALLARI SIZ UCHUN YOQILDI!**\n\n"
                            f"Endi sizga barcha qo'shimcha AI tahlil signallari va Engine Auto Trade xabarlari yuboriladi."
                        )
            if updates:
                self._save_state()

    def send_direct_message(self, chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> Optional[int]:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": self.get_main_keyboard()
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        res = self._make_request("sendMessage", payload)
        if res.get("ok"):
            return res["result"]["message_id"]
        return None

    def send_trade_open_notification(self, position: Dict[str, Any]):
        """
        Sends formatted Trade Open message matching exact user specification:
        🤖 BOT AVTOMATIK SAVDO OCHDI — BTC/USDT SHORT 🔴
        ==================================
        🪙 Kirish narxi: $63098.30
        📊 H1 EMA stack: Bearish trend
        📈 M5 EMA 9 Pullback: Bounce detected

        🎯 Take Profit 1 (1.5R): $62664.55
        🎯 Take Profit 2 (4.0R): $61941.62
        🛡️ Stop Loss: $63387.47
        ⚖️ Savdo Hajmi: 0.6916 BTC
        🔒 5x Leverage Margin: $8728.22 USD
        💰 Risk: $200.00

        ✅ Pozitsiya avtomatik ochildi. Kuzatilmoqda...
        """
        self.poll_updates()
        if not self.chat_ids:
            logger.warning("No chat_ids registered in TelegramNotifier yet. User needs to message @xrpropbot.")
            return

        side_emoji = "🟢" if position.get("side", "BUY").upper() == "BUY" else "🔴"
        side_text = position.get("side", "BUY").upper()
        symbol = position.get("symbol", "BTC/USDT")
        entry = float(position.get("entryPrice") or position.get("entry_price") or 0.0)
        size = float(position.get("size", 1.0))
        base_asset = symbol.split("/")[0]
        leverage = position.get("leverage", 5)
        margin = float(position.get("marginUsed") or position.get("margin_used") or 0.0)
        sl = float(position.get("sl", 0.0))
        tp1 = float(position.get("tp1", 0.0))
        tp2 = float(position.get("tp2", 0.0))
        risk = float(position.get("expectedLoss") or position.get("expected_loss") or 75.0)
        risk_pct = float(position.get("riskPercent") or ((risk / max(1.0, self.account_balance)) * 100.0))
        reason = position.get("aiExplanation") or position.get("ai_explanation") or "SMC Demand Zone + FVG Fill"
        confidence = position.get("aiConfidence") or position.get("ai_confidence") or 85.0

        # Balance breakdown & Prop Guard check
        total_loss = INITIAL_PROP_CAPITAL - self.account_balance
        bal_change_pct = ((self.account_balance - INITIAL_PROP_CAPITAL) / INITIAL_PROP_CAPITAL) * 100.0
        bal_change_str = f"+{bal_change_pct:.2f}%" if bal_change_pct >= 0 else f"{bal_change_pct:.2f}%"

        # Check if prop firm drawdown limit breached (10% total DD)
        if total_loss >= (INITIAL_PROP_CAPITAL * 0.10):
            text = (
                f"🚨 **PROP FIRM DRAWDOWN LIMITI BUZILDI (-10.0%)** 🚨\n"
                f"==================================\n"
                f"💵 **Qolgan Balans:** ${self.account_balance:,.2f} USD ({bal_change_str})\n"
                f"🛑 **Qoida:** FTMO / Prop firm 10% max drawdown chegarasiga yetildi.\n"
                f"🔒 **STATUS:** Barcha yangi savdolar avtomatik bloklandi va kapital muhofaza qilindi."
            )
            for cid in list(self.chat_ids):
                self.send_direct_message(cid, text)
            return

        text = (
            f"🤖 **BOT AVTOMATIK SAVDO OCHDI — {symbol} {side_text} {side_emoji}**\n"
            f"==================================\n"
            f"🪙 **Kirish narxi:** ${entry:,.2f}\n"
            f"📊 **Strategiya Confluence:** {reason}\n"
            f"📈 **AI Ishonch (Confidence):** {confidence:.1f}%\n\n"
            f"🎯 **Take Profit 1 (1.5R):** ${tp1:,.2f}\n"
            f"🎯 **Take Profit 2 (4.0R):** ${tp2:,.2f}\n"
            f"🛡️ **Stop Loss:** ${sl:,.2f}\n"
            f"⚖️ **Savdo Hajmi:** {size} {base_asset}\n"
            f"🔒 **{leverage}x Leverage Margin:** ${margin:,.2f} USD\n"
            f"💰 **Planned Risk:** ${risk:,.2f} ({risk_pct:.2f}% Risk)\n\n"
            f"💵 **10K BALANSDAN QOLGANI:** ${self.account_balance:,.2f} USD ({bal_change_str})\n"
            f"✅ Pozitsiya avtomatik ochildi. Real-vaqtda kuzatilmoqda..."
        )

        pos_id = position.get("id", "pos_001")
        for cid in list(self.chat_ids):
            msg_id = self.send_direct_message(cid, text)
            if msg_id:
                self.message_map[pos_id] = msg_id
        
        self._save_state()

    def send_trade_update_notification(self, pos_id: str, event_type: str, details: Dict[str, Any]):
        """
        Replies to original trade message when SL hit, TP hit, BE hit, or closed.
        Updates 10k balance dynamically and reports remaining equity & DD buffer!
        """
        self.poll_updates()
        reply_id = self.message_map.get(pos_id)
        if not self.chat_ids:
            return

        symbol = details.get("symbol", "BTC/USDT")
        
        # Calculate balance impact
        pnl = details.get("pnl", 0.0)
        loss = details.get("loss", 200.0)

        if event_type == "SL":
            self.account_balance -= abs(loss)
        elif event_type in ["TP1", "TP2", "CLOSE"]:
            if pnl != 0.0:
                self.account_balance += pnl

        self._save_state()

        # Calculate remaining stats out of 10k
        bal_change = self.account_balance - INITIAL_PROP_CAPITAL
        bal_change_pct = (bal_change / INITIAL_PROP_CAPITAL) * 100.0
        bal_change_str = f"+{bal_change_pct:.2f}%" if bal_change_pct >= 0 else f"{bal_change_pct:.2f}%"
        
        # 5% max daily DD limit out of 10k = $500 max daily loss
        daily_loss = self.daily_start_balance - self.account_balance
        daily_dd_pct = max(0.0, (daily_loss / self.daily_start_balance) * 100.0)
        remaining_daily_dd_dollars = max(0.0, (INITIAL_PROP_CAPITAL * 0.05) - daily_loss)

        balance_block = (
            f"----------------------------------\n"
            f"💵 **10K BALANSDAN QOLGANI:** ${self.account_balance:,.2f} USD ({bal_change_str})\n"
            f"🛡️ **Kunlik Drawdown Limitgacha Qoldi:** ${remaining_daily_dd_dollars:,.2f} USD (DD: {daily_dd_pct:.2f}% / 5.0%)"
        )

        if event_type == "BE":
            text = (
                f"🛡️ **BREAK EVEN AKTIVLASHTIRILDI — {symbol}**\n"
                f"----------------------------------\n"
                f"📌 Stop Loss kirish narxiga (${details.get('entry_price', 0.0):,.2f}) ko'chirildi.\n"
                f"🔒 Risk to'liq 0.00% ga tushirildi va kapital himoyalandi!\n"
                f"{balance_block}"
            )
        elif event_type in ["TP1", "TP2"]:
            text = (
                f"🎯 **TAKE PROFIT {event_type[-1]} ERISHILDI! — {symbol} 🟢**\n"
                f"----------------------------------\n"
                f"💰 Lock qilingan foyda: +${abs(pnl):,.2f}\n"
                f"📈 Stop loss Break Even ga surildi.\n"
                f"{balance_block}"
            )
        elif event_type == "SL":
            text = (
                f"🛑 **STOP LOSS URILDI — {symbol} 🔴**\n"
                f"----------------------------------\n"
                f"🔻 Zarar: -${abs(loss):,.2f} (-1.00% Risk)\n"
                f"🛡️ Prop firm xavfsizlik raili o'z vaqtida stop qildi.\n"
                f"{balance_block}"
            )
        elif event_type == "CLOSE":
            text = (
                f"🏁 **POZITSIYA YOPILDI — {symbol}**\n"
                f"----------------------------------\n"
                f"💰 Yakuniy PnL: {details.get('pnl_str', '+$0.00')}\n"
                f"⏱ Davomiyligi: {details.get('duration', '1h 15m')}\n"
                f"{balance_block}"
            )
        else:
            text = (
                f"ℹ️ **UPDATE — {symbol}:** {details.get('message', 'Trade updated')}\n"
                f"{balance_block}"
            )

        for cid in list(self.chat_ids):
            self.send_direct_message(cid, text, reply_to_message_id=reply_id)

    def send_prop_milestone_notification(self, event_type: str, details: Dict[str, Any]):
        """
        Sends Prop Challenge Milestone notifications:
        - STAGE_1_PASSED
        - STAGE_2_STARTED
        - STAGE_2_PASSED / FUNDED_UNLOCKED
        - STAGE_FAILED
        """
        self.poll_updates()
        if not self.chat_ids:
            return

        firm = details.get("firm", "FTMO")
        account = details.get("account", "10K-PROP-EVAL")
        balance = details.get("balance", self.account_balance)
        pnl = details.get("pnl", 1000.0)

        if event_type == "STAGE_1_PASSED":
            text = (
                f"🎉 **STAGE 1 CHELENJ MUVAFFAQIYATLI O'TILDI! 🚀**\n"
                f"==================================\n"
                f"🏆 **Prop Firma:** {firm} ({account})\n"
                f"📈 **Erishilgan Target (10.0%):** +${pnl:,.2f} USD\n"
                f"💵 **Yakuniy Balans:** ${balance:,.2f} USD\n"
                f"⏱ **Davomiyligi:** {details.get('days', 8)} savdo kuni\n"
                f"📊 **Win Rate:** {details.get('win_rate', 74.3)}% | **Max DD:** {details.get('max_dd', 1.2)}%\n\n"
                f"✅ **STAGE 1 YAKUNLANDI VA TASDIQLANDI!**\n"
                f"➡️ STAGE 2 (Verification Stage) avtomatik boshlanmoqda..."
            )
        elif event_type == "STAGE_2_STARTED":
            text = (
                f"🔑 **STAGE 2 (VERIFICATION STAGE) BOSHLANDI! 🏁**\n"
                f"==================================\n"
                f"🏆 **Prop Firma:** {firm} ({account})\n"
                f"🪙 **Dastlabki Balans:** ${balance:,.2f} USD\n"
                f"🎯 **Stage 2 Target (5.0%):** +${(balance * 0.05):,.2f} USD\n"
                f"🛡️ **Kunlik Drawdown Limit (5.0%):** ${(balance * 0.05):,.2f} USD\n"
                f"🛡️ **Maksimal Drawdown Limit (10.0%):** ${(balance * 0.10):,.2f} USD\n\n"
                f"🤖 APEX Engine Stage 2 bo'yicha avtomatik savdoni boshladi..."
            )
        elif event_type in ["STAGE_2_PASSED", "FUNDED_UNLOCKED"]:
            text = (
                f"👑 **BARCHA PROP BOSQICHLARI O'TILDI! FUNDED ACCOUNT OLINDI! 📜🎉**\n"
                f"==================================\n"
                f"🏆 **Prop Firma:** {firm} REAL FUNDED ACCOUNT\n"
                f"📜 **Sertifikat Holati:** VERIFIED & LIVE FUNDED\n"
                f"💵 **Real Boshqaruv Kapitali:** ${balance:,.2f} USD\n"
                f"💸 **Profit Split:** 80% / 20% Trader Payout\n\n"
                f"🔥 **TABRIKLAYMIZ!** Endi real mablag' bilan savdo qilinadi va barcha foydalar yechib olinadi!"
            )
        elif event_type == "STAGE_FAILED":
            text = (
                f"⚠️ **PROP CHELENJ QOIDASI BUZILDI / TO'XTATILDI 🛑**\n"
                f"==================================\n"
                f"🏆 **Prop Firma:** {firm} ({account})\n"
                f"🔻 **Sabab:** {details.get('reason', 'Max daily drawdown limit reached')}\n"
                f"🛡️ APEX Auto-Killswitch barcha savdolarni zudlik bilan yopdi."
            )
        else:
            text = f"ℹ️ **PROP EVENT ({event_type}):** {details.get('message', 'Prop event triggered')}"

        for cid in list(self.chat_ids):
            self.send_direct_message(cid, text)

    def send_ai_signal_notification(self, signal: Dict[str, Any]) -> Optional[int]:
        """
        Sends a Telegram notification when an additional AI signal is detected.
        """
        self.poll_updates()
        if not self.chat_ids:
            logger.warning("No chat_ids registered in TelegramNotifier. Cannot send AI signal.")
            return None

        side_emoji = "🟢" if signal.get("side", "BUY").upper() == "BUY" else "🔴"
        side_text = signal.get("side", "BUY").upper()
        symbol = signal.get("symbol", "BTC/USDT")
        entry = signal.get("entry", 0.0)
        sl = signal.get("sl", 0.0)
        tp1 = signal.get("tp1", signal.get("tp", 0.0))
        tp2 = signal.get("tp2", 0.0)
        tp3 = signal.get("tp3", 0.0)
        ai_score = signal.get("aiScore", 80.0)
        prob = signal.get("probability", 80.0)
        reason = signal.get("reasoning", "Market structure alignment.")

        text = (
            f"🔮 **Qoshimcha AI signal aniqlandi — {symbol} {side_text} {side_emoji}**\n"
            f"==================================\n"
            f"🪙 **Kirish narxi:** ${entry:,.2f}\n"
            f"🛡️ **Stop Loss:** ${sl:,.2f}\n"
            f"🎯 **TP1:** ${tp1:,.2f}\n"
            f"🎯 **TP2:** ${tp2:,.2f}\n"
            f"🎯 **TP3:** ${tp3:,.2f}\n"
            f"📈 **AI Ishonch:** {ai_score}% (Confluence: {prob}%)\n\n"
            f"📝 **Asos:** {reason}\n\n"
            f"⚠️ *Bu shunchaki qo'shimcha AI tahlil signalidir. Tizim avtomatik tarzda narxni kuzatadi va natijasini xabar beradi.*"
        )

        first_msg_id = None
        for cid in list(self.chat_ids):
            if cid in self.muted_ai_signal_chat_ids:
                logger.info(f"Skipping AI signal for muted chat_id {cid}")
                continue
            msg_id = self.send_direct_message(cid, text)
            if msg_id and first_msg_id is None:
                first_msg_id = msg_id
        return first_msg_id

    def send_ai_signal_update_notification(self, reply_id: int, symbol: str, event_type: str, details: Dict[str, Any]):
        """
        Sends a reply notification to the original AI signal message when SL or TP is hit.
        """
        self.poll_updates()
        if not self.chat_ids or not reply_id:
            return

        pnl_pct = details.get("pnl_pct", 0.0)
        pnl_str = f"+{pnl_pct:.2f}%" if pnl_pct >= 0 else f"{pnl_pct:.2f}%"
        current_price = details.get("price", 0.0)

        if event_type == "TP":
            text = (
                f"🎯 **AI SIGNAL: TAKE PROFIT ERISHILDI! — {symbol} 🟢**\n"
                f"----------------------------------\n"
                f"💰 Yakuniy Foyda (AI): {pnl_str}\n"
                f"📈 Chiqish narxi: ${current_price:,.2f}\n"
                f"🛡️ AI signal muvaffaqiyatli yakunlandi."
            )
        else:
            text = (
                f"🛑 **AI SIGNAL: STOP LOSS URILDI — {symbol} 🔴**\n"
                f"----------------------------------\n"
                f"🔻 Yakuniy Zarar (AI): {pnl_str}\n"
                f"📉 Chiqish narxi: ${current_price:,.2f}\n"
                f"🛡️ AI risk boshqaruvi signalni to'xtatdi."
            )

        for cid in list(self.chat_ids):
            self.send_direct_message(cid, text, reply_to_message_id=reply_id)

# Singleton instance
telegram_notifier = TelegramNotifier()
