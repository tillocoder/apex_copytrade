#!/usr/bin/env bash
# ==============================================================================
# SERVER VA SSH XAVFSIZLIGINI MAKSIMAL DARAJADA KUCHAYTIRISH SKRIPTI
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}   Termux / Linux Server Xavfsizlik Skripti          ${NC}"
echo -e "${GREEN}====================================================${NC}"

# 1. SSH Public Key Tekshiruvi
SSH_AUTH_KEYS="$HOME/.ssh/authorized_keys"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [ ! -f "$SSH_AUTH_KEYS" ] || [ ! -s "$SSH_AUTH_KEYS" ]; then
    echo -e "${YELLOW}[!] DIQQAT: ~/.ssh/authorized_keys fayli bo'sh yoki mavjud emas!${NC}"
    if [ -f "$HOME/.ssh/id_ed25519.pub" ]; then
        echo -e "${GREEN}[+] O'zingizning public kalitingiz (~/.ssh/id_ed25519.pub) authorized_keys ga qo'shilmoqda...${NC}"
        cat "$HOME/.ssh/id_ed25519.pub" >> "$SSH_AUTH_KEYS"
        chmod 600 "$SSH_AUTH_KEYS"
    else
        echo -e "${RED}[X] PAROL ORQALI KIRISHNI O'CHIRISH UCHUN KAMIDA BITTA SSH PUBLIC KEY NEEDED!${NC}"
        echo -e "${YELLOW}Iltimos, telefon yoki kompyuteringiz SSH public kalitini ~/.ssh/authorized_keys fayliga joylang.${NC}"
        echo -e "Buyruq: cat id_ed25519.pub >> ~/.ssh/authorized_keys"
    fi
fi

# 2. Muhitni aniqlash (Termux yoki Standart Linux)
IS_TERMUX=false
if [ -n "$PREFIX" ] || command -v pkg &>/dev/null; then
    IS_TERMUX=true
    echo -e "${GREEN}[+] Muhit: Termux aniqlandi.${NC}"
else
    echo -e "${GREEN}[+] Muhit: Linux (Ubuntu/Debian) aniqlandi.${NC}"
fi

# 3. Paketlarni o'rnatish
if [ "$IS_TERMUX" = true ]; then
    echo -e "${GREEN}[+] Termux paketlari yangilanmoqda...${NC}"
    pkg update -y && pkg upgrade -y
    pkg install -y openssh fail2ban
    SSHD_CONFIG_FILE="$PREFIX/etc/ssh/sshd_config"
else
    echo -e "${GREEN}[+] Linux paketlari o'rnatilmoqda (sudo kerak bo'ladi)...${NC}"
    sudo apt-get update
    sudo apt-get install -y openssh-server fail2ban ufw
    SSHD_CONFIG_FILE="/etc/ssh/sshd_config"
fi

# 4. SSH Hardening Sozlamalarini qo'llash
echo -e "${GREEN}[+] SSH konfiguratsiyasi xavfsizlantirilmoqda...${NC}"

# Zaxira nusxa olish
if [ "$IS_TERMUX" = false ]; then
    sudo cp "$SSHD_CONFIG_FILE" "${SSHD_CONFIG_FILE}.bak.$(date +%s)"
fi

# SSH Config sozlamalari:
SECURE_CONF="/tmp/sshd_security_append.conf"
cat << 'EOF' > "$SECURE_CONF"

# --- SECURITY HARDENING SETTINGS ---
Port 22222
PermitRootLogin no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowAgentForwarding no
EOF

if [ -s "$SSH_AUTH_KEYS" ]; then
    echo "PasswordAuthentication no" >> "$SECURE_CONF"
    echo "KbdInteractiveAuthentication no" >> "$SECURE_CONF"
    echo -e "${GREEN}[+] Parol orqali kirish taqiqlandi (faqat SSH Key ishlaydi).${NC}"
else
    echo -e "${YELLOW}[!] Authorized keys bo'sh bo'lgani uchun Parol orqali kirish vaqtincha yoqiq qoldirildi.${NC}"
fi

if [ "$IS_TERMUX" = false ]; then
    sudo mkdir -p /etc/ssh/sshd_config.d/
    sudo cp "$SECURE_CONF" /etc/ssh/sshd_config.d/99-security.conf
    sudo sshd -t && sudo systemctl restart ssh || sudo systemctl restart sshd
else
    cat "$SECURE_CONF" >> "$SSHD_CONFIG_FILE"
    pkill sshd || true
    sshd
fi

# 5. Fail2ban sozlash (Linux uchun)
if [ "$IS_TERMUX" = false ]; then
    echo -e "${GREEN}[+] Fail2ban (Avtomatik IP Bloklash) sozlanmoqda...${NC}"
    sudo cat << 'EOF' | sudo tee /etc/fail2ban/jail.local > /dev/null
[DEFAULT]
bantime = 86400
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 22222,22
logpath = %(sshd_log)s
backend = %(sshd_backend)s
EOF

    sudo systemctl enable fail2ban
    sudo systemctl restart fail2ban
fi

# 6. Firewall (UFW) Sozlash
if [ "$IS_TERMUX" = false ]; then
    echo -e "${GREEN}[+] UFW Firewall sozlanmoqda...${NC}"
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow 22222/tcp comment 'SSH Secure Port'
    sudo ufw limit 22222/tcp comment 'SSH Rate Limit'
    echo "y" | sudo ufw enable
    sudo ufw status verbose
fi

echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN} [✓] SERVER XAVFSIZLIGI DARAJASI MAKSIMAL KUCHAYTIRILDI! ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "${YELLOW}ESLATMA:${NC}"
echo -e "1. SSH porti ${GREEN}22222${NC} ga o'zgardi."
echo -e "2. Endi SSH orqali ulanish uchun: ${GREEN}ssh -p 22222 $USER@<IP-ADDRESS>${NC}"
echo -e "3. Fail2ban statusini ko'rish: ${GREEN}sudo fail2ban-client status sshd${NC}"
