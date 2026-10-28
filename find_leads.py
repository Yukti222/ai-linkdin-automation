# find_leads.py  -  LinkedIn pe search karke recruiters ko database mein 'queued' save karta hai.
# Ye MSG NAHI BHEJTA. Sirf list banata hai.
#
# Chalane ka tarika (terminal mein):   python find_leads.py
import urllib.parse
import re
from playwright.sync_api import sync_playwright
import config
import tracker
from common import configure_console, is_auth_or_security_interstitial, start_browser, human_pause

# Page ke saare profile links aur unke card ka text nikalne ka JavaScript
EXTRACT_JS = """
() => {
  const out = {};
  document.querySelectorAll('a[href*="/in/"]').forEach(a => {
    const url = a.href.split('?')[0];
    if (out[url]) return;
    const card = a.closest('li') || a.parentElement.parentElement.parentElement;
    out[url] = card ? card.innerText : '';
  });
  return out;
}
"""


def is_recruiter(text):
    t = text.lower()
    good = any(w in t for w in config.GOOD_WORDS)
    bad = any(w in t for w in config.BAD_WORDS)
    return good and not bad


def is_first_degree_connection(text):
    """Only accept LinkedIn result cards explicitly marked as 1st-degree connections."""
    pattern = r"^\s*[\W_]*(?:1st|1st degree(?: connection)?|first degree(?: connection)?)\s*[\W_]*$"
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def build_search_url(page_number):
    """Search recruiter profiles within the configured LinkedIn connection network."""
    params = urllib.parse.urlencode({
        "keywords": config.SEARCH_QUERY,
        "page": page_number,
        "network": f'["{config.SEARCH_NETWORK}"]',
    })
    return f"https://www.linkedin.com/search/results/people/?{params}"


def canonical_profile_url(url):
    """Normalize profile links, discarding nested action paths and query parameters."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname not in {"linkedin.com", "www.linkedin.com"}:
        return None
    match = re.match(r"^/in/([^/]+)/?", parsed.path, re.IGNORECASE)
    if not match:
        return None
    return f"https://www.linkedin.com/in/{match.group(1)}/"


def parse_card(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # "• 2nd" jaise faltu lines hata do
    lines = [l for l in lines if not l.startswith("•") and "degree connection" not in l.lower()]
    name = lines[0] if lines else ""
    headline = " | ".join(lines[1:4]) if len(lines) > 1 else ""
    return name, headline


def main():
    configure_console()
    tracker.init_db()
    new_count = 0

    with sync_playwright() as p:
        browser, page = start_browser(p, headless=False)
        if not browser:
            return False

        for pg in range(1, config.SEARCH_PAGES + 1):
            url = build_search_url(pg)
            print(f"\nSearch page {pg} khol raha hu...")
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            if is_auth_or_security_interstitial(page):
                print("ERROR: LinkedIn search login/security page par redirect hua. Search stop ki; koi message nahi bheja.")
                browser.close()
                return False

            # neeche scroll karo taaki saare results load ho jaayein
            for _ in range(4):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1200)

            results = page.evaluate(EXTRACT_JS)
            print(f"  {len(results)} profiles mile.")

            for url_, text in results.items():
                profile_url = canonical_profile_url(url_)
                if profile_url is None or not text.strip():
                    continue
                if not is_first_degree_connection(text):
                    continue
                name, headline = parse_card(text)
                if not name:
                    continue
                if is_recruiter(name + " " + headline):
                    if tracker.add_lead(name, headline, profile_url):
                        new_count += 1
                        print(f"  + SAVED: {name} | {headline[:60]}")
                else:
                    print(f"  - skip : {name} | {headline[:60]}")

            human_pause(4, 8)

        browser.close()

    print(f"\nKhatam. {new_count} naye recruiters save hue.")
    tracker.show_summary()
    return True


if __name__ == "__main__":
    main()