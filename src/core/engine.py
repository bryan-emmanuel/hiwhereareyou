import logging
from typing import Optional, Union
from src.core.interfaces import ConfigProvider, PlayerMessagingService, AdminNotificationService
from src.core.models import GameConfig

logger = logging.getLogger(__name__)

class ScavengerHuntEngine:
    def __init__(
        self,
        config_provider: ConfigProvider,
        player_messaging: PlayerMessagingService,
        admin_notification: AdminNotificationService
    ):
        self.config_provider = config_provider
        self.player_messaging = player_messaging
        self.admin_notification = admin_notification
        self._config: Optional[GameConfig] = None
        
        # Register the inbound player messages callback (SPI connection)
        self.player_messaging.set_inbound_handler(self.handle_player_message)

    @property
    def config(self) -> GameConfig:
        if self._config is None:
            self._config = self.config_provider.get_game_config()
        return self._config

    def reload_config(self) -> None:
        """Forces reloading the configuration."""
        self._config = self.config_provider.get_game_config()

    async def handle_player_message(self, sender_address: str, text: str, media_identifier: Optional[str] = None) -> None:
        """
        Main inbound callback executed by the Player Messaging plugin when a player sends input.
        """
        logger.info(f"Inbound player message from {sender_address}: text='{text}', media='{media_identifier}'")
        config = self.config

        # 1. Handle Photo/Media Submission first
        if media_identifier:
            logger.info(f"Forwarding photo submission from {sender_address} to admin notifications")
            caption = f"📸 Photo submission from player/group {sender_address}."
            await self.admin_notification.notify_media(media_identifier, caption)
            
            # Send confirmation back to the player
            await self.player_messaging.send_message(
                sender_address,
                "📸 *Photo received!* It has been successfully forwarded to the organizers. Thank you for sharing!"
            )
            return

        cleaned_text = text.strip()

        # If empty text, prompt them to scan or start
        if not cleaned_text:
            await self.player_messaging.send_message(
                sender_address,
                "👋 Welcome! To start the Scavenger Hunt, please scan the start QR code or send the start link."
            )
            return

        # Check for Start Seed Parameter
        if cleaned_text == config.start_param:
            if not config.locations:
                await self.player_messaging.send_message(sender_address, "⚠️ No locations are configured for this scavenger hunt.")
                return
            first_clue = config.locations[0].clue
            # Format the start message with the first clue
            msg = config.start_message.format(clue=first_clue)
            await self.player_messaging.send_message(sender_address, msg)
            return

        # Find the location corresponding to the scanned/sent parameter
        location_idx = -1
        for idx, loc in enumerate(config.locations):
            if loc.id == cleaned_text:
                location_idx = idx
                break

        if location_idx == -1:
            await self.player_messaging.send_message(
                sender_address,
                "❌ Invalid code scanned. Please make sure you are scanning the official QR code."
            )
            return

        solved_location = config.locations[location_idx]

        # Check if there is a next location
        if location_idx + 1 < len(config.locations):
            next_location = config.locations[location_idx + 1]
            success_msg = (
                f"✅ *Location Found:* {solved_location.name}\n\n"
                f"Here is your next clue:\n"
                f"🔍 _{next_location.clue}_\n\n"
                f"📸 *Optional:* Send a photo of your group here to share it with the organizers!"
            )
            await self.player_messaging.send_message(sender_address, success_msg)
        else:
            # Final location!
            success_msg = (
                f"🏆 *Final Location Found:* {solved_location.name}!\n\n"
                f"{config.final_message}\n\n"
                f"📸 *Optional:* Send a photo of your group here to share it with the organizers!"
            )
            await self.player_messaging.send_message(sender_address, success_msg)
            
            # Send completion notification to admins
            await self.admin_notification.notify_text(f"🏁 Player/Group {sender_address} has completed the scavenger hunt!")
