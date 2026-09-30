#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# APEX QUANT v3.3: 24-HOUR SOAK TEST FULL RESET TO 0
# ==============================================================================
set -e

echo "================================================================================"
echo "🔄 RESETTING APEX QUANT v3.3 24-HOUR PAPER TEST TO ZERO"
echo "================================================================================"

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

# 1. Kill old soak test daemon
echo "1. Stopping existing soak test daemon..."
pkill -f "run_24h_soak_test.py" 2>/dev/null || true
sleep 1

# 2. Reset database paper trades and session state
echo "2. Resetting database paper records..."
python3 -c "
import sqlite3, os
db_path = 'backend/data/apex_production.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('DELETE FROM bf_trades WHERE mode=\"PAPER\"')
        conn.execute('DELETE FROM bf_session_state')
        conn.commit()
        print('✅ Database reset successfully.')
    except Exception as e:
        print('Database reset note:', e)
    finally:
        conn.close()
"

# 3. Clean logs
echo "3. Resetting 24h logs..."
rm -f backend/logs/soak_test_24h.log backend/logs/soak_test.stdout.log
mkdir -p backend/logs backend/data

# 4. Restart Turbo Backend cleanly
echo "4. Restarting Turbo Engine..."
bash scripts/start_termux_turbo.sh

sleep 3

# 5. Launch fresh 24h soak test daemon
echo "5. Launching fresh 24h soak test daemon..."
nohup python3 -u scripts/run_24h_soak_test.py > backend/logs/soak_test.stdout.log 2>&1 &
SOAK_PID=$!
echo "✅ Soak test started with PID: $SOAK_PID"

sleep 3

# 6. Verify Telemetry Output
echo "6. Verifying live telemetry..."
if [ -f "backend/data/soak_test_24h_telemetry.json" ]; then
    python3 -c "
import json
with open('backend/data/soak_test_24h_telemetry.json') as f:
    d = json.load(f)
print(f'✅ Telemetry initialized: Status={d.get(\"status\")} | Progress={d.get(\"progressPct\")}% | Bars={d.get(\"barsScanned\")}/1440 | Elapsed={d.get(\"elapsedHours\")}h')
"
else
    echo "⚠️ Waiting for telemetry file..."
fi

echo "================================================================================"
echo "🎉 24-HOUR PAPER TEST HAS BEEN RESET TO 0 AND IS NOW LIVE!"
echo "================================================================================"
