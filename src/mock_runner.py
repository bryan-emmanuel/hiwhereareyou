import asyncio
from typing import Optional, Union
from src.providers.yaml_config import YAMLConfigProvider
from src.core.interfaces import PlayerMessagingService, AdminNotificationService
from src.core.engine import ScavengerHuntEngine

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
    print("🤖 Scavenger Hunt Simulator (Dual SPI) 🤖")
    print("=======================================")
    print("Loading config/config.yml...")
    
    config_provider = YAMLConfigProvider("config/config.yml")
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    
    try:
        engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification)
        config = engine.config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return

    print("Game loaded! Commands:")
    print("  /start [param]  - Simulate player scanning QR code (e.g. '/start start', '/start fountain_8f2a')")
    print("  /photo [id]     - Simulate player uploading photo (e.g. '/photo group_pic_1')")
    print("  /help           - Show game help instructions")
    print("  /exit           - Exit simulator")
    print("  [any other text] - Send raw text input as player")
    print("=======================================")

    player_address = "+15559999"  # Mock phone number / chat ID

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
