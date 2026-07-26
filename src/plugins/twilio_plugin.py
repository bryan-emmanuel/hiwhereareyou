import logging
import asyncio
from typing import Optional, Union
from twilio.rest import Client
from aiohttp import web
from src.core.interfaces import PlayerMessagingService, AdminNotificationService
from src.core.models import GameConfig

logger = logging.getLogger(__name__)

class TwilioPlayerMessaging(PlayerMessagingService):
    def __init__(self):
        self._handler: Optional[callable] = None
        self.config: Optional[GameConfig] = None
        self.client: Optional[Client] = None
        self._runner: Optional[web.AppRunner] = None

    def initialize(self, config: GameConfig) -> None:
        """Initialize with build-time config."""
        self.config = config
        self.client = Client(config.twilio_account_sid, config.twilio_auth_token)

    def set_inbound_handler(self, handler: callable) -> None:
        self._handler = handler

    async def send_message(self, player_address: str, text: str) -> None:
        if not self.client or not self.config:
            raise RuntimeError("TwilioPlayerMessaging is not initialized.")
        
        # SMS does not support Markdown formatting. Strip it out.
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

        # Set up standard aiohttp server for receiving webhooks from Twilio
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
        logger.info(f"Twilio Webhook HTTP Server started on http://{self.config.twilio_webhook_host}:{self.config.twilio_webhook_port}/webhook")

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            logger.info("Twilio Player Messaging listener stopped.")

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """
        Receives standard application/x-www-form-urlencoded POST requests from Twilio.
        """
        try:
            data = await request.post()
            sender = data.get("From", "")
            body = data.get("Body", "")
            
            # Twilio specifies media in MediaUrl0, MediaUrl1 etc.
            num_media = int(data.get("NumMedia", 0))
            media_url = data.get("MediaUrl0", None) if num_media > 0 else None
            
            logger.info(f"Twilio Webhook: From='{sender}', Body='{body}', MediaUrl='{media_url}'")
            
            if self._handler:
                # Forward to Scavenger Hunt core game logic
                await self._handler(sender, body, media_url)
                
        except Exception as e:
            logger.error(f"Error handling Twilio webhook: {e}")
            
        # Return an empty TwiML response
        return web.Response(text="<Response></Response>", content_type="application/xml")


class TwilioAdminNotification(AdminNotificationService):
    def __init__(self):
        self.config: Optional[GameConfig] = None
        self.client: Optional[Client] = None

    def initialize(self, config: GameConfig) -> None:
        """Initialize with build-time config."""
        self.config = config
        self.client = Client(config.twilio_account_sid, config.twilio_auth_token)

    async def notify_text(self, text: str) -> None:
        if not self.client or not self.config:
            raise RuntimeError("TwilioAdminNotification is not initialized.")
        
        # SMS does not support Markdown formatting
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
            # Twilio media_url must be a list of strings
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
