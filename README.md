# 📱 Secure Scavenger Hunt Telegram & Twilio Bot

A Python-based, fully stateless Scavenger Hunt game utilizing a strict **Service Provider Interface (SPI) / Dual Black Box** architecture. Access is restricted to authorized players via direct admin registration.

## Features

- **Decoupled Architecture (Dual SPI)**:
  - `PlayerMessagingService`: Manages player input and output.
  - `AdminNotificationService`: Manages admin logging, alerts, and inbound message commands.
  - `PlayerRegistry`: Manages the active players registry.
- **Direct Admin Registration**: Admins register player IDs directly via bot messaging (E.164 phone numbers for Twilio, usernames/chat IDs for Telegram).
- **Direct QR Scans**: Since players are registered directly in the bot database, physical QR codes link directly back to the Telegram bot (`https://t.me/Bot?start=location_id`) or Twilio SMS body (`sms:number?body=location_id`). No redirection web server or player-specific hash computation is required.
- **Security / Abuse Hardening**: The bot ignores any message (start or location scan) from unregistered players outright. 
- **Stateless Next-Clue Progression**: 
  - There is no start parameter. The game begins directly when a registered player scans the QR code at Location 1.
  - When Location X is scanned, the bot looks up its index and replies with the clue leading to Location X+1.
  - When the final location is scanned, the bot delivers the completion message and alerts the admins.
  - Progression is fully stateless at runtime, resolved dynamically via configuration lookup.
- **Unguessable Location Codes**: Location IDs in `config.yml` can contain random suffixes (e.g., `fountain_8f2a`) to prevent registered players from guessing coordinates and skipping steps.
- **Interactive Terminal Simulator**: Run the game engine directly in your command line with simulated player and admin commands.

---

## 🛠 Project Structure

```
scavenger_hunt/
│
├── config/
│   └── config.yml           # Clues, locations, and platform parameters
│
├── data/
│   └── active_players.json  # Persistent player registry database (auto-created)
│
├── src/
│   ├── core/                # Core Business Logic (Platform-independent)
│   │   ├── interfaces.py    # SPI definitions
│   │   ├── models.py        # Domain dataclasses
│   │   ├── utils.py         # Phone number standardizer
│   │   └── engine.py        # Gated game engine & admin command router
│   │
│   ├── providers/           # Shared concrete infrastructure
│   │   ├── yaml_config.py   # Config parser
│   │   ├── qr_generator.py  # Image generator
│   │   └── json_registry.py # Thread-safe JSON player registry database
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
│   └── test_engine.py       # Gated progression test suite
│
├── Dockerfile               # Build configuration
├── docker-compose.yml       # Orchestration config
├── requirements.txt         # Dependencies
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

### 3. Running Automated Tests

Run the test suite to verify the gating and transition rules:

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

Configure your API credentials and location parameters in [config/config.yml](file:///Users/bryan/Documents/repository/hiwhereareyou/config/config.yml).

---

## 🛠 Admin Messaging Commands

Administrators drive the bot functions directly from their channel/chat:
- **`help`**: Shows a list of admin commands.
- **`generate <Player ID>`**: Standardizes and registers a player ID immediately in the database.
- **`reset`**: Wipes all players from the registration database.

---

## 🖼 Generating QR Codes

Generate QR codes linking directly to your Telegram bot or Twilio phone number:

```bash
PYTHONPATH=. python3 src/generate_qrs.py --platform telegram --outdir qrs
```
*(This generates PNG images inside the `qrs/` directory. Each image points directly to `https://t.me/{bot_username}?start={location_id}`).*
