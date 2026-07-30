import os
import yaml
from src.core.interfaces import ConfigProvider
from src.core.models import GameConfig, Location

class YAMLConfigProvider(ConfigProvider):
    def __init__(self, config_path: str):
        self.config_path = config_path

    def get_game_config(self) -> GameConfig:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
            
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        telegram_data = data.get("telegram", {})
        twilio_data = data.get("twilio", {})
        game_data = data.get("game", {})
        locations_data = data.get("locations", [])

        # 1. Telegram settings (with environment overrides)
        telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", telegram_data.get("bot_token", ""))
        telegram_bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", telegram_data.get("bot_username", ""))
        telegram_master_admin_id = os.environ.get("TELEGRAM_MASTER_ADMIN_ID", telegram_data.get("master_admin_id", ""))

        # 2. Twilio settings (with environment overrides)
        twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID", twilio_data.get("account_sid", ""))
        twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN", twilio_data.get("auth_token", ""))
        twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER", twilio_data.get("phone_number", ""))
        
        twilio_webhook_host = os.environ.get("TWILIO_WEBHOOK_HOST", twilio_data.get("webhook_host", "0.0.0.0"))
        
        try:
            twilio_webhook_port = int(os.environ.get("TWILIO_WEBHOOK_PORT", twilio_data.get("webhook_port", 5000)))
        except ValueError:
            twilio_webhook_port = 5000

        # 3. Game settings
        start_param = game_data.get("start_param", "start")
        start_message = game_data.get("start_message", "")
        final_message = game_data.get("final_message", "")

        locations = []
        for loc in locations_data:
            locations.append(
                Location(
                    id=str(loc.get("id", "")),
                    name=str(loc.get("name", "")),
                    clue=str(loc.get("clue", ""))
                )
            )

        return GameConfig(
            telegram_bot_token=telegram_bot_token,
            telegram_bot_username=telegram_bot_username,
            telegram_master_admin_id=telegram_master_admin_id,
            twilio_account_sid=twilio_account_sid,
            twilio_auth_token=twilio_auth_token,
            twilio_phone_number=twilio_phone_number,
            twilio_webhook_host=twilio_webhook_host,
            twilio_webhook_port=twilio_webhook_port,
            start_param=start_param,
            start_message=start_message,
            final_message=final_message,
            locations=locations
        )
