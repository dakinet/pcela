#!/bin/bash
# TVI Bee server setup — pokrenuti jednom na svežem Debian 12 LXC-u
set -e

echo "=== TVI Bee setup ==="

# 1. System packages
apt-get update -q
apt-get install -y python3 python3-pip python3-venv curl

# 2. Korisnik
useradd -r -m -d /opt/tvi-bee -s /bin/bash tvi 2>/dev/null || true

# 3. App direktorijum
mkdir -p /opt/tvi-bee/projects /opt/tvi-bee/exports
chown -R tvi:tvi /opt/tvi-bee

# 4. Python venv + dependencies
sudo -u tvi python3 -m venv /opt/tvi-bee/venv
sudo -u tvi /opt/tvi-bee/venv/bin/pip install -q --upgrade pip
sudo -u tvi /opt/tvi-bee/venv/bin/pip install -q \
    fastapi uvicorn websocket-client python-dotenv openpyxl

# 5. Systemd servis
cp /tmp/tvi-bee.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable tvi-bee

# 6. Cloudflare tunnel
if ! command -v cloudflared &>/dev/null; then
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloudflare-main.gpg
    echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
        https://pkg.cloudflare.com/cloudflared bookworm main" \
        > /etc/apt/sources.list.d/cloudflared.list
    apt-get update -q && apt-get install -y cloudflared
fi

echo ""
echo "=== Setup završen ==="
echo "Sledeći koraci:"
echo "  1. scp fajlove na server (pokreni deploy.bat sa Windows mašine)"
echo "  2. systemctl start tvi-bee"
echo "  3. cloudflared tunnel --url http://localhost:7000"
