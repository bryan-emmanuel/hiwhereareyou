import os
import argparse
import urllib.parse
from src.providers.yaml_config import YAMLConfigProvider
from src.providers.qr_generator import QRCodeGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate QR codes for the Scavenger Hunt locations and start seed.")
    parser.add_argument("--config", default="config/config.yml", help="Path to config.yml file")
    parser.add_argument("--outdir", default="qrs", help="Directory to save generated QR code images")
    parser.add_argument(
        "--platform", 
        choices=["telegram", "twilio"], 
        default="telegram", 
        help="Target player communication platform for QR links (default: telegram)"
    )
    args = parser.parse_args()

    # Load configuration
    config_provider = YAMLConfigProvider(args.config)
    try:
        config = config_provider.get_game_config()
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return

    # Determine deep-link builder based on target platform
    qr_generator = QRCodeGenerator()
    os.makedirs(args.outdir, exist_ok=True)

    print(f"🛠 Generating QR codes configured for platform: {args.platform.upper()}\n")

    # 1. Start Seed Link
    if args.platform == "telegram":
        bot_username = config.telegram_bot_username
        if not bot_username or bot_username == "YOUR_BOT_USERNAME":
            print("⚠️ Warning: telegram.bot_username is unset or placeholder in config.yml.")
            bot_username = "PlaceholderBot"
        seed_url = f"https://t.me/{bot_username}?start={config.start_param}"
    else:  # twilio
        phone_num = config.twilio_phone_number
        if not phone_num or phone_num == "+15551234567":
            print("⚠️ Warning: twilio.phone_number is unset or placeholder in config.yml.")
            phone_num = "+15551234567"
        # SMS URI format: sms:+15551234567?body=start
        # Note: spaces/special characters are url-encoded
        encoded_body = urllib.parse.quote(config.start_param)
        seed_url = f"sms:{phone_num}?body={encoded_body}"

    seed_path = os.path.join(args.outdir, "00_start_seed.png")
    print(f"📱 Generating Start Seed QR code:")
    print(f"   Link: {seed_url}")
    print(f"   Path: {seed_path}")
    
    seed_qr_bytes = qr_generator.generate_qr_code(seed_url)
    with open(seed_path, "wb") as f:
        f.write(seed_qr_bytes)

    # 2. Location Links
    print("\n📍 Generating Location QR codes:")
    for idx, loc in enumerate(config.locations, 1):
        if args.platform == "telegram":
            loc_url = f"https://t.me/{bot_username}?start={loc.id}"
        else:  # twilio
            encoded_body = urllib.parse.quote(loc.id)
            loc_url = f"sms:{phone_num}?body={encoded_body}"

        loc_filename = f"{idx:02d}_{loc.id}.png"
        loc_path = os.path.join(args.outdir, loc_filename)
        
        print(f"   [{idx}/{len(config.locations)}] {loc.name} ({loc.id})")
        print(f"   Link: {loc_url}")
        print(f"   Path: {loc_path}")
        
        qr_bytes = qr_generator.generate_qr_code(loc_url)
        with open(loc_path, "wb") as f:
            f.write(qr_bytes)

    print(f"\n🎉 Success! All {args.platform.upper()} QR codes generated in: {os.path.abspath(args.outdir)}")

if __name__ == "__main__":
    main()
