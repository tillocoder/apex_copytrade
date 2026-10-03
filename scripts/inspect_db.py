import sqlite3
import json

conn = sqlite3.connect('backend/data/apex_production.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT id, side, entry_price, exit_price, qty, margin, pnl, status, opened_at, close_reason FROM bf_trades ORDER BY opened_at DESC')
rows = cursor.fetchall()
print(f"Total trades in db: {len(rows)}")
for r in rows:
    print(dict(r))

cursor.execute('SELECT * FROM bf_session_state')
print("Session state:", [dict(r) for r in cursor.fetchall()])
