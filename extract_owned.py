"""
Parses the downloaded `collection.json` file to extract all album URLs.
Writes unique, clean URLs to `bandcamp-owned.txt` for the Sync/enqueuer to process.
"""
import json
import sys
from pathlib import Path

BASE = Path.home() / "BandcampSync"
import json
import sys

BASE = Path.home() / "BandcampSync"
JSON_FILE = BASE / "collection.json"
OUT = Path.home() / "bandcamp-owned.txt"

def main():
    if not JSON_FILE.exists():
        print(f"ERROR: {JSON_FILE} does not exist")
        return 1

    try:
        data = json.loads(JSON_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {JSON_FILE}: {e}")
        return 1

    links = []
    for item in data:
        url = item.get("item_url")
        if url:
            links.append(url)
    
    links = sorted(set(links))

    if not links:
        print("WARNING: No album links found in collection.json.")
        OUT.write_text("")
        return 0

    OUT.write_text("\n".join(links) + "\n")
    print(f"Wrote {len(links)} URLs to {OUT}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

