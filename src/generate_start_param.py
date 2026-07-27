import sys
import argparse
from src.providers.yaml_config import YAMLConfigProvider
from src.core.utils import format_phone_number, calculate_parameter_hash

def main():
    parser = argparse.ArgumentParser(description="Admin tool to generate a player's first starting token and link.")
    parser.add_argument("player_id", help="Player ID (phone number or Telegram ID/username)")
    parser.add_argument("--config", default="config/config.yml", help="Path to config.yml file")
    parser.add_argument(
        "--platform", 
        choices=["telegram", "twilio"], 
        default="telegram", 
        help="Target platform (telegram or twilio)"
    )
    args = parser.parse_args()

    # Load configuration
    config_provider = YAMLConfigProvider(args.config)
    try:
        config = config_provider.get_game_config()
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)

    # Standardize player address if it looks like a phone number
    player_id = args.player_id.strip()
    if player_id.startswith("+") or player_id.isdigit() or ("-" in player_id) or ("(" in player_id):
        try:
            standardized = format_phone_number(player_id)
            print(f"📞 Standardized phone number: {player_id} -> {standardized}")
            player_id = standardized
        except Exception as e:
            print(f"⚠️ Failed to standardize phone number format: {e}")

    # Calculate token: sha256(salt + "start" + player_id)[:16]
    start_token = calculate_parameter_hash(config.salt, config.start_param, player_id)
    
    print("\n==========================================")
    print(f"👤 Player ID:     {player_id}")
    print(f"🔑 Start Token:   {start_token}")
    
    if args.platform == "telegram":
        link = f"https://t.me/{config.telegram_bot_username}?start={start_token}"
        print(f"📱 Telegram Link: {link}")
    else:
        link = f"sms:{config.twilio_phone_number}?body={start_token}"
        print(f"📱 Twilio Link:   {link}")
    print("==========================================\n")

if __name__ == "__main__":
    main()
