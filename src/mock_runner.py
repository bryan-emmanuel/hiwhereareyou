import asyncio
from typing import Optional, Union
from src.providers.yaml_config import YAMLConfigProvider
from src.providers.json_registry import JSONPlayerRegistry
from src.core.interfaces import PlayerMessagingService, AdminNotificationService
from src.core.engine import ScavengerHuntEngine
from src.core.utils import format_phone_number, calculate_parameter_hash

class MockPlayerMessaging(PlayerMessagingService):
    def __init__(self):
        self._handler = None

    def initialize(self, config) -> None:
        pass

    def set_inbound_handler(self, handler) -> None:
        self._handler = handler

    async def send_message(self, player_address: str, text: str) -> None:
        print(f"\n--- 💬 PLAYER MSG to {player_address} ---")
        print(text)
        print("------------------------------------------\n")

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

class MockAdminNotification(AdminNotificationService):
    def initialize(self, config) -> None:
        pass

    async def notify_text(self, text: str) -> None:
        print(f"\n--- 📣 ADMIN NOTIFICATION LOG ---")
        print(text)
        print("----------------------------------\n")

    async def notify_media(self, media_identifier: str, caption: str) -> None:
        print(f"\n--- 📣 ADMIN RECEIVED PHOTO ---")
        print(f"Media Reference: {media_identifier}")
        print(f"Caption:         {caption}")
        print("-------------------------------\n")

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

async def main():
    print("🤖 Scavenger Hunt Simulator (Hash-Based & Registry Gate) 🤖")
    print("=========================================================")
    print("Loading config/config.yml...")
    
    config_provider = YAMLConfigProvider("config/config.yml")
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    
    # Use a separate JSON registry for mock testing
    player_registry = JSONPlayerRegistry("data/active_players_mock.json")
    
    try:
        engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)
        config = engine.config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return

    # Prompt for Player ID to pre-generate hashes
    player_address = input("Enter mock player ID (e.g. +15559999 or username) [default: +15559999]: ").strip()
    if not player_address:
        player_address = "+15559999"

    # Standardize player ID
    player_id = player_address
    if player_id.startswith("+") or player_id.isdigit() or ("-" in player_id) or ("(" in player_id):
        try:
            player_id = format_phone_number(player_id)
            print(f"📞 Standardized Player ID: {player_id}")
        except Exception:
            pass

    # Print out pre-computed tokens for mock testing
    print("\n=========================================================")
    print("🔑 PRE-COMPUTED HASH TOKENS FOR THIS PLAYER ID")
    print("=========================================================")
    
    start_hash = calculate_parameter_hash(config.salt, config.start_param, player_id)
    print(f"1. Start Token (simulates scanning seed QR):")
    print(f"   Command:  /start {start_hash}")
    
    print("\n2. Location Tokens (simulates scanning location QRs):")
    for idx, loc in enumerate(config.locations, 1):
        loc_hash = calculate_parameter_hash(config.salt, loc.id, player_id)
        print(f"   [{idx}] {loc.name} (ID: {loc.id}):")
        print(f"       Command:  {loc_hash}")
    print("=========================================================\n")

    print("Commands:")
    print("  /start [param]  - Simulate player starting (e.g. '/start <token>')")
    print("  /photo [id]     - Simulate player uploading photo (e.g. '/photo group_pic_1')")
    print("  /help           - Show help instructions")
    print("  /exit           - Exit simulator")
    print("  [token]         - Send raw token/text")
    print("=========================================\n")

    while True:
        try:
            line = input("scavenger-hunt-sim> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting simulator.")
            break
            
        if not line:
            continue

        if line == "/exit":
            print("Exiting simulator.")
            break
        elif line == "/help":
            if player_messaging._handler:
                await player_messaging._handler(player_address, "help", None)
        elif line.startswith("/start"):
            parts = line.split(" ", 1)
            param = parts[1].strip() if len(parts) > 1 else ""
            if player_messaging._handler:
                await player_messaging._handler(player_address, param, None)
        elif line.startswith("/photo"):
            parts = line.split(" ", 1)
            photo_id = parts[1].strip() if len(parts) > 1 else "mock_photo_url_or_id"
            if player_messaging._handler:
                await player_messaging._handler(player_address, "", photo_id)
        else:
            if player_messaging._handler:
                await player_messaging._handler(player_address, line, None)

if __name__ == "__main__":
    asyncio.run(main())
