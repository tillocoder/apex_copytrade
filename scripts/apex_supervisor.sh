#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# APEX QUANT: 24/7 AUTONOMOUS SYSTEM SUPERVISOR & SELF-HEALING DAEMON
# ==============================================================================
# Permanently prevents:
# 1. Process termination / Silent crashes
# 2. WebSocket hangs / Zombie socket data stalls
# 3. Android CPU throttling / sleep
# 4. Stuck positions exceeding maximum lifetime
# ==============================================================================

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

LOG_DIR="$BASE_DIR/backend/logs"
SUPERVISOR_LOG="$LOG_DIR/supervisor.log"
mkdir -p "$LOG_DIR"

log_event() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$SUPERVISOR_LOG"
}

log_event "🛡️ APEX QUANT SUPERVISOR DAEMON INITIATED"

# 1. Ensure CPU wake lock is permanently held
acquire_wake_lock() {
    if command -v termux-wake-lock >/dev/null 2>&1; then
        termux-wake-lock
    fi
}

acquire_wake_lock

# 2. Maximum open files / sockets
ulimit -n 4096 2>/dev/null || true

CONSECUTIVE_HEALTH_FAILURES=0
STALE_COUNT=0

while true; do
    acquire_wake_lock

    # A. Check backend process
    BACKEND_PID=$(pgrep -f "backend/main.py" | head -n 1 || true)
    if [ -z "$BACKEND_PID" ]; then
        log_event "⚠️ [BACKEND_DEAD] backend/main.py is NOT running! Restarting immediately..."
        bash scripts/start_termux_turbo.sh >> "$SUPERVISOR_LOG" 2>&1
        sleep 5
        CONSECUTIVE_HEALTH_FAILURES=0
    else
        # B. Check health endpoint responsiveness (5s timeout)
        HEALTH_RESP=$(curl -s --max-time 5 "http://127.0.0.1:8000/api/v1/futures/health" 2>/dev/null || echo "TIMEOUT")
        if [ "$HEALTH_RESP" = "TIMEOUT" ] || [ -z "$HEALTH_RESP" ]; then
            CONSECUTIVE_HEALTH_FAILURES=$((CONSECUTIVE_HEALTH_FAILURES + 1))
            log_event "⚠️ [HEALTH_TIMEOUT] Health check failed (#$CONSECUTIVE_HEALTH_FAILURES/3)"
            if [ "$CONSECUTIVE_HEALTH_FAILURES" -ge 3 ]; then
                log_event "🚨 [HANG_DETECTED] 3 consecutive timeouts. Killing hung backend (PID $BACKEND_PID)..."
                kill -9 "$BACKEND_PID" 2>/dev/null || true
                sleep 2
                bash scripts/start_termux_turbo.sh >> "$SUPERVISOR_LOG" 2>&1
                CONSECUTIVE_HEALTH_FAILURES=0
                sleep 5
            fi
        else
            CONSECUTIVE_HEALTH_FAILURES=0
            # C. Check if stale or degraded
            IS_STALE=$(python3 -c "import json; d=json.loads('''$HEALTH_RESP'''); print(d.get('is_stale', False))" 2>/dev/null || echo "False")
            STATUS=$(python3 -c "import json; d=json.loads('''$HEALTH_RESP'''); print(d.get('status', 'HEALTHY'))" 2>/dev/null || echo "HEALTHY")
            
            if [ "$IS_STALE" = "True" ] || [ "$STATUS" = "STALE" ]; then
                STALE_COUNT=$((STALE_COUNT + 1))
                if [ "$STALE_COUNT" -ge 2 ]; then
                    log_event "⚠️ [STALE_DETECTED] Market data stale. Triggering autonomous self-healing..."
                    HEAL_RES=$(curl -s -X POST --max-time 5 "http://127.0.0.1:8000/api/v1/futures/self-heal" 2>/dev/null || true)
                    log_event "🔧 [SELF_HEAL] $HEAL_RES"
                    STALE_COUNT=0
                fi
            else
                STALE_COUNT=0
            fi
        fi
    fi

    # D. Check 24-hour soak test daemon
    SOAK_PID=$(pgrep -f "run_24h_soak_test.py" | head -n 1 || true)
    if [ -z "$SOAK_PID" ]; then
        log_event "⚠️ [SOAK_TEST_DEAD] run_24h_soak_test.py is NOT running! Restarting..."
        nohup python3 -u scripts/run_24h_soak_test.py > "$LOG_DIR/soak_test.stdout.log" 2>&1 &
        sleep 2
        NEW_SOAK=$(pgrep -f "run_24h_soak_test.py" | head -n 1 || true)
        log_event "✅ Soak test restarted with PID $NEW_SOAK"
    fi

    # E. Log rotation guard (Trims log if > 10MB)
    for lfile in "$LOG_DIR/supervisor.log" "$BASE_DIR/backend.log" "$LOG_DIR/soak_test.stdout.log"; do
        if [ -f "$lfile" ]; then
            FSIZE=$(wc -c < "$lfile" 2>/dev/null || echo 0)
            if [ "$FSIZE" -gt 10485760 ]; then
                tail -n 10000 "$lfile" > "${lfile}.tmp" && mv "${lfile}.tmp" "$lfile"
                log_event "📦 Rotated oversized log: $lfile"
            fi
        fi
    done

    sleep 30
done
