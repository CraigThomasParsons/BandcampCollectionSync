#!/usr/bin/env bash
set -euo pipefail

## Purpose:
# -----------------------------
# Enqueue owned albums into the download queue
# Converts “missing albums” into queue jobs
# One job file per album
# Handles deduplication + idempotency

OWNED="$HOME/bandcamp-owned.txt"
QUEUE="$HOME/BandcampSync/Sync/inbox/pending"
LOG="$HOME/BandcampSync/Sync/logs/enqueue.log"

mkdir -p "$(dirname "$LOG")"

log() {
  # Structured, append-only log line for enqueue lifecycle + job creation.
  local action="$1"
  local job_id="${2:-}" 
  local detail="${3:-}"
  printf '%s action=%s job_id=%s detail="%s"\n' "$(date -Is)" "$action" "$job_id" "$detail" >> "$LOG"
}

mkdir -p "$QUEUE"

log "enqueue_start" "-" "enqueue_owned.sh started"

clean_url() {
  echo "$1" | sed 's/&quot;//g' | cut -d',' -f1
}

while IFS= read -r url; do
  url="$(clean_url "$url")"
  [[ -z "$url" ]] && continue

  # Deterministic job id (stable, readable)
  job_id="$(echo -n "$url" | sha1sum | cut -d' ' -f1)"
  job_file="$QUEUE/$job_id.job"

  # Idempotent: do nothing if already queued
  if [[ -f "$job_file" ]]; then
    log "enqueue_skip" "$job_id" "already queued"
    continue
  fi

  echo "$url" > "$job_file"
  log "enqueue_job" "$job_id" "$url"

done < "$OWNED"

log "enqueue_end" "-" "enqueue_owned.sh finished"
