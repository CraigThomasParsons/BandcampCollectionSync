#!/usr/bin/env bash
set -euo pipefail

SYSTEMD="$HOME/.config/systemd/user"

mkdir -p "$SYSTEMD"

ln -sf "$PWD/bandcamp-sync-reconcile.service" "$SYSTEMD/"
ln -sf "$PWD/bandcamp-sync-reconcile.timer"   "$SYSTEMD/"
ln -sf "$PWD/bandcamp-sync-worker.service"    "$SYSTEMD/"
ln -sf "$PWD/bandcamp-sync-worker.path"       "$SYSTEMD/"

systemctl --user daemon-reload

systemctl --user enable --now bandcamp-sync-reconcile.timer
systemctl --user enable --now bandcamp-sync-worker.path

echo "✔ BandcampSync stage installed"
