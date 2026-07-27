import logging
import asyncio
from typing import Optional, Union, Callable
from twilio.rest import Client
from aiohttp import web
from src.core.interfaces import PlayerMessagingService, AdminNotificationService
from src.core.models import GameConfig
from src.core.utils import format_phone_number

logger = logging.getLogger(__name__)

# Shared admin handler to route webhook calls from the admin phone number
_shared_admin_handler: Optional[Callable] = None

class TwilioPlayerMessaging(PlayerMessagingService):
    def __init__(self):
        self._handler: Optional[Callable] = None
        self.config: Optional[GameConfig] = None
        self.client: Optional[Client] = None
        self._runner: Optional[web.AppRunner] = None

    def initialize(self, config: GameConfig) -> None:
        self.config = config
        self.client = Client(config.twilio_account_sid, config.twilio_auth_token)

    def set_inbound_handler(self, handler: Callable) -> None:
        self._handler = handler

    async def send_message(self, player_address: str, text: str) -> None:
        if not self.client or not self.config:
            raise RuntimeError("TwilioPlayerMessaging is not initialized.")
        
        # Strip markdown formatting
        clean_text = text.replace("*", "").replace("_", "")
        logger.info(f"Sending Twilio SMS to {player_address}: {clean_text}")
        
        try:
            await asyncio.to_thread(
                self.client.messages.create,
                body=clean_text,
                from_=self.config.twilio_phone_number,
                to=player_address
            )
        except Exception as e:
            logger.error(f"Twilio failed to send SMS to {player_address}: {e}")

    async def start(self) -> None:
        if not self.config:
            raise RuntimeError("TwilioPlayerMessaging is not initialized.")

        app = web.Application()
        app.router.add_post("/webhook", self._handle_webhook)
        
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        
        site = web.TCPSite(
            self._runner,
            self.config.twilio_webhook_host,
            self.config.twilio_webhook_port
        )
        await site.start()
        logger.info(f"Twilio Webhook server running on http://{self.config.twilio_webhook_host}:{self.config.twilio_webhook_port}/webhook")

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            logger.info("Twilio Player Messaging listener stopped.")

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        global _shared_admin_handler
        try:
            data = await request.post()
            raw_sender = data.get("From", "")
            body = data.get("Body", "")
            
            sender = format_phone_number(raw_sender)
            admin_phone = format_phone_number(self.config.twilio_admin_phone_number)

            num_media = int(data.get("NumMedia", 0))
            media_url = data.get("MediaUrl0", None) if num_media > 0 else None

            # Route based on sender ID: if from admin phone, route to admin handler
            if sender == admin_phone:
                logger.info(f"Twilio Webhook: Routing admin command from {sender}: '{body}'")
                if _shared_admin_handler:
                    await _shared_admin_handler(sender, body)
            else:
                logger.info(f"Twilio Webhook: Routing player message from {sender}: body='{body}', media='{media_url}'")
                if self._handler:
                    await self._handler(sender, body, media_url)
                    
        except Exception as e:
            logger.error(f"Error handling Twilio webhook: {e}")
            
        return web.Response(text="<Response></Response>", content_type="application/xml")


class TwilioAdminNotification(AdminNotificationService):
    def __init__(self):
        self._handler: Optional[Callable] = None
        self.config: Optional[GameConfig] = None
        self.client: Optional[Client] = None

    def initialize(self, config: GameConfig) -> None:
        self.config = config
        self.client = Client(config.twilio_account_sid, config.twilio_auth_token)

    def set_inbound_handler(self, handler: Callable) -> None:
        global _shared_admin_handler
        self._handler = handler
        _shared_admin_handler = handler

    async def notify_text(self, text: str) -> None:
        if not self.client or not self.config:
            raise RuntimeError("TwilioAdminNotification is not initialized.")
        
        clean_text = text.replace("*", "").replace("_", "")
        try:
            await asyncio.to_thread(
                self.client.messages.create,
                body=clean_text,
                from_=self.config.twilio_phone_number,
                to=self.config.twilio_admin_phone_number
            )
        except Exception as e:
            logger.error(f"Twilio failed to send admin text: {e}")

    async def notify_media(self, media_identifier: str, caption: str) -> None:
        if not self.client or not self.config:
            raise RuntimeError("TwilioAdminNotification is not initialized.")
        
        clean_caption = caption.replace("*", "").replace("_", "")
        try:
            await asyncio.to_thread(
                self.client.messages.create,
                body=clean_caption,
                from_=self.config.twilio_phone_number,
                to=self.config.twilio_admin_phone_number,
                media_url=[media_identifier]
            )
        except Exception as e:
            logger.error(f"Twilio failed to send admin media: {e}")

    async def start(self) -> None:
        logger.info("Twilio Admin Notification Service started.")

    async def stop(self) -> None:
        logger.info("Twilio Admin Notification Service stopped.")
