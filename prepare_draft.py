"""Prepare one unsent LinkedIn message draft for review."""
import re
import sys

from playwright.sync_api import sync_playwright

import config
import tracker
from common import configure_console, is_auth_or_security_interstitial, start_browser
from find_leads import is_first_degree_connection
from run_slot import attach_resume, find_visible, open_message_box, _message_body_selectors


def prepare_lead_draft(lead_id):
    tracker.init_db()
    lead = tracker.get_lead(lead_id)
    if lead is None:
        raise LookupError(f"Lead {lead_id} was not found.")
    if lead[4] != "queued":
        raise ValueError("Only queued leads can be prepared as new drafts.")
    if not lead[5]:
        raise ValueError("No reviewed draft text is saved for this lead.")

    _, name, _, profile_url, _, message = lead[:6]
    if not profile_url:
        raise ValueError("The lead does not have a LinkedIn profile URL.")

    with sync_playwright() as playwright:
        browser, page = start_browser(playwright, headless=False)
        if not browser:
            tracker.set_draft_state(lead_id, "failed")
            return False

        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            if is_auth_or_security_interstitial(page):
                raise RuntimeError("LinkedIn requires login or is showing a security page.")

            main = page.locator("main")
            profile_text = main.inner_text()
            normalized_name = re.sub(r"\W+", " ", name).strip().lower()
            normalized_profile = re.sub(r"\W+", " ", profile_text).strip().lower()
            if not normalized_name or normalized_name not in normalized_profile:
                raise RuntimeError("The opened profile name did not match the selected lead.")
            if not is_first_degree_connection(profile_text):
                raise RuntimeError("The selected profile is not visibly marked as a 1st-degree connection.")

            composer = open_message_box(page)
            if composer is None:
                raise RuntimeError("LinkedIn did not open a message composer for this connection.")

            attach_resume(composer, config.RESUME_FILE)
            editor = find_visible(composer, _message_body_selectors())
            if editor is None:
                raise RuntimeError("LinkedIn message editor is unavailable.")
            editor.fill(message)
            composer.wait_for_timeout(800)
            editor_text = editor.evaluate(
                "(element) => element.tagName === 'TEXTAREA' ? element.value : element.innerText"
            )
            if editor_text != message:
                raise RuntimeError("The draft text did not remain in the LinkedIn editor.")

            tracker.set_draft_state(lead_id, "prepared")
            print(f"UNSENT DRAFT PREPARED for {name}. Resume attachment was confirmed.")
            print("No send action was performed. Review the open LinkedIn composer.")
            input("Press Enter here to close the browser after reviewing the draft...")
            return True
        except Exception:
            tracker.set_draft_state(lead_id, "failed")
            raise
        finally:
            browser.close()


def main():
    configure_console()
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        raise SystemExit("Usage: python prepare_draft.py LEAD_ID")
    try:
        prepare_lead_draft(int(sys.argv[1]))
    except Exception as exc:
        tracker.set_draft_state(int(sys.argv[1]), "failed")
        print(f"Draft preparation failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
