import logging
from typing import Optional, Union
from src.core.interfaces import ConfigProvider, PlayerMessagingService, AdminNotificationService, PlayerRegistry
from src.core.models import GameConfig
from src.core.utils import format_phone_number

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
        
        # Wire SPI inbound callbacks
        self.player_messaging.set_inbound_handler(self.handle_player_message)

    @property
    def config(self) -> GameConfig:
        if self._config is None:
            self._config = self.config_provider.get_game_config()
        return self._config

    def reload_config(self) -> None:
        """Forces reloading the configuration."""
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
        Main inbound player message callback. Handles direct plaintext commands for registered players.
        Unregistered players or invalid messages are ignored outright.
        """
        config = self.config
        player_id = self._get_standardized_player_id(sender_address)
        cleaned_text = text.strip()

        # Intercept admin commands sent to the bot (fixes routing bug where plugins send all to player handler)
        if str(sender_address) == str(config.telegram_master_admin_id):
            # Admin sending media should be ignored or handled separately if needed, for now we just handle text commands
            if cleaned_text:
                await self.handle_admin_message(sender_address, text)
            return

        logger.info(f"Inbound message from '{sender_address}' (Standardized ID: '{player_id}'): text='{cleaned_text}', media='{media_identifier}'")

        # 1. Gated check: If player ID is not registered, ignore the message outright
        if not self.player_registry.is_player_registered(player_id):
            logger.info(f"Ignored message/media from unregistered player {player_id}")
            return

        # 2. Check if the player sent a photo
        if media_identifier:
            logger.info(f"Forwarding photo submission from registered player {player_id} to admins")
            caption = f"📸 Photo submission from registered player/group {player_id}."
            await self.admin_notification.notify_media(media_identifier, caption)
            
            await self.player_messaging.send_message(
                sender_address,
                "📸 *Photo received!* It has been successfully forwarded to the organizers. Thank you for sharing!"
            )
            return

        # 3. Check for empty inputs (ignore outright)
        if not cleaned_text:
            return

        # 4. Check if the input text matches any location ID directly
        location_idx = -1
        for idx, loc in enumerate(config.locations):
            if cleaned_text.lower() == loc.id.lower():
                location_idx = idx
                break

        # If it doesn't match any location ID, ignore outright
        if location_idx == -1:
            logger.info(f"Ignored invalid command/message from registered player {player_id}: '{cleaned_text}'")
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

    async def handle_admin_message(self, sender_address: str, text: str) -> None:
        """
        Main inbound admin command callback.
        """
        cleaned_text = text.strip()
        
        # Support slash-prefixed commands (e.g. /help -> help)
        if cleaned_text.startswith("/"):
            cleaned_text = cleaned_text[1:]

        parts = cleaned_text.split(None, 1)
        command = parts[0].lower() if parts else ""
        args = parts[1].strip() if len(parts) > 1 else ""

        logger.info(f"Inbound admin command from '{sender_address}': command='{command}', args='{args}'")

        if command == "help":
            help_msg = (
                "🛠 *Administrator Functions:*\n\n"
                "• `help` - Show this list of functions.\n"
                "• `allowlist view` - List all registered allowlist users.\n"
                "• `allowlist add <Player ID>` - Register a player's phone number or Telegram ID.\n"
                "• `allowlist remove <Player ID>` - Remove a specific player from the allowlist.\n"
                "• `generate <Player ID>` - (Alias) Register a player.\n"
                "• `reset` - Reset the active players registry, clearing all registered players.\n"
                "• `locations` - View all game locations with IDs, clues, and shareable message links.\n"
                "• `test <message>` - Simulate a player message and receive the same reply a player would."
            )
            await self.admin_notification.notify_text(help_msg)
            return

        elif command == "reset":
            try:
                self.player_registry.reset_registry()
                logger.info("Admin triggered registry reset.")
                await self.admin_notification.notify_text("🧹 *Registry Reset Successful.*\nAll registered players have been cleared from memory and disk.")
            except Exception as e:
                logger.error(f"Error resetting registry: {e}")
                await self.admin_notification.notify_text("❌ *Failed to reset registry.* Check application logs.")
            return

        elif command == "generate" or (command == "allowlist" and args.startswith("add ")):
            sub_args = args[4:].strip() if command == "allowlist" else args
            if not sub_args:
                await self.admin_notification.notify_text("⚠️ *Usage:* `allowlist add <Player ID>`")
                return

            player_id = sub_args
            # Standardize if phone number
            if player_id.startswith("+") or player_id.isdigit() or ("-" in player_id) or ("(" in player_id):
                try:
                    player_id = format_phone_number(player_id)
                except Exception:
                    pass

            # Register the player directly in the active registry database
            self.player_registry.register_player(player_id)
            
            # Simple confirmation of the successful registration
            await self.admin_notification.notify_text(f"👤 Player/Group {player_id} added to the allowlist successfully!")
            return

        elif command == "allowlist" and args == "view":
            players = self.player_registry.get_all_players()
            if not players:
                await self.admin_notification.notify_text("📋 *Allowlist:* Empty.")
                return
            
            lines = ["📋 *Registered Allowlist Users:*\n"]
            for idx, p in enumerate(players, 1):
                lines.append(f"{idx}. `{p}`")
            await self.admin_notification.notify_text("\n".join(lines))
            return

        elif command == "allowlist" and args.startswith("remove "):
            player_id = args[7:].strip()
            if not player_id:
                await self.admin_notification.notify_text("⚠️ *Usage:* `allowlist remove <Player ID>`")
                return

            if player_id.startswith("+") or player_id.isdigit() or ("-" in player_id) or ("(" in player_id):
                try:
                    player_id = format_phone_number(player_id)
                except Exception:
                    pass

            if str(player_id) == str(self.config.telegram_master_admin_id):
                await self.admin_notification.notify_text("🛡️ *Action Denied:* Cannot remove the master admin from the allowlist. This prevents accidental lockout.")
                return

            if self.player_registry.is_player_registered(player_id):
                self.player_registry.remove_player(player_id)
                await self.admin_notification.notify_text(f"🗑 Player/Group {player_id} removed from the allowlist.")
            else:
                await self.admin_notification.notify_text(f"⚠️ Player/Group {player_id} was not found on the allowlist.")
            return

        elif command == "locations":
            config = self.config
            if not config.locations:
                await self.admin_notification.notify_text("📍 No locations configured.")
                return

            lines = ["📍 *Game Locations:*\n"]
            for idx, loc in enumerate(config.locations, 1):
                tg_link = f"https://t.me/{config.telegram_bot_username}?start={loc.id}"
                sms_link = f"sms:{config.twilio_phone_number}?body={loc.id}"
                lines.append(
                    f"*{idx}. {loc.name}*\n"
                    f"   ID: `{loc.id}`\n"
                    f"   Clue: _{loc.clue}_\n"
                    f"   Telegram: {tg_link}\n"
                    f"   SMS: `{sms_link}`\n"
                )
            await self.admin_notification.notify_text("\n".join(lines))
            return

        elif command == "test":
            if not args:
                await self.admin_notification.notify_text("⚠️ *Usage:* `test <message>` (e.g., `test fountain_8f2a`)")
                return

            # Process the message through the player handler, but route the reply back to the admin channel
            config = self.config
            location_idx = -1
            for idx, loc in enumerate(config.locations):
                if args.lower() == loc.id.lower():
                    location_idx = idx
                    break

            if location_idx == -1:
                await self.admin_notification.notify_text(f"🧪 *Test Result:* Message `{args}` would be ignored (no matching location).")
                return

            solved_location = config.locations[location_idx]

            if location_idx + 1 < len(config.locations):
                next_location = config.locations[location_idx + 1]
                reply = (
                    f"✅ *Location Found:* {solved_location.name}\n\n"
                    f"Here is your next clue:\n"
                    f"🔍 _{next_location.clue}_\n\n"
                    f"📸 *Optional:* Send a photo of your group here to share it with the organizers!"
                )
            else:
                reply = (
                    f"🏆 *Final Location Found:* {solved_location.name}!\n\n"
                    f"{config.final_message}\n\n"
                    f"📸 *Optional:* Send a photo of your group here to share it with the organizers!"
                )

            await self.admin_notification.notify_text(f"🧪 *Test Result for* `{args}`:\n\n{reply}")
            return

        else:
            await self.admin_notification.notify_text(
                "⚠️ Unrecognized command. Type `help` to see a list of administrator functions."
            )
            return
