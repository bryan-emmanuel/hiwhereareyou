import os
import json
import logging
from threading import Lock
from src.core.interfaces import PlayerRegistry

logger = logging.getLogger(__name__)

class JSONPlayerRegistry(PlayerRegistry):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._lock = Lock()
        self._players = set()
        self._load_registry()

    def _load_registry(self) -> None:
        with self._lock:
            # Create parent directories if they don't exist
            parent_dir = os.path.dirname(self.filepath)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            if not os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "w", encoding="utf-8") as f:
                        json.dump([], f)
                    self._players = set()
                except Exception as e:
                    logger.error(f"Failed to create empty registry file at {self.filepath}: {e}")
                return

            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._players = set(data)
                logger.info(f"Loaded {len(self._players)} registered players from {self.filepath}.")
            except Exception as e:
                logger.error(f"Failed to read player registry from {self.filepath}: {e}")
                self._players = set()

    def _save_registry_unlocked(self) -> None:
        """Saves current players set to disk (assumes lock is already acquired)."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(list(self._players), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write player registry to {self.filepath}: {e}")

    def register_player(self, player_id: str) -> None:
        with self._lock:
            if player_id not in self._players:
                self._players.add(player_id)
                self._save_registry_unlocked()
                logger.info(f"Successfully registered and saved player: {player_id}")

    def is_player_registered(self, player_id: str) -> bool:
        with self._lock:
            return player_id in self._players

    def remove_player(self, player_id: str) -> None:
        with self._lock:
            if player_id in self._players:
                self._players.remove(player_id)
                self._save_registry_unlocked()
                logger.info(f"Successfully removed player from allowlist: {player_id}")

    def get_all_players(self) -> list[str]:
        with self._lock:
            return list(self._players)

    def reset_registry(self) -> None:
        with self._lock:
            self._players.clear()
            self._save_registry_unlocked()
            logger.info("Cleared all players from the allowlist.")
