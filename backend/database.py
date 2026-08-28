import sqlite3
import json
import time
import os
from typing import Dict, Any, List, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "data", "apex_production.db")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Signals Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        type TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        stop_loss REAL NOT NULL,
        tp1 REAL NOT NULL,
        tp2 REAL NOT NULL,
        tp3 REAL NOT NULL,
        risk_reward REAL NOT NULL,
        confidence_score REAL NOT NULL,
        status TEXT NOT NULL,
        trigger_reason TEXT,
        lead_quant_analysis TEXT,
        verification_matrix TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        closed_at TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol_status ON signals(symbol, status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at DESC);")

    # 2. Positions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        mark_price REAL NOT NULL,
        size REAL NOT NULL,
        margin REAL NOT NULL,
        leverage REAL NOT NULL,
        stop_loss REAL NOT NULL,
        take_profit REAL NOT NULL,
        tp1 REAL,
        tp2 REAL,
        tp3 REAL,
        unrealized_pnl REAL NOT NULL,
        realized_pnl REAL NOT NULL,
        pnl_pct REAL NOT NULL,
        status TEXT NOT NULL,
        liquidation_price REAL,
        opened_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        closed_at TEXT,
        close_reason TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);")

    # 3. Trade Journal Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_journal (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL NOT NULL,
        pnl REAL NOT NULL,
        pnl_pct REAL NOT NULL,
        status TEXT NOT NULL,
        strategy_tag TEXT,
        notes TEXT,
        emotion TEXT,
        screenshot_url TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_journal_user ON trade_journal(user_id, created_at DESC);")

    # 4. Strategy & System Configuration Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_config (
        config_key TEXT PRIMARY KEY,
        config_value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 5. Audit & Activity Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        category TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        metadata TEXT
    );
    """)

    conn.commit()
    conn.close()

# Initialize schema on module load
init_db()

# ==========================================
# FULL CRUD OPERATIONS FOR SIGNALS
# ==========================================
class SignalsRepository:
    @staticmethod
    def get_all(limit: int = 100, status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM signals WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
        else:
            cursor.execute("SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(sig_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals WHERE id = ?", (sig_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def save_or_update(sig: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Serialize nested JSON objects
        v_matrix = json.dumps(sig.get("verification_matrix", [])) if isinstance(sig.get("verification_matrix"), list) else sig.get("verification_matrix", "[]")
        
        cursor.execute("""
        INSERT INTO signals (
            id, symbol, type, timeframe, direction, entry_price, stop_loss, tp1, tp2, tp3,
            risk_reward, confidence_score, status, trigger_reason, lead_quant_analysis,
            verification_matrix, created_at, updated_at, closed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            stop_loss = excluded.stop_loss,
            tp1 = excluded.tp1,
            tp2 = excluded.tp2,
            tp3 = excluded.tp3,
            status = excluded.status,
            confidence_score = excluded.confidence_score,
            updated_at = excluded.updated_at,
            closed_at = excluded.closed_at
        """, (
            sig.get("id"),
            sig.get("symbol", "BTC/USDT"),
            sig.get("type", "SMC OrderBlock Sweep"),
            sig.get("timeframe", "15m"),
            sig.get("direction", "LONG"),
            float(sig.get("entry_price", sig.get("price", 0.0))),
            float(sig.get("stop_loss", 0.0)),
            float(sig.get("tp1", sig.get("take_profit", 0.0))),
            float(sig.get("tp2", 0.0)),
            float(sig.get("tp3", 0.0)),
            float(sig.get("risk_reward", 2.5)),
            float(sig.get("confidence_score", 85.0)),
            sig.get("status", "ACTIVE"),
            sig.get("trigger_reason", "SMC Liquidity Sweep"),
            sig.get("lead_quant_analysis", "Institutional Order Flow Analysis"),
            v_matrix,
            sig.get("created_at", sig.get("timestamp", now)),
            now,
            sig.get("closed_at")
        ))
        conn.commit()
        conn.close()
        return sig

    @staticmethod
    def delete(sig_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM signals WHERE id = ?", (sig_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

# ==========================================
# FULL CRUD OPERATIONS FOR POSITIONS
# ==========================================
class PositionsRepository:
    @staticmethod
    def get_live() -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions WHERE status IN ('OPEN', 'ACTIVE', 'PENDING') ORDER BY opened_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_all(limit: int = 100) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions ORDER BY opened_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def save_or_update(pos: Dict[str, Any]):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cursor.execute("""
        INSERT INTO positions (
            id, symbol, direction, entry_price, mark_price, size, margin, leverage,
            stop_loss, take_profit, tp1, tp2, tp3, unrealized_pnl, realized_pnl,
            pnl_pct, status, liquidation_price, opened_at, updated_at, closed_at, close_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            mark_price = excluded.mark_price,
            stop_loss = excluded.stop_loss,
            take_profit = excluded.take_profit,
            unrealized_pnl = excluded.unrealized_pnl,
            realized_pnl = excluded.realized_pnl,
            pnl_pct = excluded.pnl_pct,
            status = excluded.status,
            updated_at = excluded.updated_at,
            closed_at = excluded.closed_at,
            close_reason = excluded.close_reason
        """, (
            pos.get("id"),
            pos.get("symbol", "BTC/USDT"),
            pos.get("direction", "LONG"),
            float(pos.get("entry_price", 0.0)),
            float(pos.get("mark_price", pos.get("entry_price", 0.0))),
            float(pos.get("size", 0.1)),
            float(pos.get("margin", 500.0)),
            float(pos.get("leverage", 2.0)),
            float(pos.get("stop_loss", 0.0)),
            float(pos.get("take_profit", 0.0)),
            float(pos.get("tp1", 0.0)),
            float(pos.get("tp2", 0.0)),
            float(pos.get("tp3", 0.0)),
            float(pos.get("unrealized_pnl", 0.0)),
            float(pos.get("realized_pnl", 0.0)),
            float(pos.get("pnl_pct", 0.0)),
            pos.get("status", "OPEN"),
            float(pos.get("liquidation_price", 0.0)) if pos.get("liquidation_price") else None,
            pos.get("opened_at", now),
            now,
            pos.get("closed_at"),
            pos.get("close_reason")
        ))
        conn.commit()
        conn.close()

    @staticmethod
    def close_position(pos_id: str, exit_price: float, realized_pnl: float, reason: str = "MANUAL_CLOSE"):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cursor.execute("""
        UPDATE positions SET
            status = 'CLOSED',
            mark_price = ?,
            realized_pnl = ?,
            unrealized_pnl = 0.0,
            closed_at = ?,
            close_reason = ?,
            updated_at = ?
        WHERE id = ?
        """, (exit_price, realized_pnl, now, reason, now, pos_id))
        conn.commit()
        conn.close()

# ==========================================
# FULL CRUD OPERATIONS FOR TRADE JOURNAL
# ==========================================
class JournalRepository:
    @staticmethod
    def get_by_user(user_id: str = "usr_owner_01") -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_journal WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(trade_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_journal WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create_or_update(entry: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        trade_id = entry.get("id") or f"jnl_{int(time.time()*1000)}"
        entry["id"] = trade_id

        cursor.execute("""
        INSERT INTO trade_journal (
            id, user_id, symbol, direction, entry_price, exit_price, pnl, pnl_pct,
            status, strategy_tag, notes, emotion, screenshot_url, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            symbol = excluded.symbol,
            direction = excluded.direction,
            entry_price = excluded.entry_price,
            exit_price = excluded.exit_price,
            pnl = excluded.pnl,
            pnl_pct = excluded.pnl_pct,
            status = excluded.status,
            strategy_tag = excluded.strategy_tag,
            notes = excluded.notes,
            emotion = excluded.emotion,
            screenshot_url = excluded.screenshot_url,
            updated_at = excluded.updated_at
        """, (
            trade_id,
            entry.get("user_id", "usr_owner_01"),
            entry.get("symbol", "BTC/USDT"),
            entry.get("direction", "LONG"),
            float(entry.get("entry_price", 0.0)),
            float(entry.get("exit_price", 0.0)),
            float(entry.get("pnl", 0.0)),
            float(entry.get("pnl_pct", 0.0)),
            entry.get("status", "CLOSED"),
            entry.get("strategy_tag", "SMC OrderBlock"),
            entry.get("notes", ""),
            entry.get("emotion", "Disciplined"),
            entry.get("screenshot_url", ""),
            entry.get("created_at", now),
            now
        ))
        conn.commit()
        conn.close()
        return entry

    @staticmethod
    def delete(trade_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trade_journal WHERE id = ?", (trade_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    @staticmethod
    def clear_all(user_id: str = "usr_owner_01") -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trade_journal WHERE user_id = ?", (user_id,))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count
