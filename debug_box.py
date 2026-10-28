# debug_box.py  -  Msg box kholke batata hai ki page par kaunse input/textbox hain.
# Ye koi msg NAHI bhejta. Chalao:  python debug_box.py
import sqlite3
from playwright.sync_api import sync_playwright
from common import start_browser
from run_slot import open_message_box

INFO_JS = """
() => {
  const res = [];
  document.querySelectorAll('textarea, input, [contenteditable], [role="textbox"]').forEach(e => {
    const r = e.getBoundingClientRect();
    res.push({
      tag: e.tagName,
      cls: (e.className || '').toString().slice(0, 90),
      role: e.getAttribute('role'),
      ph: e.getAttribute('placeholder'),
      aria: e.getAttribute('aria-label'),
      editable: e.getAttribute('contenteditable'),
      visible: r.width > 0 && r.height > 0
    });
  });
  return res;
}
"""

c = sqlite3.connect("applications_tracker.db")
row = c.execute("SELECT name, profile_url FROM leads LIMIT 1").fetchone()
c.close()
print("Profile:", row)

with sync_playwright() as p:
    browser, page = start_browser(p, headless=False)
    page.goto(row[1], wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    print("Message button mila:", open_message_box(page))
    page.wait_for_timeout(6000)

    print("\nIframes:", len(page.frames) - 1)
    print("\n--- Input / textbox elements ---")
    for e in page.evaluate(INFO_JS):
        if e["visible"]:
            print(e)

    print("\n--- Buttons (visible) ---")
    names = page.evaluate("""() => [...document.querySelectorAll('button')]
        .filter(b => b.getBoundingClientRect().width > 0)
        .map(b => (b.innerText || b.getAttribute('aria-label') || '').trim())
        .filter(t => t).slice(-30)""")
    print(names)

    page.screenshot(path="debug.png")
    print("\nScreenshot saved: debug.png")
    input("Browser dekh lo, phir Enter dabao band karne ke liye...")
    browser.close()