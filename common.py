# common.py  -  Browser kholna aur cookies se login karna (dono scripts yahi use karenge)
import json
import sys
import time
import random
import config


def human_pause(a=2.0, b=5.0):
    time.sleep(random.uniform(a, b))


def configure_console():
    """Keep Unicode profile text from crashing Windows consoles with legacy encodings."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="replace")


def is_auth_or_security_interstitial(page):
    """Identify login, checkpoint, authwall, and provider security interstitials."""
    url = page.url.lower()
    title = page.title().lower()
    return any(marker in url for marker in ("login", "checkpoint", "authwall")) or any(
        marker in title for marker in ("attention required", "cloudflare")
    )


def start_browser(p, headless=False):
    """Browser kholta hai, cookies se login karta hai. Fail hone par (None, None) deta hai."""
    browser = p.chromium.launch(headless=headless)
    context = browser.new_context(viewport={"width": 1366, "height": 850})

    with open(config.COOKIES_FILE, "r") as f:
        context.add_cookies(json.load(f))

    page = context.new_page()
    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    if "feed" not in page.url or is_auth_or_security_interstitial(page):
        print("ERROR: LinkedIn login/security page aayi. linkedin_login.py se login refresh karke dobara chalao.")
        browser.close()
        return None, None

    print("Login OK (cookies se).")
    return browser, page