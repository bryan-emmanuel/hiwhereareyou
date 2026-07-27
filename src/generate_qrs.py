import os
import argparse
from src.providers.yaml_config import YAMLConfigProvider
from src.providers.qr_generator import QRCodeGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate QR codes linking directly to Telegram or Twilio.")
    parser.add_argument("--config", default="config/config.yml", help="Path to config.yml file")
    parser.add_argument("--outdir", default="qrs", help="Directory to save generated QR code images")
    parser.add_argument(
        "--platform", 
        choices=["telegram", "twilio"], 
        default="telegram", 
        help="Target platform for direct deep links (telegram or twilio)"
    )
    args = parser.parse_args()

    # Load configuration
    config_provider = YAMLConfigProvider(args.config)
    try:
        config = config_provider.get_game_config()
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return

    qr_generator = QRCodeGenerator()
    os.makedirs(args.outdir, exist_ok=True)

    print(f"📱 Generating QR codes for platform: {args.platform.upper()}\n")

    # Generate Location QR codes
    print("📍 Generating Location QR codes:")
    for idx, loc in enumerate(config.locations, 1):
        if args.platform == "telegram":
            loc_url = f"https://t.me/{config.telegram_bot_username}?start={loc.id}"
        else:
            loc_url = f"sms:{config.twilio_phone_number}?body={loc.id}"

        loc_filename = f"{idx:02d}_{loc.id}.png"
        loc_path = os.path.join(args.outdir, loc_filename)
        
        print(f"   [{idx}/{len(config.locations)}] {loc.name} ({loc.id})")
        print(f"   Link: {loc_url}")
        print(f"   Path: {loc_path}")
        
        qr_bytes = qr_generator.generate_qr_code(loc_url)
        with open(loc_path, "wb") as f:
            f.write(qr_bytes)

    print(f"\n🎉 Success! All QR codes generated in: {os.path.abspath(args.outdir)}")

if __name__ == "__main__":
    main()
