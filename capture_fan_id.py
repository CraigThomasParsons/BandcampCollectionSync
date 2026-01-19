#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
from pathlib import Path

COOKIES = Path.home() / ".config/bandcamp/cookies.txt"

def load_netscape_cookies(context):
    with COOKIES.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 6:
                name = parts[-2]
                value = parts[-1]
                context.add_cookies([{
                    "domain": "bandcamp.com",
                    "path": "/",
                    "name": name,
                    "value": value
                }])

with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    context = browser.new_context()
    load_netscape_cookies(context)

    page = context.new_page()
    page.goto("https://bandcamp.com/craigpars0061", timeout=60000)
    page.wait_for_load_state("networkidle")

    fan_id = page.evaluate("""
        () => window.FanData && window.FanData.fan_id
    """)

    print("fan_id =", fan_id)

    browser.close()
