# 📱 Secure Scavenger Hunt Telegram & Twilio Bot

A Python-based, fully stateless Scavenger Hunt game utilizing a strict **Service Provider Interface (SPI) / Dual Black Box** architecture. Progression is secured with player-specific hash verification and an active player registry.

## Features

- **Decoupled Architecture (Dual SPI)**:
  - `PlayerMessagingService`: Manages player input and output.
  - `AdminNotificationService`: Manages admin logging, alerts, and photo forwarding.
  - `PlayerRegistry`: Manages the active players registry.
- **Active Players Registry**: Only players who register via the valid starting token are permitted to progress. Gated access is disk-backed (`data/active_players.json`) and kept in-memory for instant verification.
- **Anti-Abuse Hash Progression**: Progression tokens are computed as a player-specific hash:
  $$\text{token} = \text{SHA256}(\text{salt} + \text{location\_id} + \text{player\_id})[:16]$$
  This prevents link sharing and skipping (Player B cannot use Player A's link).
- **QR Redirect Web Server**: Physical QR codes point to a browser form at `http://<domain>/scan/location_id`. The page prompts players for their ID, calculates the token using the secret salt, and automatically redirects them to the native chat app with the token prefilled.
- **Shared Utilities**: Includes a phone number standardizer utility to format numbers to E.164 (e.g. `+15551234567`).
- **Interactive Terminal Simulator**: Run the game engine directly in your command line with pre-computed tokens printed out.

---

## 🛠 Project Structure

```
scavenger_hunt/
│
├── config/
│   └── config.yml           # Clues, locations, salt, and redirection settings
│
├── data/
│   └── active_players.json  # Persistent player registry (auto-created)
│
├── src/
│   ├── core/                # Core Business Logic (Platform-independent)
│   │   ├── interfaces.py    # SPI definitions
│   │   ├── models.py        # Domain dataclasses
│   │   ├── utils.py         # Phone formatter & hash generator
│   │   └── engine.py        # Gated game engine & verification router
│   │
│   ├── providers/           # Shared concrete infrastructure
│   │   ├── yaml_config.py   # Config parser
│   │   ├── qr_generator.py  # Image generator
│   │   ├── json_registry.py # Thread-safe JSON player registry
│   │   └── redirect_server.py # Redirection server (GET forms & POST redirects)
│   │
│   ├── plugins/             # SPI Messaging Plugins
│   │   ├── telegram_plugin.py # Telegram player and admin plugins
│   │   └── twilio_plugin.py   # Twilio SMS player and admin plugins
│   │
│   ├── main.py              # Application entry point & build-time wiring
│   ├── generate_qrs.py      # QR code generation utility
│   ├── generate_start_param.py # Admin CLI tool to generate start links
│   └── mock_runner.py       # Terminal game simulator
│
├── tests/                   # Automated unit tests
│   └── test_engine.py       # Hash-based validation test suite
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

Play-test the core game mechanics interactively in your command line with pre-computed hashes:

```bash
PYTHONPATH=. python3 src/mock_runner.py
```

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

Configure your API credentials, secret salt, and redirect server settings in [config/config.yml](file:///Users/bryan/Documents/repository/hiwhereareyou/config/config.yml).

---

## 🖼 Generating QR Codes

Generate QR codes pointing to your redirect server. Ensure `game.redirect_base_url` in `config.yml` is set to your server's public domain:

```bash
PYTHONPATH=. python3 src/generate_qrs.py --outdir qrs
```
*This generates PNG images inside the `qrs/` directory. Each image points to `http://<domain>/scan/location_id` (or `start` for the seed).*

---

## 👤 Admin Tools: Generating Start Links

Organizers can generate start tokens and deep links for new players:

```bash
PYTHONPATH=. python3 src/generate_start_param.py +15551234567 --platform twilio
```
*(Optionally change `--platform` to `telegram` for Telegram start links).*

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
*(If running Twilio on Termux, you can use a tool like `ngrok` inside Termux to expose port `8080` (redirect server) and `5000` (twilio webhook) to the internet).*
