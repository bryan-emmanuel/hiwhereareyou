#!/bin/bash
# hiwhereareyou Worker Node Setup Utility - For Operator use on MacBook/Maintenance Machine
# This script automates the onboarding of Android nodes by pushing and executing the onboarding script.

set -e

# Load NODE_ID from command line
SERIAL=$1

if [ -z "$SERIAL" ]; then
    echo "Usage: ./setup_worker.sh <adb_serial>"
    echo "Connected devices:"
    adb devices
    exit 1
fi

echo "--- Starting Automated Node Setup for $SERIAL ---"

# 1. Ensure Device Connectivity
adb -s "$SERIAL" get-state > /dev/null 2>&1 || { echo "Error: Device $SERIAL not found or unauthorized."; exit 1; }

# 2. Grant Permissions (Pre-emptive)
echo "Granting Termux permissions via ADB..."
adb -s "$SERIAL" shell pm grant com.termux android.permission.WRITE_EXTERNAL_STORAGE || echo "Warning: Could not grant WRITE_EXTERNAL_STORAGE"
adb -s "$SERIAL" shell pm grant com.termux android.permission.READ_EXTERNAL_STORAGE || echo "Warning: Could not grant READ_EXTERNAL_STORAGE"

# 3. Wake and Unlock
echo "Waking device and ensuring Termux is in focus..."
adb -s "$SERIAL" shell input keyevent 224 # Wake
adb -s "$SERIAL" shell input keyevent 82  # Unlock (if possible)
adb -s "$SERIAL" shell am start -n com.termux/.app.TermuxActivity
sleep 3

# 4. Push Local Source and Onboarding Script
echo "Deploying local source code and onboarding script..."
# Package project excluding .git and virtual environments to avoid symlink issues on /sdcard
tar --exclude='./.git' --exclude='./.venv' --exclude='./__pycache__' --exclude='./.pytest_cache' -czf hiwhereareyou_source.tar.gz .
adb -s "$SERIAL" push hiwhereareyou_source.tar.gz /sdcard/Download/hiwhereareyou_source.tar.gz
rm hiwhereareyou_source.tar.gz
adb -s "$SERIAL" push scripts/onboarding.sh /sdcard/Download/onboarding.sh

# 5. Execute Onboarding
echo "Executing onboarding script in Termux..."
echo "This will run in the background. You can check the log at /sdcard/Download/hiwhereareyou_onboarding.log"

# Attempt to execute using run-as (requires debuggable/rooted or proper Termux configuration)
adb -s "$SERIAL" shell "run-as com.termux bash -c 'cp /sdcard/Download/onboarding.sh ~/onboarding.sh && bash ~/onboarding.sh'" || {
    echo "Warning: run-as failed. You may need to manually execute 'bash /sdcard/Download/onboarding.sh' inside Termux."
}

echo "--- Setup Command Sent Successfully ---"
