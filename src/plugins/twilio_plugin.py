import logging
import asyncio
from typing import Optional, Set
from twilio.rest import Client
from src.core.interfaces import PlayerMessagingService, AdminNotificationService
from src.core.models import GameConfig

logger = logging.getLogger(__name__)

class TwilioPlayerMessaging(PlayerMessagingService):
    def __init__(self):
        self._handler: Optional[callable] = None
        self.config: Optional[GameConfig] = None
        self.client: Optional[Client] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._seen_sids: Set[str] = set()

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

        # Pre-fill seen_sids with recent messages so we don't re-process old texts on startup
        try:
            logger.info("Initializing Twilio API Poller...")
            recent_msgs = await asyncio.to_thread(
                self.client.messages.list,
                to=self.config.twilio_phone_number,
                limit=50
            )
            for msg in recent_msgs:
                self._seen_sids.add(msg.sid)
            logger.info(f"Seeded Twilio poller with {len(self._seen_sids)} historical message SIDs.")
        except Exception as e:
            logger.error(f"Failed to seed Twilio poller: {e}")

        self._polling_task = asyncio.create_task(self._poll_messages())
        logger.info("Twilio API Polling Service started.")

    async def stop(self) -> None:
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        logger.info("Twilio API Polling Service stopped.")

    async def _poll_messages(self) -> None:
        """Continuously polls Twilio for new inbound SMS."""
        while True:
            try:
                # Fetch recent messages sent TO our number
                messages = await asyncio.to_thread(
                    self.client.messages.list,
                    to=self.config.twilio_phone_number,
                    limit=10
                )
                
                # Process oldest to newest in the batch
                for msg in reversed(messages):
                    if msg.sid not in self._seen_sids:
                        self._seen_sids.add(msg.sid)
                        
                        media_url = None
                        if int(msg.num_media) > 0:
                            # Fetch media details
                            media_list = await asyncio.to_thread(msg.media.list)
                            if media_list:
                                media_url = f"https://api.twilio.com{media_list[0].uri}".replace(".json", "")
                                
                        logger.info(f"Twilio API Poll: New message from='{msg.from_}', Body='{msg.body}', MediaUrl='{media_url}'")
                        
                        if self._handler:
                            await self._handler(msg.from_, msg.body, media_url)
                            
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error polling Twilio API: {e}")
                
            # Wait 3 seconds before polling again
            await asyncio.sleep(3)
