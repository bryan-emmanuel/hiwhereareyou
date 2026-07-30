#!/bin/bash
# hiwhereareyou System Starter

# Ensure we're in the project directory
cd "$(dirname "$0")"

# 1. Initialize environment based on platform
if [ -d "/data/data/com.termux" ]; then
    echo "Platform detected: Termux"
    export PREFIX="/data/data/com.termux/files/usr"
    export HOME="/data/data/com.termux/files/home"
    export PATH="$PREFIX/bin:$PATH"
    export LD_LIBRARY_PATH="$PREFIX/lib"
    export TMPDIR="$PREFIX/tmp"
    export PYTHONPATH="$HOME/hiwhereareyou"
    
    # Prepend clean bin path to fix slop
    export PATH="/data/data/com.termux/files/usr/bin:$PATH"

    if [ -f /data/data/com.termux/files/usr/etc/profile ]; then
        . /data/data/com.termux/files/usr/etc/profile
    fi

    # 1.1 Node Synchronization
    echo "Checking for updates..."
    # Extract VCS_PAT if available
    if [ -f .env ]; then
        VCS_PAT_VAL=$(grep "^VCS_PAT=" .env | cut -d'=' -f2)
        if [ -n "$VCS_PAT_VAL" ]; then
            git remote set-url origin "https://x-access-token:$VCS_PAT_VAL@github.com/bryan-emmanuel/hiwhereareyou.git"
        fi
    fi
    git pull origin main || echo "Warning: git pull failed. Starting with current version."
else
    echo "Platform detected: Darwin/Linux"
    export PYTHONPATH="$(pwd)"
fi

# 2. Kill any existing hiwhereareyou process
pkill -f "src/main.py" || true

# 3. Acquire wake lock (prevents Android from killing the process)
# Check if termux-wake-lock is available
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
fi

# 4. Start the app in the background with unbuffered logging
# We use the full path to the venv python to ensure it starts correctly
nohup ./venv/bin/python -u src/main.py > scheduler.log 2>&1 &

# 5. Report status
echo "------------------------------------------------"
echo "hiwhereareyou started in the background."
echo "PID: $!"
echo "Log: scheduler.log"
echo "------------------------------------------------"
echo "To monitor logs: tail -f scheduler.log"
echo "To check status: ./status.sh"
