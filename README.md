# 📱 Telegram & Twilio Scavenger Hunt Game Bot

A Python-based, fully stateless Scavenger Hunt game utilizing a strict **Service Provider Interface (SPI) / Dual Black Box** architecture. The player communication layer and game administration notifications are completely separated.

## Features

- **Decoupled Architecture (Dual SPI)**:
  - `PlayerMessagingService`: Manages player input and output.
  - `AdminNotificationService`: Manages admin logging, alerts, and photo forwarding.
- **Platform Agnostic Plugins**:
  - **Telegram Bot**: Support for deep linking (`https://t.me/` URLs) and private channels.
  - **Twilio SMS/MMS**: Support for native messaging. Includes an internal async HTTP webhook server to receive texts and MMS media, plus automated markdown-to-plaintext conversion for standard SMS.
- **Build-Time Wiring**: Selected plugins are bound to the SPI interfaces at build time inside `src/main.py`.
- **100% Stateless**: Game progression is driven by scanned QR parameters. No persistent player databases are needed.
- **Cheat Prevention**: Locations use unique unguessable suffixes (e.g. `fountain_8f2a`) to prevent players from skipping steps.
- **Offline QR Code Generator**: Generates both web-based `https://` links (for Telegram) and native `sms:` URIs (which pre-fill the SMS body for Twilio).
- **Interactive Terminal Simulator**: Run the game engine directly in your command line without requiring external API keys.

---

## 🛠 Project Structure

```
scavenger_hunt/
│
├── config/
│   └── config.yml           # Clues, locations, and environment settings
│
├── src/
│   ├── core/                # Core Business Logic (Platform-independent)
│   │   ├── interfaces.py    # SPI definitions (Player & Admin Messaging, Config, QR)
│   │   ├── models.py        # Core domain dataclasses
│   │   └── engine.py        # Stateless game engine & event router
│   │
│   ├── providers/           # Shared concrete infrastructure
│   │   ├── yaml_config.py   # Config parser
│   │   └── qr_generator.py  # Image generator
│   │
│   ├── plugins/             # SPI Messaging Plugins
│   │   ├── telegram_plugin.py # Telegram player and admin plugins
│   │   └── twilio_plugin.py   # Twilio SMS player and admin plugins
│   │
│   ├── main.py              # Application entry point & build-time wiring
│   ├── generate_qrs.py      # QR code generation utility
│   └── mock_runner.py       # Terminal game simulator
│
├── tests/                   # Automated unit tests
│   └── test_engine.py       # Dual-SPI test suite
│
├── Dockerfile               # Build configuration
├── docker-compose.yml       # Orchestration config
├── requirements.txt         # Dependencies (twilio, aiohttp, python-telegram-bot)
└── README.md                # This manual
```

---

## 🚀 Getting Started

### 1. Installation

Set up a virtual environment and install the dependencies:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run the Terminal Simulator (No Bot Keys Needed!)

Play-test the core game mechanics interactively in your command line:

```bash
PYTHONPATH=. python3 src/mock_runner.py
```

*Use `/start start` to begin, `/start fountain_8f2a` to simulate finding a location, and `/photo id` to send a group picture.*

### 3. Running Automated Tests

Run the test suite to verify the dual-SPI engine transitions:

```bash
PYTHONPATH=. pytest tests/
```

---

## ⚙️ Build-Time Configuration

To choose which platforms to deploy for players and admins, edit the **BUILD-TIME SPI PLUGIN SELECTION** section at the top of `src/main.py`:

```python
# Option A: Telegram Bot (Default)
from src.plugins.telegram_plugin import TelegramPlayerMessaging, TelegramAdminNotification
PlayerMessagingClass = TelegramPlayerMessaging
AdminNotificationClass = TelegramAdminNotification

# Option B: Twilio SMS/MMS (uncomment to bind, comment Option A)
# from src.plugins.twilio_plugin import TwilioPlayerMessaging, TwilioAdminNotification
# PlayerMessagingClass = TwilioPlayerMessaging
# AdminNotificationClass = TwilioAdminNotification
```

Configure your API credentials in [config/config.yml](file:///Users/bryan/Documents/repository/hiwhereareyou/config/config.yml).

---

## 🖼 Generating QR Codes

Generate QR codes formatted specifically for your chosen player platform:

### For Telegram (`https://t.me/` URLs):
```bash
PYTHONPATH=. python3 src/generate_qrs.py --platform telegram --outdir qrs
```

### For Twilio SMS (`sms:` deep-links):
```bash
PYTHONPATH=. python3 src/generate_qrs.py --platform twilio --outdir qrs
```
*Note: The native Twilio QR code uses the `sms:+15551234567?body=fountain_8f2a` URI. When scanned, it automatically opens the phone's native messaging app, pre-fills the recipient as the Twilio number, and pre-fills the message body with the code.*

---

## 🐳 Production Deployment

### Option A: Docker Compose
Set your environment variables in a local `.env` file and boot the container:
```bash
docker-compose up -d
```

### Option B: Android Phone (Termux)
In Termux, install Python and dependencies, configure `config.yml`, set the build-time wiring in `src/main.py`, and run:
```bash
PYTHONPATH=. python src/main.py
```
*(If running Twilio on Termux, you can use a tool like `ngrok` inside Termux to expose port `5000` to the internet so Twilio can send webhooks to your phone).*
