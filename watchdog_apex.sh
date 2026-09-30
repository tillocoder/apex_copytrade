#!/data/data/com.termux/files/usr/bin/bash
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export PATH=$PREFIX/bin:$PATH

termux-wake-lock 2>/dev/null || true

FAIL_COUNT_LOCAL=0
FAIL_COUNT_PUBLIC=0

while true; do
    pgrep -x "sshd" >/dev/null || sshd 2>/dev/null || true

    # 1. Check APEX local backend (port 8000)
    LOCAL_HEALTH=$(curl -s -m 3 http://127.0.0.1:8000/api/v1/system/health 2>/dev/null || echo "")
    if [[ "$LOCAL_HEALTH" != *"HEALTHY"* ]]; then
        FAIL_COUNT_LOCAL=$((FAIL_COUNT_LOCAL+1))
        echo "[WATCHDOG $(date)] Local backend unresponsive (Fail $FAIL_COUNT_LOCAL/2)..." >> /data/data/com.termux/files/home/watchdog.log
        if [ $FAIL_COUNT_LOCAL -ge 2 ]; then
            echo "[WATCHDOG $(date)] Restarting Python Backend..." >> /data/data/com.termux/files/home/watchdog.log
            pkill -9 -f "backend/main.py" || true
            sleep 1
            cd /data/data/com.termux/files/home/apex_copytrade
            nohup python3 -u backend/main.py > /data/data/com.termux/files/home/backend.log 2>&1 &
            FAIL_COUNT_LOCAL=0
            sleep 5
        fi
    else
        FAIL_COUNT_LOCAL=0
    fi

    # 2. Check Apex Speed 3D Racing Game Server (port 5050)
    GAME_HEALTH=$(curl -s -m 3 http://127.0.0.1:5050/health 2>/dev/null || echo "")
    if [[ "$GAME_HEALTH" != *"apex-speed-3d"* ]]; then
        echo "[WATCHDOG $(date)] Racing Game Server down. Restarting..." >> /data/data/com.termux/files/home/watchdog.log
        pkill -f "termux-racing-game/server.js" || true
        sleep 1
        cd /data/data/com.termux/files/home/termux-racing-game
        nohup node server.js > /data/data/com.termux/files/home/racing.log 2>&1 &
        sleep 2
    fi

    # 3. Check Cloudflare Tunnel (Tunnel connection to Cloudflare edge)
    CF_RUNNING=$(pgrep -f "cloudflared" || true)
    PUBLIC_HEALTH=$(curl -s -m 5 https://apex.xrinvest.uz/api/v1/system/health 2>/dev/null || echo "")

    if [[ -z "$CF_RUNNING" ]] || [[ "$PUBLIC_HEALTH" != *"HEALTHY"* ]]; then
        FAIL_COUNT_PUBLIC=$((FAIL_COUNT_PUBLIC+1))
        echo "[WATCHDOG $(date)] Cloudflare Tunnel down or unresponsive (Fail $FAIL_COUNT_PUBLIC/2)..." >> /data/data/com.termux/files/home/watchdog.log
        if [ $FAIL_COUNT_PUBLIC -ge 2 ]; then
            echo "[WATCHDOG $(date)] Restarting Cloudflare Tunnel with DNS resolver bindings..." >> /data/data/com.termux/files/home/watchdog.log
            pkill -9 -f "cloudflared" || true
            sleep 1
            $HOME/start_cf.sh > /dev/null 2>&1 || true
            FAIL_COUNT_PUBLIC=0
            sleep 5
        fi
    else
        FAIL_COUNT_PUBLIC=0
    fi

    sleep 15
done
