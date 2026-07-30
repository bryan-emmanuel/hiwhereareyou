#!/usr/bin/env python3
"""
Notification service for the hiwhereareyou System.
Optimized for Telegram Bot communication for AI Agent escalation.
"""

import os
import sys
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Ensure fallback to other possible config sources or defaults
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_CHANNEL_ID = os.environ.get("TELEGRAM_ADMIN_CHANNEL_ID")
# Standard Telegram Bot API base URL
NOTIFY_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" if TELEGRAM_BOT_TOKEN else None

def send_notification(title, message, priority="default"):
    """
    Sends a notification to the admin via Telegram.
    """
    if not NOTIFY_API_URL or not TELEGRAM_ADMIN_CHANNEL_ID:
        print(f"NOTIFICATION [MOCKED]: {title} - {message}", file=sys.stderr)
        return False

    # Format message for Telegram
    formatted_message = f"<b>{title}</b>\n\n{message}"
    
    if priority == "high":
        formatted_message = f"🚨 <b>{title.upper()}</b> 🚨\n\n{message}"

    payload = {
        "chat_id": TELEGRAM_ADMIN_CHANNEL_ID,
        "text": formatted_message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(NOTIFY_API_URL, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Telegram API Error: {response.status_code} - {response.text}", file=sys.stderr)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Telegram notification: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/notify.py \"Title\" \"Message\" [priority]", file=sys.stderr)
        sys.exit(1)
    
    title = sys.argv[1]
    msg = sys.argv[2]
    pri = sys.argv[3] if len(sys.argv) > 3 else "default"
    
    if send_notification(title, msg, pri):
        sys.exit(0)
    else:
        sys.exit(1)
