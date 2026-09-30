import sqlite3
import os

db_path = os.path.expanduser("~/apex_copytrade/backend/data/apex_production.db")
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "data", "apex_production.db")

print("DB Path:", db_path)
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [r[0] for r in c.fetchall()])
c.execute("SELECT COUNT(*) FROM bf_system_logs")
print("Total system logs:", c.fetchone()[0])
c.execute("SELECT level, message, timestamp FROM bf_system_logs ORDER BY id DESC LIMIT 20")
for r in c.fetchall():
    print(f"[{r[2]}] [{r[0]}] {r[1]}")

c.execute("SELECT COUNT(*) FROM bf_trades")
print("Total trades in bf_trades:", c.fetchone()[0])
