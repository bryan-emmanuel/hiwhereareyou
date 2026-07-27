import logging
from typing import Optional, Union, Callable
from telegram import Bot, Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from src.core.interfaces import PlayerMessagingService, AdminNotificationService
from src.core.models import GameConfig

logger = logging.getLogger(__name__)

# Shared application singleton to prevent Conflict error (multiple polling loops on the same token)
_shared_app: Optional[Application] = None
_app_started = False

def _get_shared_app(bot_token: str) -> Application:
    global _shared_app
    if _shared_app is None:
        logger.info("Initializing shared Telegram Application instance...")
        app_builder = ApplicationBuilder().token(bot_token)
        _shared_app = app_builder.build()
    return _shared_app

async def _start_shared_app() -> None:
    global _app_started, _shared_app
    if _shared_app and not _app_started:
        await _shared_app.initialize()
        await _shared_app.start()
        await _shared_app.updater.start_polling()
        _app_started = True
        logger.info("Shared Telegram polling started.")

async def _stop_shared_app() -> None:
    global _app_started, _shared_app
    if _shared_app and _app_started:
        await _shared_app.updater.stop()
        await _shared_app.stop()
        await _shared_app.shutdown()
        _app_started = False
        logger.info("Shared Telegram polling stopped.")


class TelegramPlayerMessaging(PlayerMessagingService):
    def __init__(self):
        self._handler: Optional[Callable] = None
        self._bot: Optional[Bot] = None
        self.config: Optional[GameConfig] = None

    def initialize(self, config: GameConfig) -> None:
        self.config = config
        self._bot = Bot(token=config.telegram_bot_token)

    def set_inbound_handler(self, handler: Callable) -> None:
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
        
        app = _get_shared_app(self.config.telegram_bot_token)

        async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            args = context.args
            param = args[0].strip() if args else ""
            if self._handler:
                await self._handler(chat_id, param, None)

        async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            if self._handler:
                await self._handler(chat_id, "help", None)

        async def photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            if update.message.photo and self._handler:
                photo_file_id = update.message.photo[-1].file_id
                await self._handler(chat_id, "", photo_file_id)

        async def text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = str(update.effective_chat.id)
            text = update.message.text or ""
            if self._handler:
                await self._handler(chat_id, text, None)

        # Register player handlers
        app.add_handler(CommandHandler("start", start_callback))
        app.add_handler(CommandHandler("help", help_callback))
        app.add_handler(MessageHandler(filters.PHOTO, photo_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, text_callback))

        # Start shared polling loop
        await _start_shared_app()

    async def stop(self) -> None:
        await _stop_shared_app()


class TelegramAdminNotification(AdminNotificationService):
    def __init__(self):
        self._handler: Optional[Callable] = None
        self._bot: Optional[Bot] = None
        self.config: Optional[GameConfig] = None

    def initialize(self, config: GameConfig) -> None:
        self.config = config
        self._bot = Bot(token=config.telegram_bot_token)

    def set_inbound_handler(self, handler: Callable) -> None:
        self._handler = handler

    async def notify_text(self, text: str) -> None:
        if not self._bot or not self.config:
            raise RuntimeError("TelegramAdminNotification is not initialized.")
        try:
            await self._bot.send_message(
                chat_id=self.config.telegram_admin_channel_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Telegram failed to send admin notification: {e}")

    async def notify_media(self, media_identifier: str, caption: str) -> None:
        if not self._bot or not self.config:
            raise RuntimeError("TelegramAdminNotification is not initialized.")
        try:
            await self._bot.send_photo(
                chat_id=self.config.telegram_admin_channel_id,
                photo=media_identifier,
                caption=caption
            )
        except Exception as e:
            logger.error(f"Telegram failed to send admin media: {e}")

    async def start(self) -> None:
        if not self.config:
            raise RuntimeError("TelegramAdminNotification is not initialized.")
        
        app = _get_shared_app(self.config.telegram_bot_token)

        async def channel_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if update.channel_post and update.channel_post.text:
                chat_id = str(update.channel_post.chat.id)
                target_id = str(self.config.telegram_admin_channel_id)
                
                # Check if it matches target admin channel ID or username
                is_match = (chat_id == target_id)
                if update.channel_post.chat.username:
                    is_match = is_match or (update.channel_post.chat.username == target_id.lstrip("@"))
                
                if is_match:
                    text = update.channel_post.text
                    if self._handler:
                        await self._handler(chat_id, text)

        # Register channel post handler for admin commands
        app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.TEXT, channel_post_callback))
        
        # Start shared polling loop
        await _start_shared_app()

    async def stop(self) -> None:
        await _stop_shared_app()
