import logging
from typing import Optional, Union
from telegram import Bot, Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from src.core.interfaces import MessagingProvider
from src.core.engine import ScavengerHuntEngine

logger = logging.getLogger(__name__)

class TelegramMessagingProvider(MessagingProvider):
    def __init__(self, bot_token: str, admin_channel_id: Union[str, int]):
        self.bot_token = bot_token
        self.admin_channel_id = admin_channel_id
        # Initialize Bot instance for sending messages
        self._bot = Bot(token=self.bot_token)

    async def send_message(self, chat_id: Union[int, str], text: str, parse_mode: str = "Markdown") -> None:
        """Sends a text message using the Telegram Bot API."""
        try:
            # Map parse mode to telegram.constants.ParseMode
            t_parse_mode = ParseMode.MARKDOWN
            if parse_mode.lower() == "html":
                t_parse_mode = ParseMode.HTML
            elif parse_mode.lower() == "markdownv2":
                t_parse_mode = ParseMode.MARKDOWN_V2

            await self._bot.send_message(chat_id=chat_id, text=text, parse_mode=t_parse_mode)
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")

    async def forward_photo_to_admin(self, photo_identifier: str, caption: str) -> None:
        """Forwards a photo to the configured admin channel."""
        try:
            await self._bot.send_photo(chat_id=self.admin_channel_id, photo=photo_identifier, caption=caption)
            logger.info(f"Forwarded photo {photo_identifier} to admin channel {self.admin_channel_id}")
        except Exception as e:
            logger.error(f"Failed to forward photo {photo_identifier} to admin channel ({self.admin_channel_id}): {e}")


def build_telegram_application(engine: ScavengerHuntEngine) -> Application:
    """
    Builds the telegram Application, registers handlers, and binds it to the Core Engine.
    """
    config = engine.config
    
    # We construct the application builder with the bot token
    app_builder = ApplicationBuilder().token(config.bot_token)
    app = app_builder.build()

    async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        args = context.args
        param = args[0] if args else ""
        await engine.handle_start_command(chat_id, param)

    async def photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        username = update.effective_user.username
        
        if update.message.photo:
            # Send the largest available photo version
            photo = update.message.photo[-1]
            photo_file_id = photo.file_id
            
            await engine.handle_photo_submission(
                sender_username=username,
                sender_id=chat_id,
                photo_identifier=photo_file_id
            )
            
            # Send confirmation message to the player
            await engine.messaging_provider.send_message(
                chat_id=chat_id,
                text="📸 *Photo received!* It has been successfully forwarded to the organizers. Thank you for sharing!"
            )

    async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = (
            "🔍 *Scavenger Hunt Help*\n\n"
            "• *Start the game*: Scan the starting QR code or click the start link provided by the organizers.\n"
            "• *Progression*: Find each location and scan its QR code. Doing so unlocks the next clue instantly.\n"
            "• *Photos*: Take a photo of your team at any location and send it directly to this chat. It will be collected for the game gallery!\n"
            "• *Clue Recovery*: If you need to see your current clue again, simply re-scan the QR code of the last location you found."
        )
        await engine.messaging_provider.send_message(chat_id=update.effective_chat.id, text=help_text)

    # Register handlers
    app.add_handler(CommandHandler("start", start_callback))
    app.add_handler(CommandHandler("help", help_callback))
    app.add_handler(MessageHandler(filters.PHOTO, photo_callback))

    return app
