#!/data/data/com.termux/files/usr/bin/bash
# hiwhereareyou Status Check

cd "$(dirname "$0")"

if pgrep -f "src/main.py" > /dev/null; then
    echo "✅ hiwhereareyou is RUNNING."
    tail -n 5 scheduler.log
else
    echo "❌ hiwhereareyou is NOT running."
fi
