import pytest
from typing import List, Tuple, Union, Optional
from src.core.interfaces import ConfigProvider, PlayerMessagingService, AdminNotificationService, PlayerRegistry
from src.core.models import GameConfig, Location
from src.core.engine import ScavengerHuntEngine
from src.core.utils import calculate_parameter_hash

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

class MockPlayerRegistry(PlayerRegistry):
    def __init__(self):
        self.active_players = set()

    def register_player(self, player_id: str) -> None:
        self.active_players.add(player_id)

    def is_player_registered(self, player_id: str) -> bool:
        return player_id in self.active_players

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
        salt="test_salt_key_123",
        redirect_host="0.0.0.0",
        redirect_port=8080,
        redirect_base_url="http://localhost:8080",
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
async def test_location_solve_unregistered_fails(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_address = "+15559999"
    # Unregistered player tries to scan Location 1 directly
    loc1_hash = calculate_parameter_hash(sample_config.salt, "loc1_abc", "+15559999")
    
    await player_messaging._handler(player_address, loc1_hash)

    # Output message should be ignored outright (no message sent)
    assert len(player_messaging.sent_messages) == 0
    assert not player_registry.is_player_registered("+15559999")

@pytest.mark.asyncio
async def test_start_command_registers_player(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_address = "+15559999"
    # Correct start hash prefilled for this player phone number
    start_hash = calculate_parameter_hash(sample_config.salt, "start", "+15559999")

    await player_messaging._handler(player_address, start_hash)

    # Verify player registered
    assert player_registry.is_player_registered("+15559999")
    
    assert len(player_messaging.sent_messages) == 1
    addr, text = player_messaging.sent_messages[0]
    assert addr == player_address
    assert "Welcome! First Clue: Solve clue one" in text

@pytest.mark.asyncio
async def test_start_command_wrong_start_hash(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_address = "+15559999"
    # Sending another player's start hash
    wrong_start_hash = calculate_parameter_hash(sample_config.salt, "start", "+15558888")

    await player_messaging._handler(player_address, wrong_start_hash)

    # Invalid start hash should be ignored outright
    assert not player_registry.is_player_registered("+15559999")
    assert len(player_messaging.sent_messages) == 0

@pytest.mark.asyncio
async def test_location_solve_registered_player(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_address = "+15559999"
    # Register the player first
    player_registry.register_player("+15559999")

    # Solve Location 1
    loc1_hash = calculate_parameter_hash(sample_config.salt, "loc1_abc", "+15559999")
    await player_messaging._handler(player_address, loc1_hash)

    assert len(player_messaging.sent_messages) == 1
    addr, text = player_messaging.sent_messages[0]
    assert addr == player_address
    assert "*Location Found:* Location One" in text
    assert "Solve clue two" in text

@pytest.mark.asyncio
async def test_location_solve_sharing_hash_abuse_fails(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    # Register Player A (+15559999) and Player B (+15558888)
    player_registry.register_player("+15559999")
    player_registry.register_player("+15558888")

    # Player A solves Location 1, gets hash A
    # Player A shares hash A with Player B. Player B submits hash A:
    hash_a = calculate_parameter_hash(sample_config.salt, "loc1_abc", "+15559999")
    
    await player_messaging._handler("+15558888", hash_a)

    # Verification: Player B should be ignored outright because hash A is invalid for Player B
    assert len(player_messaging.sent_messages) == 0

@pytest.mark.asyncio
async def test_photo_submission_unregistered_rejected(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    # Unregistered player sends a photo
    await player_messaging._handler("+15559999", "", "photo_url_abc")

    # Photo should be ignored outright
    assert len(admin_notification.sent_media) == 0
    assert len(player_messaging.sent_messages) == 0

@pytest.mark.asyncio
async def test_photo_submission_registered_accepted(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    # Register player first
    player_registry.register_player("+15559999")

    # Registered player sends a photo
    await player_messaging._handler("+15559999", "", "photo_url_abc")

    # Admins should receive it
    assert len(admin_notification.sent_media) == 1
    assert admin_notification.sent_media[0][0] == "photo_url_abc"
    assert "+15559999" in admin_notification.sent_media[0][1]

    # Player gets confirmation
    assert len(player_messaging.sent_messages) == 1
    assert "*Photo received!*" in player_messaging.sent_messages[0][1]
