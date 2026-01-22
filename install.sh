#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD="$HOME/.config/systemd/user"

echo "🎵 BandcampSync Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Create virtual environment and install Python requirements
echo ""
echo "📦 Setting up Python environment..."
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    python3 -m venv "$SCRIPT_DIR/venv"
    echo "✔ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

source "$SCRIPT_DIR/venv/bin/activate"
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "✔ Python dependencies installed"

# Install Playwright browsers
python3 -m playwright install chromium
echo "✔ Chromium browser installed for Playwright"

# 2. Create systemd user directory
echo ""
echo "🔧 Setting up systemd services..."
mkdir -p "$SYSTEMD"

# 3. Install dashboard service
ln -sf "$SCRIPT_DIR/systemd/bandcamp-dashboard.service" "$SYSTEMD/"
echo "✔ Dashboard service linked"

# 4. Install sync services
ln -sf "$SCRIPT_DIR/Sync/systemd/bandcamp-sync.service"          "$SYSTEMD/"
ln -sf "$SCRIPT_DIR/Sync/systemd/bandcamp-sync.path"             "$SYSTEMD/"
ln -sf "$SCRIPT_DIR/Sync/systemd/bandcamp-sync.timer"            "$SYSTEMD/"
ln -sf "$SCRIPT_DIR/Sync/systemd/bandcamp-sync-worker.service"   "$SYSTEMD/"
ln -sf "$SCRIPT_DIR/Sync/systemd/bandcamp-sync-worker.path"      "$SYSTEMD/"
ln -sf "$SCRIPT_DIR/Sync/systemd/bandcamp-sync-reconcile.service" "$SYSTEMD/"
ln -sf "$SCRIPT_DIR/Sync/systemd/bandcamp-sync-reconcile.timer"  "$SYSTEMD/"
echo "✔ Sync services linked"

# 5. Install retry services
ln -sf "$SCRIPT_DIR/Retry/systemd/bandcamp-sync-retry.service" "$SYSTEMD/"
ln -sf "$SCRIPT_DIR/Retry/systemd/bandcamp-sync-retry.timer"   "$SYSTEMD/"
echo "✔ Retry services linked"

# 6. Reload systemd
echo ""
echo "🔄 Reloading systemd daemon..."
systemctl --user daemon-reload
echo "✔ Systemd daemon reloaded"

# 7. Enable and start services
echo ""
echo "🚀 Enabling and starting services..."
systemctl --user enable --now bandcamp-dashboard
echo "✔ Dashboard service enabled and started"

systemctl --user enable --now bandcamp-sync-worker.path
echo "✔ Sync worker path enabled and started"

systemctl --user enable --now bandcamp-sync-reconcile.timer
echo "✔ Sync reconcile timer enabled and started"

systemctl --user enable --now bandcamp-sync-retry.timer
echo "✔ Retry timer enabled and started"

# 8. Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Add your Bandcamp cookies to ~/.config/bandcamp/cookies.txt"
echo "  2. Run: source $SCRIPT_DIR/venv/bin/activate"
echo "  3. Run: python3 $SCRIPT_DIR/bin/capture_fan_id.py"
echo "  4. Open http://localhost:5000 to view the dashboard"
echo ""
echo "Service Status:"
systemctl --user status bandcamp-dashboard --no-pager || true
echo ""
