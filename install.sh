#!/bin/bash
# FFXIV Discord Bot installation script
# Run this script as a user with sudo privileges

set -e

# Configuration
APP_DIR="/opt/ffxiv-discord-bot"
BOT_USER="ffxiv-bot"
BOT_GROUP="ffxiv-bot"
LOG_DIR="/var/log/ffxiv-bot"
SYSTEMD_DIR="/etc/systemd/system"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== FFXIV Discord Bot Installation =====${NC}"

# Check for sudo privileges
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run this script with sudo privileges.${NC}"
  exit 1
fi

# Create user and group if they don't exist
echo -e "${YELLOW}Creating bot user and group...${NC}"
if ! id -u "$BOT_USER" &>/dev/null; then
    useradd -r -m -d "$APP_DIR" -s /bin/bash "$BOT_USER"
    echo -e "${GREEN}User $BOT_USER created.${NC}"
else
    echo -e "${YELLOW}User $BOT_USER already exists.${NC}"
fi

# Install system dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib redis-server supervisor

# Create application directory if it doesn't exist
echo -e "${YELLOW}Setting up application directory...${NC}"
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Copy application files to the destination directory
echo -e "${YELLOW}Copying application files...${NC}"
cp -r $SCRIPT_DIR/* "$APP_DIR/"
cp $SCRIPT_DIR/systemd/ffxiv-bot.service "$SYSTEMD_DIR/"

# Create Python virtual environment and install dependencies
echo -e "${YELLOW}Setting up Python environment...${NC}"
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Set up the database
echo -e "${YELLOW}Setting up PostgreSQL database...${NC}"
# Check if PostgreSQL service is running
systemctl is-active --quiet postgresql || systemctl start postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER ffxiv_bot WITH PASSWORD 'password';" || true
sudo -u postgres psql -c "CREATE DATABASE ffxiv_bot OWNER ffxiv_bot;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ffxiv_bot TO ffxiv_bot;" || true

# Run database setup script
echo -e "${YELLOW}Creating database tables...${NC}"
cd "$APP_DIR"
source venv/bin/activate
python setup_db.py

# Set proper permissions
echo -e "${YELLOW}Setting permissions...${NC}"
chown -R "$BOT_USER":"$BOT_GROUP" "$APP_DIR"
chown -R "$BOT_USER":"$BOT_GROUP" "$LOG_DIR"
chmod -R 755 "$APP_DIR"
chmod -R 755 "$LOG_DIR"

# Enable and start the service
echo -e "${YELLOW}Enabling and starting service...${NC}"
systemctl daemon-reload
systemctl enable ffxiv-bot.service
systemctl start ffxiv-bot.service

echo -e "${GREEN}===== Installation Complete =====${NC}"
echo -e "${YELLOW}IMPORTANT: Edit /etc/systemd/system/ffxiv-bot.service to add your Discord token and other configuration.${NC}"
echo -e "${YELLOW}Then restart the service: sudo systemctl restart ffxiv-bot.service${NC}"
echo -e "${GREEN}===== Enjoy your FFXIV Discord Bot! =====${NC}"