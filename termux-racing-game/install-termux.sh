#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# APEX SPEED 3D - 1-Click Installer for Termux
# ========================================================

echo "🏎️ APEX SPEED 3D - Termux Setup"
echo "-----------------------------------"

# Update package manager & install Node.js if missing
if ! command -v node &> /dev/null; then
    echo "📦 Node.js o'rnatilmoqda..."
    pkg update -y && pkg install nodejs-lts -y
else
    echo "✅ Node.js mavjud: $(node -v)"
fi

# Install dependencies (only ws, takes ~2 seconds)
echo "📦 Bog'liqliklar o'rnatilmoqda..."
npm install --omit=dev

# Make start script executable
chmod +x start.sh

echo ""
echo "🎉 O'rnatish muvaffaqiyatli yakunlandi!"
echo "Ishga tushirish uchun:"
echo "  ./start.sh"
echo ""
echo "Yoki PM2 orqali orqa fonda (background) ishlatish uchun:"
echo "  npm install -g pm2"
echo "  pm2 start ecosystem.config.js"
echo "  pm2 save"
echo "-----------------------------------"
