#!/usr/bin/env bash
set -euo pipefail

## Purpose:
# -----------------------------
# Periodically move jobs from inbox/failed -> inbox/pending
# Allows for automatic retries of transient failures (rate limits, timeouts)

BASE="$HOME/BandcampSync/Sync/inbox"
FAILED="$BASE/failed"
PENDING="$BASE/pending"
LOG="$HOME/BandcampSync/Retry/logs/retry.log"

mkdir -p "$(dirname "$LOG")"

log() {
  # Structured logging for retry actions
  local action="$1"
  local job_id="${2:-}" 
  local detail="${3:-}"
  printf '%s action=%s job_id=%s detail="%s"\n' "$(date -Is)" "$action" "$job_id" "$detail" >> "$LOG"
}

log "retry_start" "-" "retry.sh started"

# Check if there are any files
if [ -z "$(ls -A "$FAILED")" ]; then
   log "retry_noop" "-" "no failed jobs found"
   log "retry_end" "-" "retry.sh finished"
   exit 0
fi

count=0
for job in "$FAILED"/*.job; do
    [ -e "$job" ] || continue
    
    filename="$(basename "$job")"
    job_id="${filename%.job}"
    
    log "retry_requeue" "$job_id" "moving failed->pending"
    mv "$job" "$PENDING/$filename"
    count=$((count + 1))
done

log "retry_end" "-" "requeued $count jobs"
