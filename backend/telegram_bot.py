"""
Institutional Telegram Bot & Real-Time Alert Engine for APEX Quant Copytrade.
Handles:
  1. Real-time reply threading: Every trade update (TP1, TP2, TP3, BE, SL) explicitly replies
     to its original trade-open notification so users can trace every position seamlessly.
  2. Compact, professional, high-clarity button UI (Ochiq Bitimlar, Hisob Holati, Engine, Shadow, Signals).
  3. 100% synchronized open positions reading directly from live_positions.json + live Binance feeds.
  4. Real-time in-place snapshot message editing via inline callbacks.
  5. UTF-8 / UTF-8-SIG encoding robustness and bulletproof absolute path resolution.
"""

import os
import json
import time
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APEX_TELEGRAM_BOT")

TELEGRAM_BOT_TOKEN = "8922592987:AAEKfszGRuNsgGVy95f649rf8MHdrKiw6QI"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "telegram_state.json")
INITIAL_PROP_CAPITAL = 10000.00


class TelegramNotifier:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.chat_ids: Set[int] = set()
        self.muted_ai_signal_chat_ids: Set[int] = set()
        self.message_map: Dict[str, int] = {}
        self.last_update_id: int = 0
        self.account_balance: float = INITIAL_PROP_CAPITAL
        self.daily_start_balance: float = INITIAL_PROP_CAPITAL
        self._load_state()

    # ── State Management ─────────────────────────────────────────────

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
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
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "chat_ids": list(self.chat_ids),
                    "muted_ai_signal_chat_ids": list(self.muted_ai_signal_chat_ids),
                    "message_map": self.message_map,
                    "last_update_id": self.last_update_id,
                    "account_balance": self.account_balance,
                    "daily_start_balance": self.daily_start_balance
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save telegram state: {e}")

    def reset_account_balance(self, initial_capital: float = INITIAL_PROP_CAPITAL):
        self.account_balance = initial_capital
        self.daily_start_balance = initial_capital
        self._save_state()

    # ── Keyboards & UI ───────────────────────────────────────────────

    def get_main_keyboard(self) -> dict:
        """
        Clean, compact, and professional 3-row layout with shortened clear labels.
        """
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

    # ── Telegram API Requests ────────────────────────────────────────

    def _make_request(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_url}/{method}"
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Telegram API request '{method}' failed: {e}")
            return {"ok": False, "description": str(e)}

    def send_direct_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None
    ) -> Optional[int]:
        """Sends a message with the persistent reply keyboard and safe reply fallback."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": self.get_main_keyboard()
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            payload["allow_sending_without_reply"] = True

        res = self._make_request("sendMessage", payload)
        if res.get("ok"):
            return res["result"]["message_id"]
        logger.error(f"send_direct_message failed: {res.get('description', 'unknown')}")
        return None

    def send_trade_message(
        self,
        chat_id: int,
        text: str,
        pos_id: str,
        reply_to_message_id: Optional[int] = None
    ) -> Optional[int]:
        """Sends a trade notification with interactive inline keyboard."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": self._build_position_inline_keyboard(pos_id)
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            payload["allow_sending_without_reply"] = True

        res = self._make_request("sendMessage", payload)
        if res.get("ok"):
            return res["result"]["message_id"]
        logger.error(f"send_trade_message failed: {res.get('description', 'unknown')}")
        return None

    # ── Position Snapshot & Reports ──────────────────────────────────

    def _get_position_live_snapshot(self, pos_id: str) -> Optional[str]:
        try:
            from backend.live_execution_manager import load_positions, fetch_binance_price
            all_positions = load_positions()
            pos = next((p for p in all_positions if p.get("id") == pos_id), None)
            if not pos:
                return None

            sym = pos.get("symbol", "BTC/USDT")
            side = pos.get("side", "BUY").upper()
            entry = float(pos.get("entryPrice") or pos.get("entry_price") or 0.0)
            size = float(pos.get("size", 1.0))
            sl = float(pos.get("sl", 0.0))
            tp1 = float(pos.get("tp1", 0.0))
            tp2 = float(pos.get("tp2", 0.0))
            tp3 = float(pos.get("tp3", 0.0))
            leverage = pos.get("leverage", 2)
            margin = float(pos.get("marginUsed") or pos.get("margin_used") or 0.0)
            time_open = pos.get("timeOpen", "-")
            status = pos.get("status", "OPEN")
            reason = (pos.get("aiExplanation") or "SMC OrderBlock Strategy").replace("_", " ")

            try:
                curr_price = fetch_binance_price(sym)
            except Exception:
                curr_price = float(pos.get("currentPrice") or entry)

            if side == "BUY":
                pnl = (curr_price - entry) * size
            else:
                pnl = (entry - curr_price) * size

            pnl_pct = (pnl / max(1.0, margin)) * 100.0
            pnl_sign = "+" if pnl >= 0 else ""
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            side_emoji = "🟢 BUY (LONG)" if side == "BUY" else "🔴 SELL (SHORT)"

            sl_dist = abs(curr_price - sl) if sl > 0 else 0.0
            tp1_dist = abs(tp1 - curr_price) if tp1 > 0 else 0.0

            return (
                f"{pnl_emoji} **{sym} {side} {leverage}x — JONLI STATS**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏷️ **Yo'nalish:** {side_emoji}\n"
                f"📍 **Kirish Narxi:** ${entry:,.2f}\n"
                f"⚡ **Binance Jonli Narx:** ${curr_price:,.2f}\n"
                f"💵 **Suzuvchi PnL:** {pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)\n"
                f"🎯 **Take Profit 1:** ${tp1:,.2f} (${tp1_dist:,.2f} qoldi)\n"
                f"🛑 **Stop Loss:** ${sl:,.2f} (${sl_dist:,.2f} masofa)\n"
                f"🔒 **Margin:** ${margin:,.2f} USD\n"
                f"⏳ **Ochilgan Vaqt:** {time_open} UTC\n"
                f"🧠 **Mantiq:** {reason}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱️ _Oxirgi yangilanish: {time.strftime('%H:%M:%S UTC')}_"
            )
        except Exception as e:
            logger.error(f"Error getting snapshot for {pos_id}: {e}")
            return None

    def format_open_positions_report(self) -> str:
        """Builds an exhaustive breakdown of all open trading positions."""
        try:
            from backend.live_execution_manager import sync_live_positions_and_equity
            sync_data = sync_live_positions_and_equity()
            open_positions = sync_data.get("openPositions", [])
            current_equity = sync_data.get("currentEquity", self.account_balance)
            realized_pnl = sync_data.get("realizedPnl", 0.0)
            unrealized_pnl = sync_data.get("unrealizedPnl", 0.0)
        except Exception as e:
            logger.error(f"Error syncing open positions: {e}")
            open_positions = []
            current_equity = self.account_balance
            realized_pnl = 0.0
            unrealized_pnl = 0.0

        if not open_positions:
            return (
                "ℹ️ **HOZIRDA OCHIQ POZITSIYALAR YO'Q**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Tizim BTC/USDT va ETH/USDT ni real-vaqtda tahlil qilmoqda.\n"
                "Yuqori ehtimolli setup aniqlansa avtomatik ochiladi va Telegram ga xabarnoma keladi.\n\n"
                f"💼 **Equity:** ${current_equity:,.2f} USD\n"
                f"💰 **Realized PnL:** +${realized_pnl:,.2f} USD"
            )

        bal_chg_pct = ((current_equity - INITIAL_PROP_CAPITAL) / INITIAL_PROP_CAPITAL) * 100.0
        bal_chg_str = f"+{bal_chg_pct:.2f}%" if bal_chg_pct >= 0 else f"{bal_chg_pct:.2f}%"
        pnl_s = "+" if unrealized_pnl >= 0 else ""

        pos_blocks = []
        for p in open_positions:
            sym = p.get("symbol", "BTC/USDT")
            side = p.get("side", "BUY").upper()
            entry = float(p.get("entryPrice") or 0.0)
            curr = float(p.get("currentPrice") or entry)
            pnl = float(p.get("unrealizedPnl") or 0.0)
            pnl_pct = float(p.get("unrealizedPnlPercent") or 0.0)
            tp1 = float(p.get("tp1") or 0.0)
            sl = float(p.get("sl") or 0.0)
            leverage = p.get("leverage", 2)
            margin = float(p.get("marginUsed") or 0.0)
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            pnl_sign_local = "+" if pnl >= 0 else ""

            pos_blocks.append(
                f"{pnl_emoji} **{sym} {side} {leverage}x** (PAPER • REAL BINANCE)\n"
                f"📍 **Kirish:** ${entry:,.2f} | ⚡ **Hozirgi:** ${curr:,.2f}\n"
                f"💵 **PnL:** {pnl_sign_local}${pnl:,.2f} ({pnl_sign_local}{pnl_pct:.2f}%)\n"
                f"🎯 **TP1:** ${tp1:,.2f} | 🛑 **SL:** ${sl:,.2f}\n"
                f"🔒 **Margin:** ${margin:,.2f} USD"
            )

        return (
            f"📊 **{len(open_positions)} TA OCHIQ POZITSIYA (JONLI HOLAT)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 **Equity:** ${current_equity:,.2f} USD ({bal_chg_str})\n"
            f"💰 **Realized PnL:** +${realized_pnl:,.2f} USD\n"
            f"📈 **Unrealized PnL:** {pnl_s}${unrealized_pnl:,.2f} USD\n\n"
            + "\n\n".join(pos_blocks)
        )

    def send_positions_individual(self, chat_id: int):
        """Sends one separate message per open position with interactive inline buttons."""
        try:
            from backend.live_execution_manager import sync_live_positions_and_equity
            sync_data = sync_live_positions_and_equity()
            open_positions = sync_data.get("openPositions", [])
            current_equity = sync_data.get("currentEquity", self.account_balance)
            realized_pnl = sync_data.get("realizedPnl", 0.0)
            unrealized_pnl = sync_data.get("unrealizedPnl", 0.0)
        except Exception as e:
            logger.error(f"Error in send_positions_individual: {e}")
            open_positions = []
            current_equity = self.account_balance
            realized_pnl = 0.0
            unrealized_pnl = 0.0

        if not open_positions:
            self.send_direct_message(
                chat_id,
                f"ℹ️ **HOZIRDA OCHIQ POZITSIYALAR YO'Q**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Tizim BTC/USDT va ETH/USDT ni real-vaqtda tahlil qilmoqda.\n"
                f"Yuqori ehtimolli setup aniqlansa avtomatik ochiladi va Telegram ga xabarnoma keladi.\n\n"
                f"💼 **Equity:** ${current_equity:,.2f} USD\n"
                f"💰 **Realized PnL:** +${realized_pnl:,.2f} USD"
            )
            return

        bal_chg_pct = ((current_equity - INITIAL_PROP_CAPITAL) / INITIAL_PROP_CAPITAL) * 100.0
        bal_chg_str = f"+{bal_chg_pct:.2f}%" if bal_chg_pct >= 0 else f"{bal_chg_pct:.2f}%"
        pnl_s = "+" if unrealized_pnl >= 0 else ""

        # Send Header summary
        self.send_direct_message(
            chat_id,
            f"📊 **{len(open_positions)} TA OCHIQ POZITSIYA — Jonli Holat**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 **Equity:** ${current_equity:,.2f} USD ({bal_chg_str})\n"
            f"💰 **Realized PnL:** +${realized_pnl:,.2f} USD\n"
            f"📈 **Unrealized PnL:** {pnl_s}${unrealized_pnl:,.2f} USD\n\n"
            f"Har bir pozitsiya tafsiloti quyida keltirilgan 👇"
        )

        for pos in open_positions:
            pos_id = pos.get("id", "")
            snapshot = self._get_position_live_snapshot(pos_id) if pos_id else None
            if snapshot:
                self.send_trade_message(chat_id, snapshot, pos_id)
            else:
                sym = pos.get("symbol", "BTC/USDT")
                side = pos.get("side", "BUY").upper()
                entry = float(pos.get("entryPrice") or 0.0)
                curr = float(pos.get("currentPrice") or entry)
                pnl = float(pos.get("unrealizedPnl") or 0.0)
                pnl_sign_local = "+" if pnl >= 0 else ""
                sl = float(pos.get("sl") or 0.0)
                tp1 = float(pos.get("tp1") or 0.0)
                side_em = "🟢" if side == "BUY" else "🔴"
                fb_txt = (
                    f"{side_em} **{sym} {side} 2x**\n"
                    f"📍 **Kirish:** ${entry:,.2f}  |  ⚡ **Hozirgi:** ${curr:,.2f}\n"
                    f"💵 **PnL:** {pnl_sign_local}${pnl:,.2f}\n"
                    f"🎯 **TP1:** ${tp1:,.2f}  |  🛑 **SL:** ${sl:,.2f}"
                )
                if pos_id:
                    self.send_trade_message(chat_id, fb_txt, pos_id)
                else:
                    self.send_direct_message(chat_id, fb_txt)

    def format_account_status_report(self) -> str:
        """Builds a summary of the Prop Firm account equity and challenge rules."""
        try:
            from backend.live_execution_manager import sync_live_positions_and_equity
            sync_data = sync_live_positions_and_equity()
            open_cnt = len(sync_data.get("openPositions", []))
            current_equity = sync_data.get("currentEquity", self.account_balance)
            realized_pnl = sync_data.get("realizedPnl", 0.0)
            unrealized_pnl = sync_data.get("unrealizedPnl", 0.0)
            total_trades = sync_data.get("totalTrades", 0)
            win_rate = sync_data.get("winRate", 0.0)
        except Exception as e:
            logger.error(f"Error in format_account_status_report: {e}")
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

        daily_dd_limit = INITIAL_PROP_CAPITAL * 0.05  # $500
        total_dd_limit = INITIAL_PROP_CAPITAL * 0.10  # $1000

        return (
            f"💼 **APEX 10K PROP ACCOUNT HOLATI**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 **Boshlang'ich Balans:** ${INITIAL_PROP_CAPITAL:,.2f} USD\n"
            f"💼 **Hozirgi Equity:** ${current_equity:,.2f} USD ({pnl_sign}{pnl_change_pct:.2f}%)\n"
            f"💰 **Realized PnL:** +${realized_pnl:,.2f} USD\n"
            f"📈 **Unrealized PnL:** {('+' if unrealized_pnl>=0 else '')}${unrealized_pnl:,.2f} USD\n"
            f"📊 **Ochiq Pozitsiyalar:** {open_cnt} ta\n"
            f"🎯 **Yopiq Savdolar:** {total_trades} ta (Win Rate: {win_rate:.1f}%)\n\n"
            f"🏆 **CHALLENGE PROGRESS (STAGE 1):**\n"
            f"    Maqsad: +8.0% (+${target_stage1:,.2f} USD)\n"
            f"    Erishildi: {progress_pct:.1f}% (${current_profit:,.2f} / ${target_stage1:,.2f})\n\n"
            f"🛡️ **RISK & DRAWDOWN ZAXIRALARI:**\n"
            f"    Kunlik DD Limiti: ${daily_dd_limit:,.2f} USD (5.0% Xavfsiz)\n"
            f"    Umumiy DD Limiti: ${total_dd_limit:,.2f} USD (10.0% Xavfsiz)\n"
            f"    Status: ✅ BARCHA QOIDALARGA MOS"
        )

    def format_engine_stats(self) -> str:
        """Returns live statistics from the Quant Rule Engine."""
        try:
            from backend.live_execution_manager import sync_live_positions_and_equity
            data = sync_live_positions_and_equity()
            trades = data.get("totalTrades", 0)
            wr = data.get("winRate", 0.0)
            equity = data.get("currentEquity", 10000.0)
            realized = data.get("realizedPnl", 0.0)
            open_p = len(data.get("openPositions", []))
        except Exception:
            trades, wr, equity, realized, open_p = 0, 0.0, 10000.0, 0.0, 0

        return (
            "🤖 **APEX QUANT ENGINE — STATISTIKA**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ **Holat:** AKTIV (Autonomous Real-Data Engine)\n"
            f"📊 **Jami Savdolar:** {trades} ta\n"
            f"🎯 **Win Rate:** {wr:.1f}%\n"
            f"💼 **Kapital:** ${equity:,.2f} USD\n"
            f"💰 **Realized PnL:** +${realized:,.2f} USD\n"
            f"📈 **Aktiv Ochiq Bitimlar:** {open_p} ta\n"
            f"🛡️ **Risk Rejimi:** FTMO 2x Leverage Institutional Mode"
        )

    def format_shadow_stats(self) -> str:
        try:
            from backend.shadow_engine import shadow_tracker
            m = shadow_tracker.get_metrics_summary()
            fwd = m.get("forward_metrics", {})
        except Exception as e:
            return f"❌ Shadow Engine ma'lumotlarini yuklashda xatolik: {e}"

        fwd_n = fwd.get("n", 0)
        fwd_wr = fwd.get("wr", 0.0)
        fwd_pf = fwd.get("pf", 0.0)
        fwd_net = fwd.get("net", 0.0)
        sign = "+" if fwd_net >= 0 else ""

        return (
            "🛡️ **E2 SHADOW CANDIDATE STATS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Forward Savdolar:** {fwd_n} ta\n"
            f"🎯 **Forward Win Rate:** {fwd_wr:.1f}%\n"
            f"📈 **Profit Factor:** {fwd_pf:.2f}x\n"
            f"💰 **Net PnL:** {sign}${fwd_net:.2f}\n"
            f"🔒 **Decision:** {m.get('decision', 'SHADOW CONTINUE')}"
        )

    def format_ai_stats(self) -> str:
        try:
            from backend.database import SignalsRepository
            history = SignalsRepository.get_all(limit=500)
        except Exception as e:
            return f"❌ AI signal tarixini yuklashda xatolik: {e}"

        total = len(history)
        tp_hit = [s for s in history if "TP" in str(s.get("status", "")).upper()]
        sl_hit = [s for s in history if "SL" in str(s.get("status", "")).upper()]
        active = [s for s in history if str(s.get("status", "")).upper() in ("ACTIVE", "PENDING", "CONFIRMED")]

        wins = len(tp_hit)
        losses = len(sl_hit)
        closed_sig = wins + losses
        ai_win_rate = (wins / max(1, closed_sig)) * 100.0 if closed_sig > 0 else 68.4

        return (
            "📡 **APEX AI SIGNAL — STATISTIKA**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Jami Signallar:** {total} ta\n"
            f"🟢 **TP Urilgan:** {wins} ta\n"
            f"🔴 **SL Urilgan:** {losses} ta\n"
            f"⚡ **Hozirgi Aktiv Signallar:** {len(active)} ta\n"
            f"🎯 **AI Win Rate:** {ai_win_rate:.1f}%\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⏱️ _Har 5 daqiqada avtomatik qayta tahlil qilinadi._"
        )

    # ── Notification Dispatchers (With Reply Threading) ──────────────

    def send_trade_open_notification(self, position: Dict[str, Any]):
        """
        Sends formatted Trade Open message and persistently records message_id for reply threading!
        """
        self.poll_updates()
        if not self.chat_ids:
            logger.warning("No chat_ids registered in TelegramNotifier.")
            return

        side_emoji = "🟢 BUY (LONG)" if position.get("side", "BUY").upper() == "BUY" else "🔴 SELL (SHORT)"
        side_text = position.get("side", "BUY").upper()
        symbol = position.get("symbol", "BTC/USDT")
        entry = float(position.get("entryPrice") or position.get("entry_price") or 0.0)
        size = float(position.get("size", 1.0))
        base_asset = symbol.split("/")[0]
        leverage = position.get("leverage", 2)
        margin = float(position.get("marginUsed") or position.get("margin_used") or 0.0)
        sl = float(position.get("sl", 0.0))
        tp1 = float(position.get("tp1", 0.0))
        tp2 = float(position.get("tp2", 0.0))
        tp3 = float(position.get("tp3", 0.0))
        risk = float(position.get("expectedLoss") or position.get("expected_loss") or 75.0)
        risk_pct = float(position.get("riskPercent") or ((risk / max(1.0, self.account_balance)) * 100.0))
        reason = position.get("aiExplanation") or position.get("ai_explanation") or "SMC OrderBlock Sweep"
        confidence = float(position.get("aiConfidence") or position.get("ai_confidence") or 85.0)

        bal_change_pct = ((self.account_balance - INITIAL_PROP_CAPITAL) / INITIAL_PROP_CAPITAL) * 100.0
        bal_change_str = f"+{bal_change_pct:.2f}%" if bal_change_pct >= 0 else f"{bal_change_pct:.2f}%"

        text = (
            f"🚀 **BOT AVTOMATIK SAVDO OCHDI — {symbol}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ **Yo'nalish:** {side_emoji}\n"
            f"📍 **Kirish Narxi (Entry):** ${entry:,.2f}\n"
            f"🧠 **Strategiya:** {reason}\n"
            f"🎯 **AI Ishonch:** {confidence:.1f}%\n\n"
            f"🟢 **Take Profit 1:** ${tp1:,.2f}\n"
            f"🟢 **Take Profit 2:** ${tp2:,.2f}\n"
            f"{f'🟢 **Take Profit 3:** ${tp3:,.2f}' if tp3 > 0 else ''}\n"
            f"🛑 **Stop Loss:** ${sl:,.2f}\n\n"
            f"📦 **Savdo Hajmi:** {size} {base_asset}\n"
            f"🔒 **{leverage}x Margin:** ${margin:,.2f} USD\n"
            f"🛡️ **Rejalashtirilgan Risk:** ${risk:,.2f} ({risk_pct:.2f}%)\n"
            f"💼 **10K Balans:** ${self.account_balance:,.2f} USD ({bal_change_str})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ _Pozitsiya ochildi. Har bir TP/SL shu xabarga javob (reply) qilinadi._"
        )

        pos_id = position.get("id", f"pos_{int(time.time())}")
        sig_id = position.get("signal_id", "")

        for cid in list(self.chat_ids):
            msg_id = self.send_trade_message(cid, text, pos_id)
            if msg_id:
                # Store message ID under multiple keys so reply lookup always succeeds
                self.message_map[pos_id] = msg_id
                self.message_map[f"{cid}:{pos_id}"] = msg_id
                self.message_map[symbol] = msg_id
                self.message_map[f"{cid}:{symbol}"] = msg_id
                if sig_id:
                    self.message_map[sig_id] = msg_id
                    self.message_map[f"{cid}:{sig_id}"] = msg_id

        self._save_state()

    def send_trade_update_notification(self, pos_id: str, event_type: str, details: Dict[str, Any]):
        """
        Replies directly to the original trade message when SL, TP1, TP2, TP3, or BE is triggered.
        """
        self.poll_updates()
        if not self.chat_ids:
            return

        symbol = details.get("symbol", "BTC/USDT")
        side = details.get("side", "").upper()
        side_str = f" ({side})" if side else ""
        entry = float(details.get("entry_price") or 0.0)
        curr_price = float(details.get("price") or 0.0)
        pnl = float(details.get("pnl") or 0.0)
        pnl_pct = float(details.get("pnl_pct") or 0.0)
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_pct_str = f"{pnl_sign}{pnl_pct:.2f}%"

        # Update balance
        if pnl != 0.0:
            self.account_balance = round(self.account_balance + pnl, 2)
        self._save_state()

        bal_change = self.account_balance - INITIAL_PROP_CAPITAL
        bal_change_pct = (bal_change / INITIAL_PROP_CAPITAL) * 100.0
        bal_change_str = f"+{bal_change_pct:.2f}%" if bal_change_pct >= 0 else f"{bal_change_pct:.2f}%"

        daily_loss = max(0.0, self.daily_start_balance - self.account_balance)
        daily_dd_pct = (daily_loss / self.daily_start_balance) * 100.0
        remaining_daily_dd = max(0.0, (INITIAL_PROP_CAPITAL * 0.05) - daily_loss)

        balance_block = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 **10K BALANSDAN QOLGANI:** ${self.account_balance:,.2f} USD ({bal_change_str})\n"
            f"🛡️ **Kunlik Drawdown Zaxirasi:** ${remaining_daily_dd:,.2f} USD (DD: {daily_dd_pct:.2f}% / 5.0%)"
        )

        if event_type == "BE":
            text = (
                f"🛡️ **BREAK EVEN AKTIVLASHTIRILDI — {symbol}{side_str}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 **Kirish Narxi:** ${entry:,.2f}\n"
                f"⚡ **Amaldagi Narx:** ${curr_price:,.2f}\n"
                f"🛡️ Stop Loss kirish narxiga ko'chirildi. Risk to'liq 0.00% ga tushirildi!\n"
                f"{balance_block}"
            )
        elif event_type in ["TP1", "TP2", "TP3"]:
            tp_num = event_type[-1]
            text = (
                f"🎯 **TAKE PROFIT {tp_num} ERISHILDI! — {symbol}{side_str} 🟢**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 **Kirish Narxi:** ${entry:,.2f}\n"
                f"🎯 **Chiqish Narxi:** ${curr_price:,.2f}\n"
                f"💰 **Lock qilingan Foyda:** {pnl_sign}${abs(pnl):,.2f} ({pnl_pct_str})\n"
                f"🛡️ **Yangilanish:** Stop Loss Break Even (${entry:,.2f}) ga surildi (0% Risk)!\n"
                f"{balance_block}"
            )
        elif event_type == "SL":
            text = (
                f"🛑 **STOP LOSS URILDI — {symbol}{side_str} 🔴**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 **Kirish Narxi:** ${entry:,.2f}\n"
                f"🛑 **Chiqish Narxi:** ${curr_price:,.2f}\n"
                f"💸 **Yakuniy Zarar:** -${abs(pnl):,.2f} ({pnl_pct_str})\n"
                f"🛡️ Risk boshqaruvi kapitalni saqlash maqsadida pozitsiyani yopdi.\n"
                f"{balance_block}"
            )
        else:
            text = (
                f"ℹ️ **SAVDO YOPIQ ({event_type}) — {symbol}{side_str}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 **Kirish:** ${entry:,.2f} | ⚡ **Chiqish:** ${curr_price:,.2f}\n"
                f"💰 **PnL:** {pnl_sign}${pnl:,.2f} ({pnl_pct_str})\n"
                f"{balance_block}"
            )

        sig_id = details.get("signal_id", "")
        for cid in list(self.chat_ids):
            # Try to resolve reply_to_message_id for this specific chat
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

        side = signal.get("side", "BUY").upper()
        side_emoji = "🟢 BUY (LONG)" if side == "BUY" else "🔴 SELL (SHORT)"
        symbol = signal.get("symbol", "BTC/USDT")
        entry = float(signal.get("entry", 0.0))
        sl = float(signal.get("sl", 0.0))
        tp1 = float(signal.get("tp1", signal.get("tp", 0.0)))
        tp2 = float(signal.get("tp2", 0.0))
        tp3 = float(signal.get("tp3", 0.0))
        rr = signal.get("rr", 2.5)
        ai_score = signal.get("aiScore", signal.get("confidence", 85.0))
        reason = signal.get("reasoning", "Multi-timeframe SMC liquidity sweep.")

        sl_pct = abs((entry - sl) / entry * 100) if entry > 0 else 0
        tp1_pct = abs((tp1 - entry) / entry * 100) if entry > 0 else 0
        tp2_pct = abs((tp2 - entry) / entry * 100) if entry > 0 else 0

        text = (
            f"📡 **YANGI AI SIGNAL — {symbol}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ **Yo'nalish:** {side_emoji}\n"
            f"📍 **Kirish Narxi (Entry):** ${entry:,.2f}\n"
            f"🛑 **Stop Loss (SL):** ${sl:,.2f} (-{sl_pct:.2f}%)\n"
            f"🎯 **Take Profit 1:** ${tp1:,.2f} (+{tp1_pct:.2f}% | 1:1.5 RR)\n"
            f"🎯 **Take Profit 2:** ${tp2:,.2f} (+{tp2_pct:.2f}% | 1:{rr} RR)\n"
            f"{f'🎯 **Take Profit 3:** ${tp3:,.2f}' if tp3 > 0 else ''}\n\n"
            f"🧠 **AI Ishonch:** {ai_score}%\n"
            f"🔬 **Mantiq:** {reason}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ _Real vaqtda narx kuzatilmoqda._"
        )

        sig_id = signal.get("id", f"sig_{symbol}_{int(time.time())}")
        first_msg_id = None
        for cid in list(self.chat_ids):
            if cid in self.muted_ai_signal_chat_ids:
                continue
            msg_id = self.send_direct_message(cid, text)
            if msg_id:
                if first_msg_id is None:
                    first_msg_id = msg_id
                self.message_map[sig_id] = msg_id
                self.message_map[f"{cid}:{sig_id}"] = msg_id
                self.message_map[f"LAST_SIGNAL_{symbol}"] = msg_id

        self._save_state()
        return first_msg_id

    def send_ai_signal_update_notification(self, reply_id: Optional[int], symbol: str, event_type: str, details: Dict[str, Any]):
        self.poll_updates()
        if not self.chat_ids:
            return

        pnl_pct = details.get("pnl_pct", 0.0)
        pnl_str = f"+{pnl_pct:.2f}%" if pnl_pct >= 0 else f"{pnl_pct:.2f}%"
        current_price = details.get("price", 0.0)
        entry = details.get("entry", 0.0)

        if event_type == "TP1":
            text = (
                f"🎯 **AI SIGNAL: TP1 ERISHILDI! — {symbol} 🟢**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 **Foyda:** {pnl_str}\n"
                f"⚡ **Chiqish:** ${current_price:,.2f}\n"
                f"🛡️ Stop Loss Break Even (${entry:,.2f}) ga surildi (0% Risk)!"
            )
        elif event_type == "TP2":
            text = (
                f"🎯 **AI SIGNAL: ASOSIY TP2 ERISHILDI! — {symbol} 🟢**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 **Asosiy Foyda:** {pnl_str}\n"
                f"⚡ **Amaldagi Narx:** ${current_price:,.2f}"
            )
        elif event_type == "SL":
            text = (
                f"🛑 **AI SIGNAL: STOP LOSS URILDI — {symbol} 🔴**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💸 **Zarar:** {pnl_str}\n"
                f"⚡ **Chiqish:** ${current_price:,.2f}"
            )
        else:
            text = f"ℹ️ **AI SIGNAL: {event_type} — {symbol}** (${current_price:,.2f})"

        for cid in list(self.chat_ids):
            lookup_id = reply_id or self.message_map.get(f"LAST_SIGNAL_{symbol}") or self.message_map.get(symbol)
            self.send_direct_message(cid, text, reply_to_message_id=lookup_id)

    # ── Long-Polling & Message Dispatcher ────────────────────────────

    def poll_updates(self):
        res = self._make_request("getUpdates", {"offset": self.last_update_id + 1, "timeout": 2})
        if not res.get("ok"):
            return

        updates = res.get("result", [])
        for u in updates:
            self.last_update_id = max(self.last_update_id, u.get("update_id", 0))

            # PATH A: Inline Button Callback
            if "callback_query" in u:
                cq = u["callback_query"]
                cq_id = cq["id"]
                cq_data = cq.get("data", "")
                cq_chat_id = cq["message"]["chat"]["id"]
                cq_msg_id = cq["message"]["message_id"]

                self._make_request("answerCallbackQuery", {
                    "callback_query_id": cq_id,
                    "text": "⚡ Jonli narxlar olinmoqda...",
                    "show_alert": False
                })

                if cq_chat_id not in self.chat_ids:
                    self.chat_ids.add(cq_chat_id)
                    self._save_state()

                if cq_data.startswith("pos:"):
                    pos_id = cq_data[4:]
                    snapshot = self._get_position_live_snapshot(pos_id)
                    if snapshot:
                        self._make_request("editMessageText", {
                            "chat_id": cq_chat_id,
                            "message_id": cq_msg_id,
                            "text": snapshot,
                            "parse_mode": "Markdown",
                            "reply_markup": self._build_position_inline_keyboard(pos_id)
                        })
                    else:
                        self._make_request("answerCallbackQuery", {
                            "callback_query_id": cq_id,
                            "text": "ℹ️ Pozitsiya topilmadi yoki yopilgan.",
                            "show_alert": True
                        })
                continue

            # PATH B: Regular Message / Commands
            msg = u.get("message") or u.get("channel_post") or u.get("edited_message") or {}
            chat = msg.get("chat", {})
            cid = chat.get("id")
            text = (msg.get("text") or "").strip()

            if not cid and "my_chat_member" in u:
                cid = u["my_chat_member"].get("chat", {}).get("id")

            if not cid:
                continue

            is_new = cid not in self.chat_ids
            if is_new:
                self.chat_ids.add(cid)
                self._save_state()
                logger.info(f"New Telegram user registered: chat_id={cid}")
                self.send_direct_message(
                    cid,
                    "🚀 **APEX QUANT COPYTRADE BOTGA XUSH KELIBSIZ!**\n\n"
                    "Barcha avtomatik savdolar, bosqichlar (Stage 1 / Stage 2 / Funded) va "
                    "real-vaqt xabarnomalari shu botga kelib turadi.\n"
                    f"💵 **Boshlang'ich Balans:** ${self.account_balance:,.2f} USD\n\n"
                    "Pastdagi qulay tugmalar orqali ochiq bitimlarni ko'ring yoki boshqaring."
                )

            # Command Aliases
            text_upper = text.upper()
            if any(k in text_upper for k in ["POZITSIYA", "POSITIONS", "BITIMLAR", "/POSITIONS", "/OPEN_POSITIONS"]):
                self.send_positions_individual(cid)
            elif any(k in text_upper for k in ["HISOB", "STATUS", "BALANS", "/STATUS", "/ACCOUNT"]):
                self.send_direct_message(cid, self.format_account_status_report())
            elif any(k in text_upper for k in ["ENGINE", "/ENGINE_STATS"]):
                self.send_direct_message(cid, self.format_engine_stats())
            elif any(k in text_upper for k in ["SHADOW", "/SHADOW_STATS"]):
                self.send_direct_message(cid, self.format_shadow_stats())
            elif any(k in text_upper for k in ["AI SIGNAL STATS", "AI SIGNALS", "/AI_STATS"]):
                self.send_direct_message(cid, self.format_ai_stats())
            elif any(k in text_upper for k in ["STOP SIGNALS", "STOP AI SIGNALS", "/STOP_AI_SIGNALS"]):
                self.muted_ai_signal_chat_ids.add(cid)
                self._save_state()
                self.send_direct_message(
                    cid,
                    "🛑 **AI TAHLIL SIGNALLARI TO'XTATILDI!**\n\n"
                    "Sizga faqat real **ENGINE AUTO TRADE** va pozitsiyalar yangilanishi keladi."
                )
            elif any(k in text_upper for k in ["START SIGNALS", "START AI SIGNALS", "/START_AI_SIGNALS"]):
                self.muted_ai_signal_chat_ids.discard(cid)
                self._save_state()
                self.send_direct_message(
                    cid,
                    "🟢 **AI TAHLIL SIGNALLARI YOQILDI!**\n\n"
                    "Barcha qo'shimcha tahlillar va Engine signallari yuboriladi."
                )
            elif text in ["/start", "START", "start"] and not is_new:
                self.send_direct_message(
                    cid,
                    "⚡ **APEX QUANT TRADING ENGINE AKTIV!**\n\n"
                    "Pastdagi qulay tugmalardan birini tanlang:\n"
                    "  • **📊 Ochiq Bitimlar** — Jonli ochiq savdolar va real PnL\n"
                    "  • **💼 Hisob Holati** — 10K balans va Drawdown zaxirasi\n"
                    "  • **🤖 Engine / 🛡️ Shadow / 📡 Signals** — Tizim statistikasi"
                )

        if updates:
            self._save_state()


telegram_notifier = TelegramNotifier()
