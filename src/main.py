import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from src.providers.yaml_config import YAMLConfigProvider
from src.providers.json_registry import JSONPlayerRegistry
from src.core.engine import ScavengerHuntEngine

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("scavenger_hunt")


# =====================================================================
# BUILD-TIME SPI PLUGIN SELECTION
# =====================================================================
# Choose which plugins to bind to the SPI interfaces at build time:

# Option A: Telegram Bot (Default)
from src.plugins.telegram_plugin import TelegramPlayerMessaging, TelegramAdminNotification
PlayerMessagingClass = TelegramPlayerMessaging
AdminNotificationClass = TelegramAdminNotification

# Option B: Twilio SMS/MMS (uncomment to bind, comment Option A)
# from src.plugins.twilio_plugin import TwilioPlayerMessaging
# PlayerMessagingClass = TwilioPlayerMessaging
# AdminNotificationClass = TelegramAdminNotification # No Twilio admin plugin provided yet
# =====================================================================


async def async_main():
    config_path = os.environ.get("SCAVENGER_CONFIG_PATH", "config/config.yml")
    logger.info(f"Loading configuration from: {config_path}")
    
    config_provider = YAMLConfigProvider(config_path)
    try:
        config = config_provider.get_game_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # 1. Instantiate the build-time selected plugins
    logger.info(f"Instantiating player messaging plugin: {PlayerMessagingClass.__name__}")
    player_messaging = PlayerMessagingClass()
    player_messaging.initialize(config)

    logger.info(f"Instantiating admin notifications plugin: {AdminNotificationClass.__name__}")
    admin_notification = AdminNotificationClass()
    admin_notification.initialize(config)

    # 2. Instantiate the disk-backed active players registry
    registry_path = os.environ.get("SCAVENGER_REGISTRY_PATH", "data/active_players.json")
    logger.info(f"Loading player registry from: {registry_path}")
    player_registry = JSONPlayerRegistry(registry_path)

    # 3. Instantiate and wire the core engine
    logger.info("Initializing game core engine...")
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    # 4. Start services
    logger.info("Starting player messaging and admin notifications...")
    await player_messaging.start()
    await admin_notification.start()
    
    logger.info("🎉 Scavenger Hunt system is active and running!")
    
    # 5. Wait for termination signal
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Termination signal received. Shutting down services...")
        await player_messaging.stop()
        await admin_notification.stop()


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Application shut down by user.")


if __name__ == "__main__":
    main()
