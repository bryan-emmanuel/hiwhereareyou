import asyncio
from typing import Optional, Union, Callable
from src.providers.yaml_config import YAMLConfigProvider
from src.core.interfaces import PlayerMessagingService, AdminNotificationService
from src.core.engine import ScavengerHuntEngine
from src.core.utils import format_phone_number

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
    def __init__(self):
        self._handler = None

    def initialize(self, config) -> None:
        pass

    def set_inbound_handler(self, handler: Callable) -> None:
        self._handler = handler

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
    print("🤖 Scavenger Hunt Simulator (Direct Registration Flow) 🤖")
    print("=========================================================")
    print("Loading config/config.yml...")
    
    config_provider = YAMLConfigProvider("config/config.yml")
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    
    from src.providers.json_registry import JSONPlayerRegistry
    player_registry = JSONPlayerRegistry("data/active_players_mock.json")
    
    try:
        engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)
        config = engine.config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return

    # Prompt for Player ID
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

    print("\n=========================================================")
    print("📍 PLAIN TEXT COMMANDS FOR THIS SIMULATOR")
    print("=========================================================")
    print(f"1. Start Command:      {config.start_param}")
    print("\n2. Location Scan codes:")
    for idx, loc in enumerate(config.locations, 1):
        print(f"   [{idx}] {loc.name}: {loc.id}")
    print("=========================================================\n")

    print("Simulator Commands:")
    print("  /start [param]       - Simulate player starting (e.g. '/start start')")
    print("  /photo [id]          - Simulate player uploading photo (e.g. '/photo group_pic_1')")
    print("  /help                - Show help instructions for players")
    print("  /exit                - Exit simulator")
    print("  /admin help          - Simulate admin requesting help")
    print("  /admin reset         - Simulate admin wiping player registry")
    print("  /admin generate <id> - Simulate admin registering a player ID (e.g. '/admin generate +15559999')")
    print("  /admin [text]        - Simulate admin sending general command text")
    print("  [text]               - Send raw text as player")
    print("=========================================================\n")

    admin_address = "admin_channel_or_number"

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
        elif line.startswith("/admin"):
            parts = line.split(" ", 1)
            cmd = parts[1].strip() if len(parts) > 1 else ""
            if admin_notification._handler:
                await admin_notification._handler(admin_address, cmd)
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
