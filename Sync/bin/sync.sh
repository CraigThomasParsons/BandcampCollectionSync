#!/usr/bin/env bash
set -euo pipefail

COOKIES="$HOME/.config/bandcamp/cookies.txt"
OWNED="$HOME/bandcamp-owned.txt"
DEST="$HOME/Music/Bandcamp"

clean_url() {
  echo "$1" | sed 's/&quot;//g' | cut -d',' -f1
}


if [[ ! -f "$COOKIES" ]]; then
  echo "ERROR: Missing cookies at $COOKIES"
  exit 1
fi

if [[ ! -f "$OWNED" ]]; then
  echo "ERROR: Missing owned list at $OWNED"
  echo "Run: $HOME/BandcampSync/extract_owned.py"
  exit 1
fi

mkdir -p "$DEST"

while IFS= read -r url; do
  url="$(clean_url "$url")"
  [[ -z "$url" ]] && continue
  echo "🔍 $url"

  # Compute intended album folder from yt-dlp metadata (fast).
  # If it exists, skip. If not, download.
  album_dir="$(yt-dlp --cookies "$COOKIES" --print '%(artist)s/%(album)s' "$url" 2>/dev/null | head -n1 || true)"
  if [[ -n "$album_dir" && -d "$DEST/$album_dir" ]]; then
    echo "✔ already have: $album_dir"
    continue
  fi

  echo "⬇ downloading..."
  yt-dlp \
    --cookies "$COOKIES" \
    --extract-audio \
    --audio-format flac \
    --embed-metadata \
    --embed-thumbnail \
    --output "$DEST/%(artist)s/%(album)s/%(track_number)02d - %(title)s.%(ext)s" \
    "$url"

done < "$OWNED"

