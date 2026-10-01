import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "data", "apex_production.db")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
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
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bf_session_state (
        session_key TEXT PRIMARY KEY,
        mode TEXT NOT NULL,
        session_pnl REAL DEFAULT 0.0,
        trades_count INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        target_reached INTEGER DEFAULT 0,
        updated_at TEXT NOT NULL
    )
    """)
    conn.execute("DELETE FROM bf_trades WHERE mode = 'PAPER'")
    conn.execute("DELETE FROM bf_session_state")
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM bf_trades").fetchone()[0]
    conn.close()
    print(f"[OK] Database cleaned. Current paper trades count: {count}")
