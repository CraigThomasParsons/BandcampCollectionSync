#!/usr/bin/env bash
set -euo pipefail

## Minimal wrapper to download a single album given a job file.
# Job file format is intentionally simple: either a raw URL line
# or a shell-style "URL=..." line. This keeps the queue human-readable.

JOB="$1"

if [[ ! -f "$JOB" ]]; then
	echo "ERROR: job file not found: $JOB" >&2
	exit 1
fi

line="$(head -n1 "$JOB" | tr -d '\r' | xargs || true)"
if [[ -z "$line" ]]; then
	echo "ERROR: job file is empty: $JOB" >&2
	exit 1
fi

if [[ "$line" == URL=* ]]; then
	URL="${line#URL=}"
else
	URL="$line"
fi

COOKIES="$HOME/.config/bandcamp/cookies.txt"
DEST="$HOME/Music/Bandcamp"

if [[ ! -f "$COOKIES" ]]; then
	echo "ERROR: Missing cookies at $COOKIES" >&2
	exit 1
fi

mkdir -p "$DEST"

# Compute intended album folder from yt-dlp metadata (fast).
# If it exists, skip. If not, download.
album_dir="$(yt-dlp --cookies "$COOKIES" --print '%(artist)s/%(album)s' "$URL" 2>/dev/null | head -n1 || true)"
if [[ -n "$album_dir" && -d "$DEST/$album_dir" ]]; then
	echo "✔ already have: $album_dir"
	exit 0
fi

echo "⬇ downloading $URL"
yt-dlp \
	--cookies "$COOKIES" \
	--extract-audio \
	--audio-format flac \
	--embed-metadata \
	--embed-thumbnail \
	--output "$DEST/%(artist)s/%(album)s/%(track_number)02d - %(title)s.%(ext)s" \
	"$URL"
