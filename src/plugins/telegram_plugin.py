import logging
from typing import Optional, Union
from telegram import Bot, Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from src.core.interfaces import PlayerMessagingService, AdminNotificationService
from src.core.models import GameConfig

logger = logging.getLogger(__name__)

class TelegramPlayerMessaging(PlayerMessagingService):
    def __init__(self):
        self._handler: Optional[callable] = None
        self._app: Optional[Application] = None
        self._bot: Optional[Bot] = None
        self.config: Optional[GameConfig] = None

    def initialize(self, config: GameConfig) -> None:
        """Initialize with build-time config."""
        self.config = config
        self._bot = Bot(token=config.telegram_bot_token)

    def set_inbound_handler(self, handler: callable) -> None:
        self._handler = handler

    async def send_message(self, player_address: str, text: str) -> None:
        if not self._bot:
            raise RuntimeError("TelegramPlayerMessaging is not initialized.")
        try:
            await self._bot.send_message(chat_id=player_address, text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Telegram failed to send message to player {player_address}: {e}")

    async def start(self) -> None:
        if not self.config:
            raise RuntimeError("TelegramPlayerMessaging is not initialized.")
        
        # Build the application
        app_builder = ApplicationBuilder().token(self.config.telegram_bot_token)
        self._app = app_builder.build()

        async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            args = context.args
            param = args[0].strip() if args else ""
            if self._handler:
                # Pass the deep-link param directly to the engine
                await self._handler(chat_id, param, None)

        async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            if self._handler:
                # Treat /help command as "help" text
                await self._handler(chat_id, "help", None)

        async def photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            if update.message.photo and self._handler:
                # Send the file_id of the largest photo
                photo_file_id = update.message.photo[-1].file_id
                await self._handler(chat_id, "", photo_file_id)

        async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            if str(self.config.telegram_master_admin_id) == chat_id:
                status_msg = "✅ <b>hiwhereareyou Status</b>\n\nSystem is online and running normally."
                await update.message.reply_text(status_msg, parse_mode=ParseMode.HTML)
            else:
                if self._handler:
                    await self._handler(chat_id, "/status", None)

        async def text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            text = update.message.text or ""
            if self._handler:
                await self._handler(chat_id, text, None)

        # Register bot handlers
        self._app.add_handler(CommandHandler("start", start_callback))
        self._app.add_handler(CommandHandler("help", help_callback))
        self._app.add_handler(CommandHandler("status", status_callback))
        self._app.add_handler(MessageHandler(filters.PHOTO, photo_callback))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_callback))

        # Start async polling
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        logger.info("Telegram Player Messaging listener started.")

    async def stop(self) -> None:
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            logger.info("Telegram Player Messaging listener stopped.")


class TelegramAdminNotification(AdminNotificationService):
    def __init__(self):
        self._bot: Optional[Bot] = None
        self.config: Optional[GameConfig] = None

    def initialize(self, config: GameConfig) -> None:
        """Initialize with build-time config."""
        self.config = config
        self._bot = Bot(token=config.telegram_bot_token)

    async def notify_text(self, text: str) -> None:
        if not self._bot or not self.config:
            raise RuntimeError("TelegramAdminNotification is not initialized.")
        try:
            await self._bot.send_message(
                chat_id=self.config.telegram_master_admin_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Telegram failed to send admin notification: {e}")

    async def notify_media(self, media_identifier: str, caption: str) -> None:
        if not self._bot or not self.config:
            raise RuntimeError("TelegramAdminNotification is not initialized.")
        try:
            # Telegram's send_photo supports both file_ids and external image URLs (e.g. from Twilio)
            await self._bot.send_photo(
                chat_id=self.config.telegram_master_admin_id,
                photo=media_identifier,
                caption=caption
            )
        except Exception as e:
            logger.error(f"Telegram failed to send admin media: {e}")

    async def start(self) -> None:
        logger.info("Telegram Admin Notification Service started.")

    async def stop(self) -> None:
        logger.info("Telegram Admin Notification Service stopped.")
