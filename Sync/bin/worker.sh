#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/BandcampSync/Sync/logs/worker.log"
mkdir -p "$(dirname "$LOG")"

log() {
  # Structured, append-only log line for worker lifecycle + job transitions.
  # Format: ISO8601 action=... job_id=... detail="..."
  local action="$1"
  local job_id="${2:-}" 
  local detail="${3:-}"
  printf '%s action=%s job_id=%s detail="%s"\n' "$(date -Is)" "$action" "$job_id" "$detail" >> "$LOG"
}

log "worker_start" "-" "worker.sh started"

## Purpose:
# -----------------------------
# 🔹 worker.sh one album at a time
# 
# Consumes one job
# Downloads one album 
# Moves job to done/ or failed/

BASE="$HOME/BandcampSync/Sync/inbox"
PENDING="$BASE/pending"
INPROGRESS="$BASE/in_progress"
DONE="$BASE/done"
FAILED="$BASE/failed"

mkdir -p "$PENDING" "$INPROGRESS" "$DONE" "$FAILED"

job="$(ls "$PENDING"/*.job 2>/dev/null | head -n1 || true)"
if [[ -z "$job" ]]; then
  log "worker_noop" "-" "no pending jobs"
  log "worker_end" "-" "worker.sh exited"
  exit 0
fi

name="$(basename "$job")"
job_id="${name%.job}"

log "job_transition" "$job_id" "pending->in_progress"
mv "$job" "$INPROGRESS/$name"

if "$HOME/BandcampSync/Sync/bin/download_one.sh" "$INPROGRESS/$name"; then
  mv "$INPROGRESS/$name" "$DONE/$name"
  log "job_transition" "$job_id" "in_progress->done"
  log "worker_end" "$job_id" "worker.sh exited"
else
  mv "$INPROGRESS/$name" "$FAILED/$name"
  log "job_transition" "$job_id" "in_progress->failed"
  log "worker_end" "$job_id" "worker.sh exited"
fi
