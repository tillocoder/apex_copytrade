#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# APEX QUANT v3.3: ANDROID & TERMUX TURBO HARDWARE ACCELERATION LAUNCHER
# ==============================================================================
# Unlocks maximum Android performance, CPU wake locks, and network socket limits.

echo "================================================================================"
echo "⚡ UNLOCKING MAXIMUM ANDROID & TERMUX HARDWARE POWER FOR APEX QUANT"
echo "================================================================================"

# 1. Acquire Android Wake Lock (prevents CPU core throttling and sleep)
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo "✅ [CPU_LOCK] termux-wake-lock ACQUIRED (Android sleep & throttling disabled)"
fi

# 2. Maximize File Descriptors / Open Sockets (Soft -> Hard Limit: 4096)
HARD_LIMIT=$(ulimit -Hn 2>/dev/null || echo 4096)
ulimit -n "$HARD_LIMIT" 2>/dev/null || ulimit -n 4096
CURRENT_LIMIT=$(ulimit -n)
echo "✅ [SOCKET_LIMIT] ulimit -n set to $CURRENT_LIMIT (Max concurrent sockets unlocked)"

# 3. CPU Core Telemetry
ONLINE_CPUS=$(cat /sys/devices/system/cpu/online 2>/dev/null || echo "Unknown")
echo "✅ [CPU_CORES] Active online cores: $ONLINE_CPUS"

# 4. Terminate previous backend instance cleanly (without killing soak test daemon!)
PID_MAIN=$(pgrep -f "backend/main.py" || true)
if [ -n "$PID_MAIN" ]; then
    echo "Stopping existing backend PID(s): $PID_MAIN"
    kill $PID_MAIN 2>/dev/null || true
    sleep 2
fi

# 5. Launch Backend with Turbo Flags
cd "$(dirname "$0")/.." || exit 1
export PYTHONOPTIMIZE=1
export PYTHONUNBUFFERED=1

echo "🚀 Starting APEX QUANT Turbo Engine (Uvicorn 4000 sockets / GZip / No-Disk-Lag)..."
nohup python3 -u backend/main.py > backend.log 2>&1 &
NEW_PID=$!
echo "✅ Backend started with PID $NEW_PID"

sleep 2
if ps -p "$NEW_PID" > /dev/null; then
    echo "================================================================================"
    echo "🎉 TURBO ENGINE IS LIVE & HEALTHY ON PID $NEW_PID!"
    echo "================================================================================"
else
    echo "❌ Failed to start. Checking backend.log:"
    tail -n 20 backend.log
fi
