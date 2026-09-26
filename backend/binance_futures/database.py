import sqlite3
import os
import json
import time
from typing import Dict, Any, List, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "apex_production.db")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_futures_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Trades table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bf_trades (
        id TEXT PRIMARY KEY,
        client_order_id TEXT UNIQUE,
        mode TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL,
        qty REAL NOT NULL,
        margin REAL NOT NULL,
        leverage INTEGER NOT NULL,
        sl REAL,
        tp REAL,
        pnl REAL DEFAULT 0.0,
        roi_pct REAL DEFAULT 0.0,
        fee REAL DEFAULT 0.0,
        status TEXT NOT NULL,
        close_reason TEXT,
        opened_at TEXT NOT NULL,
        closed_at TEXT,
        signal_snapshot TEXT
    );
    """)

    # 2. Orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bf_orders (
        id TEXT PRIMARY KEY,
        client_order_id TEXT UNIQUE,
        binance_order_id INTEGER,
        mode TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        type TEXT NOT NULL,
        price REAL,
        qty REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 3. Session state table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bf_session_state (
        session_key TEXT PRIMARY KEY,
        mode TEXT NOT NULL,
        session_pnl REAL DEFAULT 0.0,
        trades_count INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        target_reached INTEGER DEFAULT 0,
        updated_at TEXT NOT NULL
    );
    """)

    # 4. System logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bf_system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def log_system_event(level: str, message: str):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO bf_system_logs (level, message, timestamp) VALUES (?, ?, ?)",
                     (level, message, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[BF_DB_ERROR] Failed to log event: {e}")

def save_trade(trade_data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO bf_trades (
        id, client_order_id, mode, symbol, side, entry_price, exit_price,
        qty, margin, leverage, sl, tp, pnl, roi_pct, fee, status,
        close_reason, opened_at, closed_at, signal_snapshot
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade_data["id"],
        trade_data.get("client_order_id", trade_data["id"]),
        trade_data.get("mode", "PAPER"),
        trade_data.get("symbol", "ETHUSDT"),
        trade_data["side"],
        trade_data["entry_price"],
        trade_data.get("exit_price"),
        trade_data["qty"],
        trade_data.get("margin", 0.50),
        trade_data.get("leverage", 100),
        trade_data.get("sl"),
        trade_data.get("tp"),
        trade_data.get("pnl", 0.0),
        trade_data.get("roi_pct", 0.0),
        trade_data.get("fee", 0.0),
        trade_data["status"],
        trade_data.get("close_reason"),
        trade_data["opened_at"],
        trade_data.get("closed_at"),
        json.dumps(trade_data.get("signal_snapshot", {})) if isinstance(trade_data.get("signal_snapshot"), dict) else trade_data.get("signal_snapshot")
    ))
    conn.commit()
    conn.close()

def get_trades(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bf_trades ORDER BY opened_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    trades = [dict(r) for r in rows]
    conn.close()
    return trades

def get_session_stats(session_key: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bf_session_state WHERE session_key = ?", (session_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "session_key": session_key,
        "mode": "PAPER",
        "session_pnl": 0.0,
        "trades_count": 0,
        "wins": 0,
        "losses": 0,
        "target_reached": 0
    }

def update_session_stats(session_key: str, pnl_delta: float, is_win: bool, target_reached: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bf_session_state WHERE session_key = ?", (session_key,))
    row = cursor.fetchone()
    now_str = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    if row:
        new_pnl = row["session_pnl"] + pnl_delta
        new_trades = row["trades_count"] + 1
        new_wins = row["wins"] + (1 if is_win else 0)
        new_losses = row["losses"] + (0 if is_win else 1)
        new_target = 1 if (target_reached or new_pnl >= 2.0) else row["target_reached"]
        cursor.execute("""
        UPDATE bf_session_state SET
            session_pnl = ?, trades_count = ?, wins = ?, losses = ?,
            target_reached = ?, updated_at = ?
        WHERE session_key = ?
        """, (new_pnl, new_trades, new_wins, new_losses, new_target, now_str, session_key))
    else:
        cursor.execute("""
        INSERT INTO bf_session_state (session_key, mode, session_pnl, trades_count, wins, losses, target_reached, updated_at)
        VALUES (?, 'PAPER', ?, 1, ?, ?, ?, ?)
        """, (session_key, pnl_delta, 1 if is_win else 0, 0 if is_win else 1, 1 if pnl_delta >= 2.0 else 0, now_str))
    conn.commit()
    conn.close()
