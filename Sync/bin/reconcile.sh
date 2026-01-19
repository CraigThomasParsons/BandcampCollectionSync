#!/usr/bin/env bash
set -euo pipefail
## Purpose:
# -----------------------------
# Compare desired state (owned albums)
# Against actual state (downloaded albums)
# Enqueue only what’s missing

LOG="$HOME/BandcampSync/Sync/logs/reconcile.log"
mkdir -p "$(dirname "$LOG")"

log() {
	# Structured, append-only log line for reconciliation lifecycle.
	local action="$1"
	local detail="${2:-}"
	printf '%s action=%s detail="%s"\n' "$(date -Is)" "$action" "$detail" >> "$LOG"
}

log "reconcile_start" "reconcile.sh started"
"$HOME/BandcampSync/Sync/bin/enqueue_owned.sh"
log "reconcile_end" "reconcile.sh finished"


