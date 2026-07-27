import pytest
from typing import List, Tuple, Union, Optional, Callable
from src.core.interfaces import ConfigProvider, PlayerMessagingService, AdminNotificationService, PlayerRegistry
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
        self._handler = None
        self.sent_logs: List[str] = []
        self.sent_media: List[Tuple[str, str]] = []

    def set_inbound_handler(self, handler: Callable) -> None:
        self._handler = handler

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
        self.reset_called = False

    def register_player(self, player_id: str) -> None:
        self.active_players.add(player_id)

    def is_player_registered(self, player_id: str) -> bool:
        return player_id in self.active_players

    def reset_registry(self) -> None:
        self.active_players.clear()
        self.reset_called = True

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
async def test_location_solve_unregistered_fails(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_address = "+15559999"
    # Unregistered player tries to scan Location 1 directly
    await player_messaging._handler(player_address, "loc1_abc")

    # Output message should be ignored outright (no message sent)
    assert len(player_messaging.sent_messages) == 0
    assert not player_registry.is_player_registered("+15559999")

@pytest.mark.asyncio
async def test_admin_generate_registers_and_confirms(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    # Admin registers a player
    await admin_notification._handler("admin_chat", "generate +15559999")

    # Verify player registered
    assert player_registry.is_player_registered("+15559999")
    
    # Simple confirmation reply back to admin
    assert len(admin_notification.sent_logs) == 1
    assert "Player/Group +15559999 registered successfully!" in admin_notification.sent_logs[0]

@pytest.mark.asyncio
async def test_registered_player_starts_game(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_address = "+15559999"
    player_registry.register_player("+15559999")

    # Registered player starts
    await player_messaging._handler(player_address, "start")

    assert len(player_messaging.sent_messages) == 1
    assert "Welcome! First Clue: Solve clue one" in player_messaging.sent_messages[0][1]

@pytest.mark.asyncio
async def test_location_solve_registered_player(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_address = "+15559999"
    player_registry.register_player("+15559999")

    # Solve Location 1
    await player_messaging._handler(player_address, "loc1_abc")

    assert len(player_messaging.sent_messages) == 1
    assert "*Location Found:* Location One" in player_messaging.sent_messages[0][1]
    assert "Solve clue two" in player_messaging.sent_messages[0][1]

@pytest.mark.asyncio
async def test_invalid_location_solve_ignored(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_address = "+15559999"
    player_registry.register_player("+15559999")

    # Send incorrect code
    await player_messaging._handler(player_address, "loc1_wrong")

    assert len(player_messaging.sent_messages) == 0

@pytest.mark.asyncio
async def test_admin_help_command(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    await admin_notification._handler("admin_chat", "help")

    assert len(admin_notification.sent_logs) == 1
    assert "Administrator Functions" in admin_notification.sent_logs[0]

@pytest.mark.asyncio
async def test_admin_reset_command(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    player_registry.register_player("+15559999")
    assert player_registry.is_player_registered("+15559999")

    await admin_notification._handler("admin_chat", "reset")

    assert player_registry.reset_called
    assert not player_registry.is_player_registered("+15559999")
    
    assert len(admin_notification.sent_logs) == 1
    assert "Registry Reset Successful" in admin_notification.sent_logs[0]

@pytest.mark.asyncio
async def test_photo_submission_gating(sample_config):
    config_provider = MockConfigProvider(sample_config)
    player_messaging = MockPlayerMessaging()
    admin_notification = MockAdminNotification()
    player_registry = MockPlayerRegistry()
    engine = ScavengerHuntEngine(config_provider, player_messaging, admin_notification, player_registry)

    # 1. Unregistered photo submission -> Ignored
    await player_messaging._handler("+15559999", "", "photo_url_abc")
    assert len(admin_notification.sent_media) == 0
    assert len(player_messaging.sent_messages) == 0

    # 2. Registered photo submission -> Accepted & Forwarded
    player_registry.register_player("+15559999")
    await player_messaging._handler("+15559999", "", "photo_url_abc")

    assert len(admin_notification.sent_media) == 1
    assert admin_notification.sent_media[0][0] == "photo_url_abc"
    assert len(player_messaging.sent_messages) == 1
    assert "*Photo received!*" in player_messaging.sent_messages[0][1]
