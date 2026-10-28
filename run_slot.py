# run_slot.py - LinkedIn composer helpers. The command-line sender is disabled.
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from common import configure_console


def open_message_box(page):
    """Open the normal LinkedIn compose route and wait for its editor to hydrate."""
    ctx = page.context
    before = set(ctx.pages)
    main = page.locator("main")
    compose_url = _visible_message_compose_url(page, main)
    if compose_url:
        page.goto(compose_url, wait_until="domcontentloaded", timeout=30000)

    message_actions = (
        main.get_by_role("button", name=re.compile(r"^Message(?:$|\s)", re.I)),
        main.get_by_role("link", name=re.compile(r"^Message(?:$|\s)", re.I)),
    )
    if not compose_url:
        clicked = _click_first_visible(message_actions)
    else:
        clicked = True
    if not clicked:
        more_actions = (
            main.get_by_role("button", name=re.compile(r"^More$", re.I)),
            main.get_by_role("button", name=re.compile(r"^More actions$", re.I)),
        )
        if _click_first_visible(more_actions):
            page.wait_for_timeout(800)
            menu_message_actions = (
                page.get_by_role("menuitem", name=re.compile(r"^Message$", re.I)),
                page.get_by_role("button", name=re.compile(r"^Message$", re.I)),
                page.get_by_role("link", name=re.compile(r"^Message$", re.I)),
            )
            compose_url = _visible_message_compose_url(page, page)
            if compose_url:
                page.goto(compose_url, wait_until="domcontentloaded", timeout=30000)
                clicked = True
            else:
                clicked = _click_first_visible(menu_message_actions)
    if not clicked:
        print("  No available Message action; this profile may require a connection or InMail.")
        return None

    page.wait_for_timeout(4000)
    new_pages = [p for p in ctx.pages if p not in before]
    if new_pages:                      # InMail: naya tab khula
        cp = new_pages[-1]
        try:
            cp.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        cp.wait_for_timeout(4000)
    else:
        cp = page

    editor = find_visible(cp, _message_body_selectors(), timeout_s=20)
    if editor is None:
        print("  Message action opened, but the compose editor did not load.")
        return None
    return cp


def _visible_message_compose_url(page, scope):
    links = scope.get_by_role("link", name=re.compile(r"^Message(?:$|\s)", re.I))
    for index in range(links.count()):
        link = links.nth(index)
        if not link.is_visible():
            continue
        href = link.get_attribute("href")
        if not href:
            continue
        target = urljoin(page.url, href)
        parsed = urlsplit(target)
        if (
            parsed.scheme == "https"
            and parsed.hostname in {"linkedin.com", "www.linkedin.com"}
            and parsed.path.startswith("/messaging/compose/")
        ):
            return target
    return None


def _message_body_selectors():
    return [
        "textarea[name='message']",
        "textarea[aria-label*='message' i]",
        "div.msg-form__contenteditable",
        "div[role='textbox'][contenteditable='true']",
        "div[contenteditable='true']",
    ]


def _click_first_visible(locators):
    for locator in locators:
        for index in range(locator.count()):
            element = locator.nth(index)
            if element.is_visible() and element.is_enabled():
                element.click()
                return True
    return False


def find_visible(page, selectors, timeout_s=12):
    """Selectors mein se pehla visible element dhundhta hai."""
    for _ in range(timeout_s):
        for s in selectors:
            loc = page.locator(s)
            for i in range(loc.count() - 1, -1, -1):
                el = loc.nth(i)
                try:
                    if el.is_visible():
                        return el
                except Exception:
                    pass
        page.wait_for_timeout(1000)
    return None


def attach_resume(cp, resume_path):
    """Attach the configured resume and require a visible filename confirmation."""
    resume = Path(resume_path)
    if not resume.is_file():
        raise FileNotFoundError(f"Resume file does not exist: {resume}")

    file_inputs = cp.locator("input[type='file']")
    if file_inputs.count() == 0:
        attach_button = cp.get_by_role("button", name=re.compile(r"attach.*file|file.*attach", re.I))
        if attach_button.count() > 0 and attach_button.first.is_visible():
            attach_button.first.click()
            file_inputs = cp.locator("input[type='file']")

    if file_inputs.count() == 0:
        raise RuntimeError("LinkedIn did not show a file attachment control.")

    file_input = file_inputs.last
    accept = (file_input.get_attribute("accept") or "").lower()
    if accept and ".pdf" not in accept and "*/*" not in accept:
        raise RuntimeError(f"LinkedIn attachment control does not accept PDFs: {accept}")

    file_input.set_input_files(str(resume))
    try:
        cp.get_by_text(resume.name, exact=False).first.wait_for(state="visible", timeout=10000)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError("Resume upload was not visibly confirmed; message was not sent.") from exc


def main():
    configure_console()
    print("Automated sending is disabled. Use the dashboard's Review message action to prepare an unsent draft.")


if __name__ == "__main__":
    main()