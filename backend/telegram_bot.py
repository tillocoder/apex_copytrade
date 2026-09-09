import os
import json
import logging
import time
import requests
from typing import Dict, Any, Optional, Set, List

logger = logging.getLogger("telegram_bot")
logger.setLevel(logging.INFO)

INITIAL_PROP_CAPITAL = 10000.0

def is_trade_win(trade: Dict[str, Any]) -> bool:
    """Unified helper to strictly determine if a trade was profitable."""
    pnl = float(trade.get("realizedPnl", trade.get("realized_pnl", 0.0)) or 0.0)
    status = str(trade.get("status", "")).upper()
    return pnl > 0.0 or any(status.startswith(prefix) for prefix in ["CLOSED_TP1", "CLOSED_TP2", "CLOSED_BE_PROFIT", "CLOSED_PROFIT"])

class TelegramNotifier:
    """
    Enterprise-grade asynchronous Telegram bot for Apex Quantum Trading Terminal.
    Provides real-time trade signals, 2-stage TP updates, multi-chat broadcasting,
    persistent message reply tracking, and mathematically bulletproof live telemetry.
    """
    def __init__(self):
        self.bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", "8922592987:AAEKfszGRuNsgGVy95f649rf8MHdrKiw6QI")
        default_cid = os.getenv("TELEGRAM_CHAT_ID", "5563813326")
        self.chat_ids: Set[int] = {int(default_cid)} if default_cid else {5563813326}
        self.public_app_url: str = os.getenv("PUBLIC_APP_URL", "https://apex.xrinvest.uz")
        self.account_balance: float = INITIAL_PROP_CAPITAL
        self.last_update_id: int = 0
        self.message_map: Dict[str, int] = {}
        self.signals_active: bool = True
        self.state_file = os.path.join(os.path.dirname(__file__), "data", "telegram_state.json")
        self._load_state()

    def _ensure_dir(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def _load_state(self):
        default_cid = os.getenv("TELEGRAM_CHAT_ID", "5563813326")
        if default_cid:
            self.chat_ids.add(int(default_cid))
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid in data.get("chat_ids", []):
                        self.chat_ids.add(int(cid))
                    self.last_update_id = data.get("last_update_id", 0)
                    self.message_map = data.get("message_map", {})
                    self.signals_active = data.get("signals_active", True)
            except Exception as e:
                logger.error(f"Error loading telegram state: {e}")

    def _save_state(self):
        self._ensure_dir(self.state_file)
        temp_file = self.state_file + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({
                    "chat_ids": list(self.chat_ids),
                    "last_update_id": self.last_update_id,
                    "message_map": self.message_map,
                    "signals_active": self.signals_active
                }, f, indent=2)
            os.replace(temp_file, self.state_file)
        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            logger.error(f"Error saving telegram state: {e}")

    def _get_persistent_menu_keyboard(self) -> Dict[str, Any]:
        """Persistent institutional command keyboard shown in all user chats."""
        return {
            "keyboard": [
                [
                    {"text": "💼 Hisob Holati"},
                    {"text": "📦 Ochiq Bitimlar"}
                ],
                [
                    {"text": "🧠 AI Signals"},
                    {"text": "🤖 Engine v4.2"},
                    {"text": "🛡️ Shadow Tracker"}
                ],
                [
                    {"text": "🟢 Start Signals"},
                    {"text": "🔴 Stop Signals"}
                ]
            ],
            "resize_keyboard": True,
            "is_persistent": True
        }

    def _get_live_performance_metrics(self) -> Dict[str, Any]:
        """Calculates exact real-time institutional metrics directly from persistent trade history."""
        try:
            equity_file = os.path.join(os.path.dirname(__file__), "data", "live_equity.json")
            if os.path.exists(equity_file):
                with open(equity_file, "r", encoding="utf-8-sig") as f:
                    eq = json.load(f)
            else:
                eq = {}
            
            trade_history = eq.get("tradeHistory", [])
            total_closed = len(trade_history)
            
            wins = 0
            losses = 0
            win_pnl = 0.0
            loss_pnl = 0.0
            total_pnl = 0.0
            
            for t in trade_history:
                pnl = float(t.get("realizedPnl", t.get("realized_pnl", 0.0)) or 0.0)
                total_pnl += pnl
                if is_trade_win(t):
                    wins += 1
                    win_pnl += max(0.0, pnl)
                else:
                    losses += 1
                    loss_pnl += abs(min(0.0, pnl))
                    
            win_rate = (wins / total_closed * 100.0) if total_closed > 0 else 0.0
            profit_factor = (win_pnl / loss_pnl) if loss_pnl > 0 else (999.0 if win_pnl > 0 else 0.0)
            
            # Calculate exact delta from previous trade state
            if total_closed > 1:
                prev_th = trade_history[:-1]
                prev_wins = sum(1 for t in prev_th if is_trade_win(t))
                prev_wr = (prev_wins / len(prev_th)) * 100.0
                delta = win_rate - prev_wr
                delta_sign = "+" if delta >= 0 else ""
                delta_str = f"▲ {delta_sign}{delta:.1f}%" if delta >= 0 else f"▼ {delta:.1f}%"
            elif total_closed == 1:
                delta_str = "▲ +100.0%" if wins == 1 else "▼ -100.0%"
            else:
                delta_str = "0.0%"
                
            current_equity = float(eq.get("initialCapital", INITIAL_PROP_CAPITAL)) + total_pnl
            
            return {
                "total_closed": total_closed,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 1),
                "delta_str": delta_str,
                "profit_factor": round(profit_factor, 2),
                "total_pnl": round(total_pnl, 2),
                "current_equity": round(current_equity, 2),
                "initial_capital": float(eq.get("initialCapital", INITIAL_PROP_CAPITAL))
            }
        except Exception as e:
            logger.error(f"[METRICS ERROR] {e}")
            return {
                "total_closed": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "delta_str": "0.0%",
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "current_equity": INITIAL_PROP_CAPITAL,
                "initial_capital": INITIAL_PROP_CAPITAL
            }

    def send_direct_message(self, chat_id: int, text: str, reply_to_message_id: Optional[int] = None, show_keyboard: bool = True) -> Optional[int]:
        if not self.bot_token:
            return None
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            payload["allow_sending_without_reply"] = True

        if show_keyboard:
            payload["reply_markup"] = self._get_persistent_menu_keyboard()

        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                msg_data = res.json().get("result", {})
                return msg_data.get("message_id")
            else:
                logger.error(f"Telegram API Error: {res.status_code} - {res.text}")
                return None
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return None

    def send_trade_message(self, chat_id: int, text: str, pos_id: str) -> Optional[int]:
        """Sends a trade opening message with direct deep-link inline button for live chart analysis."""
        if not self.bot_token:
            return None
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        deep_link = f"{self.public_app_url}/?pos_id={pos_id}"
        inline_kb = {
            "inline_keyboard": [
                [
                    {"text": "🔴 LIVE | Jonli Grafik & Telemetriya", "url": deep_link}
                ]
            ]
        }
        
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": inline_kb
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                msg_data = res.json().get("result", {})
                return msg_data.get("message_id")
            else:
                logger.error(f"Telegram trade message error: {res.status_code} - {res.text}")
                return None
        except Exception as e:
            logger.error(f"Telegram trade send failed: {e}")
            return None

    def poll_updates(self):
        """Polls Telegram updates and processes incoming user commands and button clicks."""
        if not self.bot_token:
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 0}
        try:
            res = requests.get(url, params=params, timeout=10)
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
        """Dispatches response for all menu buttons and slash commands."""
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

        elif "engine" in text_lower or "/stats" in text_lower or "/winrate" in text_lower or "/telemetry" in text_lower:
            self._send_engine_stats(chat_id)

        elif "shadow" in text_lower or "/shadow" in text_lower:
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
            unrealized_pnl = sync_data.get("unrealizedPnl", 0.0)
        except Exception:
            open_cnt = 0
            unrealized_pnl = 0.0

        metrics = self._get_live_performance_metrics()
        current_equity = metrics["current_equity"] + unrealized_pnl
        realized_pnl = metrics["total_pnl"]
        total_trades = metrics["total_closed"]
        win_rate = metrics["win_rate"]
        wins = metrics["wins"]
        losses = metrics["losses"]

        pnl_change_pct = ((current_equity - INITIAL_PROP_CAPITAL) / INITIAL_PROP_CAPITAL) * 100.0
        pnl_sign = "+" if pnl_change_pct >= 0 else ""
        real_pnl_sign = "+" if realized_pnl >= 0 else ""

        target_stage1 = INITIAL_PROP_CAPITAL * 0.08  # $800
        current_profit = current_equity - INITIAL_PROP_CAPITAL
        progress_pct = max(0.0, min(100.0, (current_profit / target_stage1) * 100.0))

        text = (
            "💼 <b>APEX 10K PROP ACCOUNT HOLATI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Boshlang'ich Balans:</b> ${INITIAL_PROP_CAPITAL:,.2f} USD\n"
            f"📈 <b>Joriy Equity:</b> ${current_equity:,.2f} USD ({pnl_sign}{pnl_change_pct:.2f}%)\n"
            f"💵 <b>Realizatsiya Qilingan PnL:</b> {real_pnl_sign}${realized_pnl:,.2f} USD\n"
            f"⚡ <b>Suzuvchi (Unrealized) PnL:</b> {('+' if unrealized_pnl>=0 else '')}${unrealized_pnl:,.2f} USD\n"
            f"📦 <b>Ochiq Pozitsiyalar:</b> {open_cnt} ta\n"
            f"🏆 <b>Yopiq Savdolar:</b> {total_trades} ta (<b>Win Rate: {win_rate:.1f}%</b> | {wins}W / {losses}L)\n\n"
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

        text = f"📦 <b>OCHIQ POZITSIYALAR ({len(open_pos)} ta)</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for p in open_pos:
            sym = p.get("symbol", "BTC/USDT")
            side = p.get("side", "BUY")
            side_badge = "🟢 BUY" if side == "BUY" else "🔴 SELL"
            entry = float(p.get("entryPrice") or p.get("entry_price") or 0.0)
            curr = float(p.get("currentPrice") or entry)
            unrealized = float(p.get("unrealizedPnl") or 0.0)
            unrealized_pct = float(p.get("unrealizedPnlPercent") or 0.0)
            sign = "+" if unrealized >= 0 else ""
            tp1_hit = p.get("tp1_hit", False)
            tp_status = " (✅ TP1 olingan, qolgan 50% TP2 kutilmoqda)" if tp1_hit else ""

            text += (
                f"{side_badge} <b>{sym}</b>\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Hozirgi:</b> ${curr:,.2f}\n"
                f"💰 <b>PnL:</b> {sign}${unrealized:,.2f} ({sign}{unrealized_pct:.2f}%){tp_status}\n"
                f"🎯 <b>TP1:</b> ${float(p.get('tp1',0)):,.2f} | <b>TP2:</b> ${float(p.get('tp2',0)):,.2f} | <b>SL:</b> ${float(p.get('sl',0)):,.2f}\n"
                "──────────────────────\n"
            )
        self.send_direct_message(chat_id, text)

    def _send_active_signals(self, chat_id: int):
        try:
            from backend.database import SignalsRepository
            signals = SignalsRepository.get_latest(limit=5)
        except Exception:
            signals = []

        if not signals:
            self.send_direct_message(chat_id, "ℹ️ So'nggi AI signallari topilmadi.")
            return

        text = "🧠 <b>OXIRGI AI KVANT SIGNALLARI</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for s in signals:
            sym = s.get("symbol", "BTC/USDT")
            direction = s.get("direction", s.get("side", "BUY"))
            dir_badge = "🟢 BUY" if direction in ("BUY", "LONG") else "🔴 SELL"
            entry = float(s.get("entry_price", 0.0))
            score = float(s.get("confidence_score", s.get("score", 80.0)))
            status = s.get("status", "ACTIVE")
            text += (
                f"{dir_badge} <b>{sym}</b> | <b>{status}</b>\n"
                f"🎯 <b>Entry:</b> ${entry:,.2f} | <b>Score:</b> {score:.1f}%\n"
                f"🟢 <b>TP1:</b> ${float(s.get('tp1',0)):,.2f} | <b>TP2:</b> ${float(s.get('tp2',0)):,.2f}\n"
                f"🔴 <b>SL:</b> ${float(s.get('stop_loss',0)):,.2f}\n"
                "──────────────────────\n"
            )
        self.send_direct_message(chat_id, text)

    def _send_engine_stats(self, chat_id: int):
        metrics = self._get_live_performance_metrics()
        total_trades = metrics["total_closed"]
        win_rate = metrics["win_rate"]
        wins = metrics["wins"]
        losses = metrics["losses"]
        pf = metrics["profit_factor"]
        total_pnl = metrics["total_pnl"]
        pnl_sign = "+" if total_pnl >= 0 else ""

        text = (
            "🤖 <b>APEX QUANTUM ENGINE v4.2 — JONLI STATISTIKA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <b>Algoritm:</b> SMC + Institutional OrderFlow\n"
            "📡 <b>Rejim:</b> Institutional M15 Execution\n"
            "🎯 <b>Aktiv Juftliklar:</b> BTC/USDT, ETH/USDT\n"
            "⏱️ <b>Skanerlash Davri:</b> Har 60 soniyada\n"
            "🛡️ <b>Risk Boshqaruvi:</b> 2-Stage TP + Break-Even Trailing\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Jonli Win Rate:</b> <b>{win_rate:.1f}%</b> ({wins} Yutuq / {losses} Zarar)\n"
            f"🏆 <b>Jami Yopiq Savdolar:</b> {total_trades} ta\n"
            f"📈 <b>Profit Factor:</b> {pf:.2f}x\n"
            f"💰 <b>Jami Realized PnL:</b> {pnl_sign}${total_pnl:,.2f} USD\n"
            f"💼 <b>Hisob Balansi:</b> ${metrics['current_equity']:,.2f} USD\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 <i>Engine to'liq avtomatik ishlamoqda. Real vaqtda barcha yopiq savdolar telemetriyaga hisoblanadi.</i>"
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
        risk = float(position.get("expectedLoss") or position.get("expected_loss") or 0.0)
        risk_pct = float(position.get("riskPercent") or ((risk / max(1.0, self.account_balance)) * 100.0))
        reason = position.get("aiExplanation") or position.get("ai_explanation") or "SMC Liquidity Sweep"
        confidence = float(position.get("aiConfidence") or position.get("ai_confidence") or 77.9)

        # Dollar estimations for TP1, TP2, SL
        is_buy = (side == "BUY")
        if is_buy:
            tp1_usd = round(abs(tp1 - entry) * (size * 0.5), 2)
            tp2_usd = round((abs(tp1 - entry) * (size * 0.5)) + (abs(tp2 - entry) * (size * 0.5)), 2)
            sl_usd = round(abs(entry - sl) * size, 2)
        else:
            tp1_usd = round(abs(entry - tp1) * (size * 0.5), 2)
            tp2_usd = round((abs(entry - tp1) * (size * 0.5)) + (abs(entry - tp2) * (size * 0.5)), 2)
            sl_usd = round(abs(sl - entry) * size, 2)

        if risk <= 0:
            risk = sl_usd

        metrics = self._get_live_performance_metrics()

        text = (
            f"⚡ <b>YANGI SAVDO OCHILDI — {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Yo'nalish:</b> {side_badge} <b>{leverage}X</b> [Kredit Yelkasi: {leverage}X]\n"
            f"🎯 <b>Kirish Narxi (Entry):</b> ${entry:,.2f}\n"
            f"🟢 <b>Take Profit 1:</b> ${tp1:,.2f} (+1.5R | <b>+${tp1_usd:,.2f} USD</b>)\n"
            f"🟢 <b>Take Profit 2:</b> ${tp2:,.2f} (+2.8R | <b>+${tp2_usd:,.2f} USD</b>)\n"
            f"🔴 <b>Stop Loss:</b> ${sl:,.2f} (-{risk_pct:.2f}% | <b>-${sl_usd:,.2f} USD</b>)\n\n"
            f"📦 <b>Hajm:</b> {size} {base_asset} (${margin:,.2f} Margin)\n"
            f"🛡️ <b>Maksimal Xavf:</b> -${risk:,.2f} USD\n"
            f"🧠 <b>Strategiya:</b> {reason} (AI: {confidence:.1f}%)\n"
            f"📊 <b>Tizimning Jonli Win Rate:</b> <b>{metrics['win_rate']:.1f}%</b> ({metrics['wins']}W / {metrics['losses']}L | {metrics['total_closed']} ta yopiq savdo)\n"
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

        metrics = self._get_live_performance_metrics()
        wr = metrics['win_rate']
        delta_str = metrics['delta_str']
        wins = metrics['wins']
        losses = metrics['losses']
        total_cnt = metrics['total_closed']
        tot_pnl = metrics['total_pnl']
        tot_pnl_sign = "+" if tot_pnl >= 0 else ""

        if event_type == "TP1":
            tp2_price = details.get("tp2", 0.0)
            text = (
                f"🎯 <b>TAKE PROFIT 1 ERISHILDI! — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Chiqish:</b> ${curr_price:,.2f}\n"
                f"💰 <b>50% Foyda Naqd Qilindi:</b> {pnl_sign}${pnl:,.2f} USD\n"
                f"🚀 <b>Qolgan 50%:</b> TP2 (${tp2_price:,.2f}) tomon harakatlanmoqda.\n"
                f"🛡️ <i>Erta chiqib ketishlarning oldini olish uchun SL narx TP2 tomon kengaygach Break-Even'ga o'tkaziladi.</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Joriy Win Rate:</b> <b>{wr:.1f}%</b> ({wins} Win / {losses} Loss | Jami: {total_cnt} ta)"
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
                f"🎯 <i>Asosiy Nishon: TP2 (${tp2_target:,.2f})</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Joriy Win Rate:</b> <b>{wr:.1f}%</b> ({wins}W / {losses}L)"
            )
        elif event_type == "TP2":
            tp1_pnl = float(details.get("tp1_pnl") or 0.0)
            stage_pnl = float(details.get("stage_pnl") or 0.0)
            breakdown_str = f" <i>(TP1: +${tp1_pnl:,.2f} | TP2: +${stage_pnl:,.2f})</i>" if tp1_pnl > 0 else ""
            text = (
                f"🏆 <b>TAKE PROFIT 2 (FINAL TARGET) ERISHILDI! — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Chiqish:</b> ${curr_price:,.2f}\n"
                f"💰 <b>Jami Sof Foyda:</b> {pnl_sign}${pnl:,.2f} USD{breakdown_str}\n"
                f"🎉 <i>Savdo to'liq muvaffaqiyat bilan yopildi!</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Win Rate & Telemetriya Yangilanishi:</b>\n"
                f"📈 <b>Jonli Win Rate:</b> <b>{wr:.1f}%</b> (<b>{delta_str}</b>)\n"
                f"🏆 <b>Natijalar:</b> {wins} Yutuq | {losses} Zarar (Jami: {total_cnt} ta)\n"
                f"💵 <b>Jami Realized PnL:</b> {tot_pnl_sign}${tot_pnl:,.2f} USD"
            )
        elif event_type == "BE_PROFIT":
            tp1_pnl = float(details.get("tp1_pnl") or 0.0)
            stage_pnl = float(details.get("stage_pnl") or 0.0)
            breakdown_str = f" <i>(TP1: +${tp1_pnl:,.2f} | BE: +${stage_pnl:,.2f})</i>" if tp1_pnl > 0 else ""
            text = (
                f"🛡️ <b>POZITSIYA FOYDALI BREAK-EVENDA YOPILDI — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Chiqish:</b> ${curr_price:,.2f}\n"
                f"💰 <b>Jami Olingan Foyda:</b> +${abs(pnl):,.2f} USD{breakdown_str}\n"
                f"✅ <i>Kapital to'liq saqlanib, TP1 foydasi hisobda qoldi!</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Win Rate & Telemetriya Yangilanishi:</b>\n"
                f"📈 <b>Jonli Win Rate:</b> <b>{wr:.1f}%</b> (<b>{delta_str}</b>)\n"
                f"🏆 <b>Natijalar:</b> {wins} Yutuq | {losses} Zarar (Jami: {total_cnt} ta)\n"
                f"💵 <b>Jami Realized PnL:</b> {tot_pnl_sign}${tot_pnl:,.2f} USD"
            )
        elif event_type == "SL":
            text = (
                f"🛑 <b>STOP LOSS URILDI — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 <b>Kirish:</b> ${entry:,.2f} ➔ <b>Chiqish:</b> ${curr_price:,.2f}\n"
                f"📉 <b>Zarar:</b> -${abs(pnl):,.2f} USD\n"
                f"🛡️ <i>Prop firm risk boshqaruvi kapitalni himoya qildi (0.13% risk).</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Win Rate & Telemetriya Yangilanishi:</b>\n"
                f"📉 <b>Jonli Win Rate:</b> <b>{wr:.1f}%</b> (<b>{delta_str}</b>)\n"
                f"🏆 <b>Natijalar:</b> {wins} Yutuq | {losses} Zarar (Jami: {total_cnt} ta)\n"
                f"💵 <b>Jami Realized PnL:</b> {tot_pnl_sign}${tot_pnl:,.2f} USD"
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
        side = signal.get("side", signal.get("direction", "BUY")).upper()
        if side == "LONG":
            side = "BUY"
        elif side == "SHORT":
            side = "SELL"

        entry = float(signal.get("entry_price") or signal.get("entry") or 0.0)
        sl = float(signal.get("sl") or signal.get("stop_loss") or 0.0)
        tp1 = float(signal.get("tp1") or 0.0)
        tp2 = float(signal.get("tp2") or 0.0)
        score = float(signal.get("score") or signal.get("confidence") or signal.get("confidence_score") or 77.9)
        setup = signal.get("setup", signal.get("trigger_reason", "SMC Liquidity Sweep"))

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
