"""
Scrapes the user's Bandcamp collection using Playwright.
replaces the unreliable API method.

Features:
- Robust pagination handling (infinite scroll + "Show more" button)
- Retries on scroll to handle lazy loading
- Extracts item metadata (Artist, Title, URL) to collection.json
"""
import json
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Configuration
CONFIG_DIR = Path.home() / "BandcampSync/config"
COOKIES_FILE = Path.home() / ".config/bandcamp/cookies.txt"
OUT_FILE = Path.home() / "BandcampSync/collection.json"
FAILED_LOG = Path.home() / "BandcampSync/dashboard.log"

def log(msg):
    print(msg)
    with FAILED_LOG.open("a") as f:
        f.write(f"{time.ctime()}: {msg}\n")

def load_netscape_cookies(context):
    if not COOKIES_FILE.exists():
        log(f"WARNING: Cookies file not found at {COOKIES_FILE}")
        return

    with COOKIES_FILE.open() as f:
        count = 0
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 6:
                continue
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
                    "secure": secure.lower() == "true"
                }])
                count += 1
            except:
                pass
    log(f"Loaded {count} cookies.")

def scrape_collection():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        load_netscape_cookies(context)
        page = context.new_page()

        # Build URL - Assuming username is needed. 
        # But wait, we can just go to bandcamp.com/profile and it redirects?
        # Or we can use the fan_id to find the url? 
        # The user said he is 'craigpars0061'. 
        # Ideally we read the URL or username from somewhere or just use the fan_id logic.
        # But 'capture_fan_id.py' just saves the ID.
        # Let's try navigating to /profile again, or rely on the user providing the URL?
        # The user provided `https://bandcamp.com/craigpars0061` in the prompt.
        url = "https://bandcamp.com/craigpars0061"
        log(f"Navigating to {url}...")
        
        try:
            page.goto(url, timeout=60000)
        except Exception as e:
            log(f"Navigation failed: {e}")
            browser.close()
            return

        # Check if we got redirected
        final_url = page.url
        log(f"Landed at: {final_url}")
        
        
        # Pagination Loop
        # Bandcamp uses 'infinite scroll' which requires triggering scroll events.
        # It also has a "Show more" button that appears periodically.
        # We loop until neither scrolling nor clicking produces new items or height changes.
        last_height = 0
        count_before = 0
        retries = 0
        
        while True:
            # Scroll to bottom
            page.mouse.wheel(0, 5000)
            time.sleep(1)
            page.mouse.wheel(0, 5000)
            time.sleep(2)
            
            # Check for Show More button using multiple selectors
            button_clicked = False
            
            # Try text selector
            if page.is_visible("text=Show more"):
                print("Clicking 'Show more' (text)...")
                try:
                    page.click("text=Show more")
                    button_clicked = True
                except Exception as e:
                    print(f"Error clicking 'Show more' text: {e}")

            # Try class selector if text didn't work or just to be safe
            if not button_clicked and page.is_visible(".show-more"):
                 print("Clicking 'Show more' (class)...")
                 try:
                     page.click(".show-more")
                     button_clicked = True
                 except Exception as e:
                     print(f"Error clicking .show-more: {e}")
            
            if button_clicked:
                print("Button clicked. Waiting for items to load...")
                # Wait for item count to increase (poll for 10s)
                previous_count = page.locator(".collection-item-container").count()
                waited = 0
                new_items_found = False
                while waited < 10:
                    time.sleep(1)
                    waited += 1
                    current_count = page.locator(".collection-item-container").count()
                    if current_count > previous_count:
                        print(f"New items loaded! Count: {previous_count} -> {current_count}")
                        new_items_found = True
                        break
                
                if not new_items_found:
                    print(f"Timed out waiting for new items (stuck at {previous_count})")
                
                continue

            # If no button clicked, check height
            new_height = page.evaluate("document.body.scrollHeight")
            current_count = page.locator(".collection-item-container").count()
            
            print(f"Status: {current_count} items. Height: {new_height}")

            if new_height == last_height and current_count == count_before:
                 # Height and count stable.
                 # Check if we should retry
                 if retries < 5:
                     print(f"Height/Count stable. Retrying scroll ({retries}/5)...")
                     retries += 1
                     time.sleep(2)
                     # Force scroll
                     page.keyboard.press("End")
                     time.sleep(2)
                     continue
                 else:
                     print("Stable for too long. Stopping.")
                     break
            else:
                # Progress made
                retries = 0
            
            last_height = new_height
            count_before = current_count # Update baseline
            log("Scrolling...")

        # Extract items
        # Selector: .collection-item-container
        # Within that: .collection-item-title, .collection-item-artist, .item-link (for URL)
        
        items_data = page.evaluate("""() => {
            const items = [];
            document.querySelectorAll('.collection-item-container').forEach(el => {
                const titleEl = el.querySelector('.collection-item-title');
                const artistEl = el.querySelector('.collection-item-artist');
                const linkEl = el.querySelector('.item-link');
                
                if (titleEl && artistEl && linkEl) {
                    items.push({
                        item_title: titleEl.innerText.trim(),
                        band_name: artistEl.innerText.replace('by ', '').trim(),
                        item_url: linkEl.href
                    });
                }
            });
            return items;
        }""")

        log(f"Scraped {len(items_data)} items.")
        
        with OUT_FILE.open("w") as f:
            json.dump(items_data, f, indent=2)
            
        browser.close()

if __name__ == "__main__":
    scrape_collection()
