#!/usr/bin/env python3
"""
Bootstrap helper to discover the Bandcamp fan_id for the logged-in user.
This script uses Playwright and existing cookies to navigate to the user's profile
and extract the fan_id from `window.FanData` or `pagedata`.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Paths
COOKIES_FILE = Path.home() / ".config/bandcamp/cookies.txt"
CONFIG_DIR = Path.home() / "BandcampSync/config"
FAN_ID_FILE = CONFIG_DIR / "fan_id.txt"

def load_netscape_cookies(context):
    """Loads Netscape-formatted cookies from the file into the Playwright context."""
    if not COOKIES_FILE.exists():
        print(f"ERROR: Cookies file not found at {COOKIES_FILE}")
        print("Please log in and save your cookies first.")
        sys.exit(1)

    with COOKIES_FILE.open() as f:
        count = 0
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")
            if len(parts) < 6:
                continue

            # Handle 6 or 7 field Netscape format
            if len(parts) == 6:
                domain, flag, path, secure, name, value = parts
            else:
                domain, flag, path, secure, expiry, name, value = parts[:7]

            try:
                context.add_cookies([{
                    "domain": domain.lstrip("."),
                    "path": path,
                    "name": name,
                    "value": value,
                    "secure": secure.lower() == "true",
                    # Add expiry only if it looks like a valid timestamp if needed, 
                    # but Playwright handles session cookies fine without it usually.
                }])
                count += 1
            except Exception as e:
                print(f"Warning: Skipping cookie {name}: {e}")
    
    print(f"Loaded {count} cookies.")

def discover_fan_id():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()
        load_netscape_cookies(context)
        page = context.new_page()

        print("Navigating to bandcamp.com/profile...")
        try:
            # Direct navigation to profile usually redirects to the correct user page
            response = page.goto("https://bandcamp.com/profile", timeout=60000, wait_until="domcontentloaded")
            final_url = page.url
            print(f"Landed at: {final_url}")
            
            # Check if we are on a login page or generic home
            if "login" in final_url:
                print("ERROR: Redirected to login. Cookies might be invalid.")
                browser.close()
                return None
            
            # Extract fan_id from window.FanData
            # This works on both the feed page and the specific collection page usually
            fan_id = page.evaluate("() => window.FanData ? window.FanData.fan_id : null")

            if fan_id:
                print(f"Found fan_id: {fan_id}")
                browser.close()
                return fan_id
            
            # Fallback: Try looking for pagedata blob if FanData is missing
            print("FanData not found. Checking pagedata...")
            pagedata = page.get_attribute("#pagedata", "data-blob")
            if pagedata:
                import json
                data = json.loads(pagedata)
                if 'identities' in data and 'fan' in data['identities']:
                    fan_id = data['identities']['fan']['id']
                    print(f"Found fan_id from pagedata: {fan_id}")
                    browser.close()
                    return fan_id

            print("ERROR: Could not find fan_id on the page.")
            browser.close()
            return None

        except Exception as e:
            print(f"ERROR: Navigation failed: {e}")
            browser.close()
            return None

def save_fan_id(fan_id):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with FAN_ID_FILE.open("w") as f:
        f.write(str(fan_id) + "\n")
    print(f"Saved fan_id to {FAN_ID_FILE}")

def main():
    fan_id = discover_fan_id()
    if fan_id:
        save_fan_id(fan_id)
    else:
        print("ERROR: Fan ID discovery failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
