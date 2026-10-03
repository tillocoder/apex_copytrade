---
name: termux-ssh-sync
description: Connects, synchronizes code, and manages the APEX QUANT live/paper trading engine on Android Termux via SSH.
---

# Termux SSH Automation & Sync Skill

This skill documents and automates connecting directly to the user's Android Termux trading server over local Wi-Fi / SSH.

## Connection Profile
- **Host / IP**: `192.168.1.136`
- **Port**: `8022`
- **Authentication**: Key-based (`C:\Users\tillo\.ssh\id_ed25519`)
- **Remote Project Directory**: `/data/data/com.termux/files/home/apex_copytrade`
- **Remote User**: `u0_a114` (Termux default)

## Standard Execution Commands

### 1. Test SSH Connection
```powershell
ssh -p 8022 -o StrictHostKeyChecking=no 192.168.1.136 "uname -a"
```

### 2. Fast File Synchronization (PC -> Termux)
```powershell
# Copy modified python modules
scp -P 8022 -o StrictHostKeyChecking=no backend/binance_futures/*.py 192.168.1.136:~/apex_copytrade/backend/binance_futures/
scp -P 8022 -o StrictHostKeyChecking=no scripts/*.py scripts/*.sh 192.168.1.136:~/apex_copytrade/scripts/
```

### 3. Reset 24-Hour Paper Test to Zero
```powershell
ssh -p 8022 -o StrictHostKeyChecking=no 192.168.1.136 "cd ~/apex_copytrade && bash scripts/reset_and_start_24h_test.sh"
```

### 4. Restart Backend Daemon (with Wake Lock & Turbo Sockets)
```powershell
ssh -p 8022 -o StrictHostKeyChecking=no 192.168.1.136 "cd ~/apex_copytrade && bash scripts/start_termux_turbo.sh"
```

### 5. Inspect Real-Time Endpoints
```powershell
# Check unified state
ssh -p 8022 -o StrictHostKeyChecking=no 192.168.1.136 "curl -s http://127.0.0.1:8000/api/v1/futures/state"

# Check 24h soak test telemetry
ssh -p 8022 -o StrictHostKeyChecking=no 192.168.1.136 "curl -s http://127.0.0.1:8000/api/v1/futures/soak-test"

# Check paper trades
ssh -p 8022 -o StrictHostKeyChecking=no 192.168.1.136 "curl -s http://127.0.0.1:8000/api/v1/futures/paper-trades"
```
