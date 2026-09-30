#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# APEX SPEED 3D - Quick Start Script for Termux
# ========================================================

# Check if port is already defined, otherwise default to 5050
export PORT=${PORT:-5050}
export HOST=${HOST:-0.0.0.0}

echo "🏁 Starting Apex Speed 3D Racing Server on port $PORT..."
node server.js
