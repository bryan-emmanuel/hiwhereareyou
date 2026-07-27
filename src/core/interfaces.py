from abc import ABC, abstractmethod
from typing import Callable, Coroutine, Optional, Union
from src.core.models import GameConfig

# Callback type for players: (player_address, text_content, optional_media_url_or_id)
PlayerInboundHandler = Callable[[str, str, Optional[str]], Coroutine[None, None, None]]

# Callback type for administrators: (admin_address, text_content)
AdminInboundHandler = Callable[[str, str], Coroutine[None, None, None]]

class ConfigProvider(ABC):
    @abstractmethod
    def get_game_config(self) -> GameConfig:
        """Loads and returns the game configuration."""
        pass

class PlayerMessagingService(ABC):
    @abstractmethod
    def set_inbound_handler(self, handler: PlayerInboundHandler) -> None:
        """
        Registers the game engine callback for player messages.
        Whenever a player sends a message or media, the plugin must invoke this callback.
        """
        pass

    @abstractmethod
    async def send_message(self, player_address: str, text: str) -> None:
        """Sends a text message to a specific player's address (chat ID, phone, etc.)."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Starts the player messaging client listener loop or webhook server."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops the player messaging listener loop or server."""
        pass

class AdminNotificationService(ABC):
    @abstractmethod
    def set_inbound_handler(self, handler: AdminInboundHandler) -> None:
        """
        Registers the game engine callback for administrator commands/messages.
        Whenever an administrator sends a command, the plugin must invoke this callback.
        """
        pass

    @abstractmethod
    async def notify_text(self, text: str) -> None:
        """Sends a text notification/reply to the game administrators' channel/address."""
        pass

    @abstractmethod
    async def notify_media(self, media_identifier: str, caption: str) -> None:
        """Sends a photo/media notification with a caption to the game administrators."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Initializes and connects the admin notification client/channel."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Disconnects the admin notification client."""
        pass

class PlayerRegistry(ABC):
    @abstractmethod
    def register_player(self, player_id: str) -> None:
        """Saves a player ID to the registry (in memory and persisted to disk)."""
        pass

    @abstractmethod
    def is_player_registered(self, player_id: str) -> bool:
        """Returns True if the player is in the registry, False otherwise."""
        pass

    @abstractmethod
    def reset_registry(self) -> None:
        """Clears all players from the registry (memory and disk)."""
        pass

class QRProvider(ABC):
    @abstractmethod
    def generate_qr_code(self, data: str) -> bytes:
        """Generates a QR code image as bytes (e.g. PNG) for the given data string."""
        pass
