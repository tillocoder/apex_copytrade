#!/data/data/com.termux/files/usr/bin/bash
pkill -9 -f cloudflared || true
sleep 1
nohup termux-chroot "/data/data/com.termux/files/home/cloudflared tunnel --config /data/data/com.termux/files/home/.cloudflared/config.yml run 6c07f140-d72a-41b8-b09c-c20353428851" > /data/data/com.termux/files/home/cloudflared.log 2>&1 &
echo "[+] Cloudflared restarted"
