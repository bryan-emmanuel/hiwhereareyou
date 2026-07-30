from dataclasses import dataclass
from typing import List, Union

@dataclass
class Location:
    id: str
    name: str
    clue: str

@dataclass
class GameConfig:
    # Telegram-specific parameters
    telegram_bot_token: str
    telegram_bot_username: str
    telegram_master_admin_id: str
    
    # Twilio-specific parameters
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    twilio_webhook_host: str
    twilio_webhook_port: int
    
    # Core Game logic parameters
    final_message: str
    locations: List[Location]
