#!/data/data/com.termux/files/usr/bin/bash
# hiwhereareyou Node Onboarding Script
# This script is executed on a fresh Termux installation to prepare it for node duty.

set -e

LOG_FILE="$HOME/onboarding.log"
echo "--- Starting Node Onboarding: $(date) ---" | tee -a "$LOG_FILE"

# 1. Update Termux Packages
echo "Updating packages..." | tee -a "$LOG_FILE"
export DEBIAN_FRONTEND=noninteractive
pkg update -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" | tee -a "$LOG_FILE"
pkg upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" | tee -a "$LOG_FILE"

# 2. Install Core Dependencies
echo "Installing core dependencies..." | tee -a "$LOG_FILE"
pkg install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" git python clang make libffi openssl build-essential procps termux-api termux-services | tee -a "$LOG_FILE"

# 3. Setup Project Directory
echo "Setting up project directory..." | tee -a "$LOG_FILE"
HOME_DIR="/data/data/com.termux/files/home"
PROJECT_DIR="$HOME_DIR/hiwhereareyou"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Copying repository from local source..." | tee -a "$LOG_FILE"
    mkdir -p "$PROJECT_DIR"
    tar -xzf /sdcard/Download/hiwhereareyou_source.tar.gz -C "$PROJECT_DIR" | tee -a "$LOG_FILE"
else
    echo "Project directory already exists. Updating from local source..." | tee -a "$LOG_FILE"
    tar -xzf /sdcard/Download/hiwhereareyou_source.tar.gz -C "$PROJECT_DIR" | tee -a "$LOG_FILE"
fi

cd "$PROJECT_DIR"

# 4. Create Virtual Environment
echo "Setting up Python virtual environment..." | tee -a "$LOG_FILE"
if [ ! -d "venv" ]; then
    python -m venv venv | tee -a "$LOG_FILE"
fi

# 5. Install Python Dependencies
echo "Installing Python dependencies..." | tee -a "$LOG_FILE"
./venv/bin/pip install --upgrade pip | tee -a "$LOG_FILE"
if [ -f "requirements.txt" ]; then
    ./venv/bin/pip install -r requirements.txt | tee -a "$LOG_FILE"
fi
# Ensure python-dotenv is available for loading environment variables
./venv/bin/pip install python-dotenv requests | tee -a "$LOG_FILE"

# 6. Setup Autonomous Boot
echo "Setting up autonomous boot..." | tee -a "$LOG_FILE"
BOOT_DIR="/data/data/com.termux/files/home/.termux/boot"
mkdir -p "$BOOT_DIR"
cat <<EOF > "$BOOT_DIR/start-hiwhereareyou.sh"
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd /data/data/com.termux/files/home/hiwhereareyou && sh start.sh
EOF
chmod +x "$BOOT_DIR/start-hiwhereareyou.sh"

echo "--- Onboarding Complete ---" | tee -a "$LOG_FILE"
echo "You can now start the app with: sh start.sh" | tee -a "$LOG_FILE"
cp "$LOG_FILE" /sdcard/Download/hiwhereareyou_onboarding.log || echo "Warning: Could not copy log to /sdcard"
