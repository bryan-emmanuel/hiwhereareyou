import pytest
from typing import List, Tuple, Union, Optional
from src.core.interfaces import ConfigProvider, PlayerMessagingService, AdminNotificationService
from src.core.models import GameConfig, Location
from src.core.engine import ScavengerHuntEngine

class MockConfigProvider(ConfigProvider):
    def __init__(self, config: GameConfig):
        self._config = config

    def get_game_config(self) -> GameConfig:
        return self._config

class MockPlayerMessaging(PlayerMessagingService):
    def __init__(self):
        self._handler = None
        self.sent_messages: List[Tuple[str, str]] = []

    def set_inbound_handler(self, handler) -> None:
        self._handler = handler

    async def send_message(self, player_address: str, text: str) -> None:
        self.sent_messages.append((player_address, text))

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

class MockAdminNotification(AdminNotificationService):
    def __init__(self):
        self.sent_logs: List[str] = []
        self.sent_media: List[Tuple[str, str]] = []

    async def notify_text(self, text: str) -> None:
        self.sent_logs.append(text)

    async def notify_media(self, media_identifier: str, caption: str) -> None:
        self.sent_media.append((media_identifier, caption))

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

@pytest.fixture
def sample_config() -> GameConfig:
    return GameConfig(
        telegram_bot_token="test_telegram_token",
        telegram_bot_username="test_telegram_bot",
        telegram_admin_channel_id="test_admin_channel",
        twilio_account_sid="test_twilio_sid",
        twilio_auth_token="test_twilio_token",
        twilio_phone_number="+15551111",
        twilio_admin_phone_number="+15552222",
        twilio_webhook_host="0.0.0.0",
        twilio_webhook_port=5000,
        start_param="start",
        start_message="Welcome! First Clue: {clue}",
        final_message="You finished the hunt!",
        locations=[
            Location(id="loc1_abc", name="Location One", clue="Solve clue one"),
            Location(id="loc2_def", name="Location Two", clue="Solve clue two"),
            Location(id="loc3_ghi", name="Location Three", clue="Solve clue three")
        ]
    )

@pytest.mark.asyncio
async def test_start_command_seed(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification)

    # Simulate player sending the start command/seed
    await player_messaging._handler("+15550000", "start")
    
    assert len(player_messaging.sent_messages) == 1
    player_address, text = player_messaging.sent_messages[0]
    assert player_address == "+15550000"
    assert "Welcome! First Clue: Solve clue one" in text

@pytest.mark.asyncio
async def test_start_command_no_param(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification)

    # Simulate empty parameter
    await player_messaging._handler("+15550000", "")

    assert len(player_messaging.sent_messages) == 1
    player_address, text = player_messaging.sent_messages[0]
    assert player_address == "+15550000"
    assert "Welcome! To start the Scavenger Hunt" in text

@pytest.mark.asyncio
async def test_start_command_invalid_param(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification)

    # Simulate incorrect parameter scan
    await player_messaging._handler("+15550000", "invalid_param")

    assert len(player_messaging.sent_messages) == 1
    player_address, text = player_messaging.sent_messages[0]
    assert player_address == "+15550000"
    assert "Invalid code scanned" in text

@pytest.mark.asyncio
async def test_start_command_solve_mid_game(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification)

    # Solve first location (loc1_abc)
    await player_messaging._handler("+15550000", "loc1_abc")

    assert len(player_messaging.sent_messages) == 1
    player_address, text = player_messaging.sent_messages[0]
    assert player_address == "+15550000"
    assert "*Location Found:* Location One" in text
    assert "Solve clue two" in text  # Displays Clue 2

@pytest.mark.asyncio
async def test_start_command_solve_final(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification)

    # Solve final location (loc3_ghi)
    await player_messaging._handler("+15550000", "loc3_ghi")

    # Verify player received final completion message
    assert len(player_messaging.sent_messages) == 1
    player_address, text = player_messaging.sent_messages[0]
    assert player_address == "+15550000"
    assert "*Final Location Found:* Location Three!" in text
    assert "You finished the hunt!" in text

    # Verify administrators received completion log
    assert len(admin_notification.sent_logs) == 1
    assert "completed the scavenger hunt!" in admin_notification.sent_logs[0]

@pytest.mark.asyncio
async def test_photo_submission(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification)

    # Simulate player sending a photo
    await player_messaging._handler("+15550000", "", "photo_123_url")

    # Verify player received photo receipt confirmation
    assert len(player_messaging.sent_messages) == 1
    player_address, text = player_messaging.sent_messages[0]
    assert player_address == "+15550000"
    assert "*Photo received!*" in text

    # Verify administrators received the media submission
    assert len(admin_notification.sent_media) == 1
    media_id, caption = admin_notification.sent_media[0]
    assert media_id == "photo_123_url"
    assert "+15550000" in caption
