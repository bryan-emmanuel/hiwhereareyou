# SKILL.md — ADB Infrastructure Administration

## Purpose

Enables the Operator to perform administrative tasks on remote Android devices using the Android Debug Bridge (ADB). This is essential for managing the Termux environment, updating code, and troubleshooting the `hiwhereareyou` autonomous system.

## Prerequisites

- `adb` (Android Debug Bridge) installed on the local machine.
- Developer Options and USB Debugging enabled on the remote device.
- Device authorized via the "Allow USB Debugging" prompt.

## Command Reference

### Basic Device Connectivity

    # List connected devices
    adb devices -l

    # Restart ADB server if device is not found
    adb kill-server && adb start-server

### Termux File System Access (Critical)

Because Termux files are private to the app, you MUST use `run-as com.termux` to interact with them.

    # Read a file (e.g., logs)
    adb shell "run-as com.termux cat /data/data/com.termux/files/home/hiwhereareyou/scheduler.log"

    # List project directory
    adb shell "run-as com.termux ls -la /data/data/com.termux/files/home/hiwhereareyou"

### Synchronization & Deployment

    # Push a file to the SD card first (cannot push directly to private app space)
    adb push local_file.py /sdcard/Download/

    # Move file from SD card to Termux home
    adb shell "run-as com.termux cp /sdcard/Download/local_file.py /data/data/com.termux/files/home/hiwhereareyou/"

    # Force a Git Pull/Reset on the remote device
    adb shell "run-as com.termux /data/data/com.termux/files/usr/bin/bash -c 'cd ~/hiwhereareyou && git fetch origin main && git reset --hard origin/main'"

### App Lifecycle Management

    # Start the app using the management script
    adb shell "run-as com.termux sh /data/data/com.termux/files/home/hiwhereareyou/start.sh"

    # Check app status
    adb shell "run-as com.termux sh /data/data/com.termux/files/home/hiwhereareyou/status.sh"

## Troubleshooting Patterns

### "Permission Denied" on Cat/CP
If `run-as com.termux` fails, ensure the Termux app is actually installed and that you are using the correct package name (`com.termux`).

### Environment Discrepancies
Always use absolute paths for Termux binaries (`/data/data/com.termux/files/usr/bin/...`) when executing commands via ADB shell to ensure dependencies like `node` or `python` are found.

### ADB Unauthorized
If the device shows as `unauthorized`, toggle USB Debugging OFF and ON in Developer Options and re-accept the prompt.
