import logging
from typing import Optional, Union
from src.core.interfaces import ConfigProvider, PlayerMessagingService, AdminNotificationService, PlayerRegistry
from src.core.models import GameConfig
from src.core.utils import format_phone_number, calculate_parameter_hash

logger = logging.getLogger(__name__)

class ScavengerHuntEngine:
    def __init__(
        self,
        config_provider: ConfigProvider,
        player_messaging: PlayerMessagingService,
        admin_notification: AdminNotificationService,
        player_registry: PlayerRegistry
    ):
        self.config_provider = config_provider
        self.player_messaging = player_messaging
        self.admin_notification = admin_notification
        self.player_registry = player_registry
        self._config: Optional[GameConfig] = None
        
        # Wire SPI inbound callback
        self.player_messaging.set_inbound_handler(self.handle_player_message)

    @property
    def config(self) -> GameConfig:
        if self._config is None:
            self._config = self.config_provider.get_game_config()
        return self._config

    def reload_config(self) -> None:
        self._config = self.config_provider.get_game_config()

    def _get_standardized_player_id(self, sender_address: str) -> str:
        """Standardizes phone numbers if the sender is from Twilio."""
        player_id = sender_address.strip()
        # Check if the player address looks like a phone number
        if player_id.startswith("+") or player_id.isdigit() or ("-" in player_id) or ("(" in player_id):
            try:
                return format_phone_number(player_id)
            except Exception as e:
                logger.error(f"Error standardizing phone number '{player_id}': {e}")
        return player_id

    async def handle_player_message(self, sender_address: str, text: str, media_identifier: Optional[str] = None) -> None:
        """
        Main inbound player message callback.
        """
        config = self.config
        player_id = self._get_standardized_player_id(sender_address)
        cleaned_text = text.strip()

        logger.info(f"Inbound message from '{sender_address}' (Standardized ID: '{player_id}'): text='{cleaned_text}', media='{media_identifier}'")

        # 1. Check if the player sent a photo
        if media_identifier:
            # Player must be active to submit photos
            if not self.player_registry.is_player_registered(player_id):
                await self.player_messaging.send_message(
                    sender_address,
                    "❌ You have not started the Scavenger Hunt yet. Please scan the starting QR code first!"
                )
                return

            logger.info(f"Forwarding photo submission from registered player {player_id} to admins")
            caption = f"📸 Photo submission from registered player/group {player_id}."
            await self.admin_notification.notify_media(media_identifier, caption)
            
            await self.player_messaging.send_message(
                sender_address,
                "📸 *Photo received!* It has been successfully forwarded to the organizers. Thank you for sharing!"
            )
            return

        # 2. Check for empty inputs
        if not cleaned_text:
            await self.player_messaging.send_message(
                sender_address,
                "👋 Welcome! To start the Scavenger Hunt, please scan the start QR code or enter your start link."
            )
            return

        # 3. Check if input matches the start seed hash
        start_hash = calculate_parameter_hash(config.salt, config.start_param, player_id)
        if cleaned_text == start_hash:
            # Register the player
            self.player_registry.register_player(player_id)
            logger.info(f"Registered new active player: {player_id}")

            if not config.locations:
                await self.player_messaging.send_message(sender_address, "⚠️ No locations are configured for this scavenger hunt.")
                return

            first_clue = config.locations[0].clue
            msg = config.start_message.format(player_id=player_id, clue=first_clue)
            await self.player_messaging.send_message(sender_address, msg)
            return

        # 4. Gated verification check for registered players only
        if not self.player_registry.is_player_registered(player_id):
            await self.player_messaging.send_message(
                sender_address,
                "❌ You have not registered/started the game yet. Please scan the starting QR code first to register!"
            )
            return

        # 5. Check if the parameter matches any location hash
        location_idx = -1
        for idx, loc in enumerate(config.locations):
            loc_hash = calculate_parameter_hash(config.salt, loc.id, player_id)
            if cleaned_text == loc_hash:
                location_idx = idx
                break

        if location_idx == -1:
            await self.player_messaging.send_message(
                sender_address,
                "❌ Invalid code scanned. Please make sure you are scanning the official QR code at your current location."
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
            await self.admin_notification.notify_text(f"🏁 Player/Group {player_id} has completed the scavenger hunt!")
