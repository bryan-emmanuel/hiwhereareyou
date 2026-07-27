import os
import argparse
from src.providers.yaml_config import YAMLConfigProvider
from src.providers.qr_generator import QRCodeGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate QR codes pointing to the Redirect Web Server.")
    parser.add_argument("--config", default="config/config.yml", help="Path to config.yml file")
    parser.add_argument("--outdir", default="qrs", help="Directory to save generated QR code images")
    args = parser.parse_args()

    # Load configuration
    config_provider = YAMLConfigProvider(args.config)
    try:
        config = config_provider.get_game_config()
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return

    redirect_base = config.redirect_base_url.rstrip("/")
    if not redirect_base or "YOUR_REDIRECT_BASE_URL" in redirect_base:
        print("⚠️ Warning: game.redirect_base_url is unset in config.yml. Defaulting to http://localhost:8080")
        redirect_base = "http://localhost:8080"

    qr_generator = QRCodeGenerator()
    os.makedirs(args.outdir, exist_ok=True)

    print(f"🌐 Generating QR codes pointing to Redirect Server: {redirect_base}\n")

    # 1. Start Seed QR code
    seed_url = f"{redirect_base}/scan/{config.start_param}"
    seed_path = os.path.join(args.outdir, "00_start_seed.png")
    print(f"📱 Generating Start Seed QR code:")
    print(f"   Link: {seed_url}")
    print(f"   Path: {seed_path}")
    
    seed_qr_bytes = qr_generator.generate_qr_code(seed_url)
    with open(seed_path, "wb") as f:
        f.write(seed_qr_bytes)

    # 2. Location QR codes
    print("\n📍 Generating Location QR codes:")
    for idx, loc in enumerate(config.locations, 1):
        loc_url = f"{redirect_base}/scan/{loc.id}"
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
