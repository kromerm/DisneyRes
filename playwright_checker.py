"""
Playwright-based availability checker for Disney World dining reservations.

This module launches a real Chromium browser, navigates Disney's reservation
SPA, and captures the availability API responses.  Because it uses a real
browser it handles authentication, cookies, and Queue-it automatically.

Usage
-----
Import and call ``check_availability()``, or run this file directly to do a
one-off test:

    python playwright_checker.py \\
        --slug be-our-guest-restaurant \\
        --date 2026-06-01 \\
        --party 2 \\
        --start 17:00 \\
        --end 21:00
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE      = "https://disneyworld.disney.go.com"
DINE_RES  = BASE + "/dine-res"

# Saved browser session state lets us reuse cookies between checks.
SESSION_FILE = Path(__file__).parent / "browser_session.json"

# How long (seconds) to wait for the page to settle before scraping.
PAGE_SETTLE_SECS = 8

# Queue-it max wait: if we're stuck for this long, give up and return empty.
QUEUE_WAIT_TIMEOUT_MS = 180_000  # 3 minutes


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def check_availability(
    slug: str,
    date: str,
    party_size: int,
    start_time: str = "07:00",
    end_time: str = "23:00",
    headless: bool = True,
    email: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    """
    Open Disney's reservation SPA in a browser, trigger an availability
    search for the given restaurant / date / party size, and return the
    result.

    Disney requires a MyDisney login to view availability.  Pass ``email``
    and ``password`` (or set ``DISNEYRES_EMAIL`` / ``DISNEYRES_PASSWORD``
    environment variables) so the checker can log in automatically.

    Parameters
    ----------
    slug : str
        Restaurant URL slug (e.g. ``"be-our-guest-restaurant"``).
    date : str
        Reservation date in ``YYYY-MM-DD`` format.
    party_size : int
        Number of guests (1–20).
    start_time : str
        Earliest acceptable time slot (``HH:MM`` 24-hour).
    end_time : str
        Latest acceptable time slot (``HH:MM`` 24-hour).
    headless : bool
        Run the browser in headless mode.  Set to ``False`` to watch the
        browser window — useful when Queue-it is active.
    email : str | None
        MyDisney account email.  Falls back to ``DISNEYRES_EMAIL`` env var.
    password : str | None
        MyDisney account password.  Falls back to ``DISNEYRES_PASSWORD`` env var.

    Returns
    -------
    dict with keys:
        ``found``  – bool, True when at least one slot is available
        ``slots``  – list of dicts, each with at minimum a ``"time"`` key
        ``raw``    – raw captured API responses (for debugging)
    """
    import os  # noqa: PLC0415

    # Resolve credentials from env vars if not passed directly.
    email    = email    or os.environ.get("DISNEYRES_EMAIL", "")
    password = password or os.environ.get("DISNEYRES_PASSWORD", "")

    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Run:  python -m playwright install --with-deps chromium"
        )

    captured: list[dict] = []

    with sync_playwright() as pw:
        # Prefer real Chrome (better TLS fingerprint, avoids bot detection).
        # Fall back to Playwright's bundled Chromium if Chrome is not installed.
        _launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        try:
            browser = pw.chromium.launch(
                channel="chrome",
                headless=headless,
                args=_launch_args,
            )
            logger.debug("Launched real Chrome browser")
        except Exception:
            logger.debug("Real Chrome not found — using Playwright Chromium")
            browser = pw.chromium.launch(headless=headless, args=_launch_args)

        # Re-use saved session cookies so we don't hammer auth on every check.
        context_options: dict = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }
        if SESSION_FILE.exists():
            try:
                context_options["storage_state"] = str(SESSION_FILE)
                logger.debug("Loaded saved browser session from %s", SESSION_FILE)
            except Exception:
                pass

        context = browser.new_context(**context_options)

        # Inject stealth JS into every page to hide automation fingerprints.
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
            """
        )

        page = context.new_page()

        # ----------------------------------------------------------------
        # Intercept API responses
        # ----------------------------------------------------------------
        def _on_response(response):
            url = response.url
            # Log every non-static response at DEBUG level so we can diagnose
            # which endpoints Disney actually uses.
            if response.status < 400 and any(
                kw in url
                for kw in ("/api/", "dine-vas", "dine-res", "disney.go.com/dining")
            ):
                logger.debug("NET %d  %s", response.status, url)

            # Capture responses that look like availability data
            if any(
                kw in url
                for kw in (
                    "getAvailability",
                    "getCalendarDays",
                    "/api/availability",
                    "dine-vas/api",
                    "dine-res/api",
                    "calendar-days",
                    "offer-list",
                    "nextAvailability",
                    "offerAvailability",
                    "reservation",
                )
            ):
                try:
                    body = response.json()
                    captured.append({"url": url, "status": response.status, "body": body})
                    logger.debug("Captured API response from: %s", url)
                except Exception:
                    pass

        page.on("response", _on_response)

        try:
            result = _do_check(
                page, context, slug, date, party_size, start_time, end_time,
                captured, email=email, password=password,
            )
        finally:
            # Save session state for next time
            try:
                context.storage_state(path=str(SESSION_FILE))
                logger.debug("Saved browser session to %s", SESSION_FILE)
            except Exception:
                pass
            browser.close()

        return result


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------

_DEBUG_SCREENSHOTS = Path(__file__).parent / "debug_screenshots"


def _maybe_screenshot(page, tag: str) -> None:
    """Save a screenshot when DEBUG logging is enabled (helps diagnose page state)."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    try:
        _DEBUG_SCREENSHOTS.mkdir(exist_ok=True)
        path = _DEBUG_SCREENSHOTS / f"{tag}.png"
        page.screenshot(path=str(path), full_page=False)
        logger.debug("Screenshot saved: %s", path)
    except Exception as exc:
        logger.debug("Screenshot failed: %s", exc)


def _do_check(
    page,
    context,
    slug: str,
    date: str,
    party_size: int,
    start_time: str,
    end_time: str,
    captured: list,
    email: str = "",
    password: str = "",
) -> dict[str, Any]:
    from playwright.sync_api import TimeoutError as PWTimeout  # noqa: PLC0415

    target = datetime.strptime(date, "%Y-%m-%d")

    # Include date and party size as query params so the SPA can pre-fill the form.
    booking_url = (
        f"{DINE_RES}/restaurant/{slug}/"
        f"?offerDate={date}&partySize={party_size}"
    )

    def _goto_booking_page() -> bool:
        """Navigate to the restaurant booking URL. Returns False on hard error."""
        logger.info("Navigating to %s", booking_url)
        try:
            page.goto(booking_url, wait_until="domcontentloaded", timeout=60_000)
            try:
                page.wait_for_load_state("networkidle", timeout=20_000)
            except PWTimeout:
                logger.debug("Network not fully idle — continuing anyway")
            page.wait_for_timeout(2_000)
            return True
        except PWTimeout:
            logger.warning("Page load timed out — proceeding anyway")
            return True
        except Exception as exc:
            logger.warning("Navigation error (%s) — returning empty result", exc)
            return False

    # Warm up with the Disney homepage first so the browser session looks
    # legitimate before hitting the reservation SPA.
    try:
        logger.debug("Warming up via Disney homepage…")
        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(1_500)
    except Exception as exc:
        logger.debug("Warm-up navigation failed (non-fatal): %s", exc)

    if not _goto_booking_page():
        return {"found": False, "slots": [], "raw": captured}

    logger.debug("Landed on: %s", page.url)
    _maybe_screenshot(page, "01_landed")

    # ---- Handle Queue-it waiting room ----
    if "queue-it" in page.url:
        logger.info("Queue-it detected — waiting up to %d s", QUEUE_WAIT_TIMEOUT_MS // 1000)
        try:
            page.wait_for_url(f"**{DINE_RES}/**", timeout=QUEUE_WAIT_TIMEOUT_MS)
        except PWTimeout:
            logger.warning("Queue-it wait timed out")
            return {"found": False, "slots": [], "raw": captured}

    # ---- Log in if Disney presents an authentication modal ----
    if _login_modal_visible(page):
        if email and password:
            logger.info("Login modal detected — signing in as %s", email)
            _handle_login(page, email, password)
            _maybe_screenshot(page, "02_after_login")
            logger.debug("Post-login URL: %s", page.url)

            # After login the SPA often redirects to the homepage or a generic
            # page — navigate back to the booking URL so the form re-loads.
            logger.info("Re-navigating to booking page after login…")
            if not _goto_booking_page():
                return {"found": False, "slots": [], "raw": captured}
            _maybe_screenshot(page, "03_post_login_booking")
            logger.debug("Post re-nav URL: %s", page.url)
        else:
            logger.warning(
                "Login modal detected but no credentials provided. "
                "Set DISNEYRES_EMAIL and DISNEYRES_PASSWORD (or pass --email/--password)."
            )
            return {"found": False, "slots": [], "raw": captured, "need_login": True}

    # ---- Handle 404 / redirect to wrong page ----
    if DINE_RES not in page.url:
        logger.warning("Unexpected URL after navigation: %s", page.url)

    # ---- Try to set party size in the UI ----
    _try_set_party_size(page, party_size)
    _maybe_screenshot(page, "04_party_size_set")

    # ---- Navigate calendar to target month and click the target date ----
    _try_navigate_calendar(page, target)
    _maybe_screenshot(page, "05_calendar_navigated")

    # ---- Wait for API calls to settle (longer than before) ----
    page.wait_for_timeout(PAGE_SETTLE_SECS * 1000)
    _maybe_screenshot(page, "06_final")

    # Log all captured responses at debug level for diagnostics
    if captured:
        logger.debug("Captured %d API response(s):", len(captured))
        for item in captured:
            logger.debug("  %s  ->  %s", item["url"][-100:], str(item["body"])[:200])
    else:
        logger.debug("No API responses captured — availability endpoint not triggered")

    # ---- Parse captured API responses ----
    slots = _parse_slots(captured, start_time, end_time, date)
    found = bool(slots)

    # ---- Fallback: scrape visible time-slot elements from the DOM ----
    if not found:
        dom_slots = _scrape_dom_slots(page, start_time, end_time)
        if dom_slots:
            slots = dom_slots
            found = True

    return {"found": found, "slots": slots, "raw": captured}


def _login_modal_visible(page) -> bool:
    """
    Return True if Disney's MyDisney login modal is currently visible.

    The login form may be rendered in the main frame or in a cross-origin
    iframe (Disney loads auth from a separate origin).
    """
    try:
        # ------------------------------------------------------------------
        # 1. Check the main frame and every sub-frame for email/password inputs
        # ------------------------------------------------------------------
        all_frames = page.frames
        logger.debug("Login check — %d frame(s):", len(all_frames))
        for frame in all_frames:
            logger.debug("  frame url=%s", frame.url)
            try:
                el = frame.query_selector(
                    "input[type='email'], "
                    "input[type='text'][placeholder*='email' i], "
                    "input[placeholder*='email' i], "
                    "input[name*='email' i], "
                    "input[id*='email' i], "
                    "input[autocomplete='email']"
                )
                if el:
                    try:
                        if el.is_visible():
                            logger.debug("  → login input found and visible")
                            return True
                    except Exception:
                        pass
            except Exception:
                pass

        # ------------------------------------------------------------------
        # 2. Scan all frame URLs for known auth/SSO domains
        # ------------------------------------------------------------------
        auth_keywords = ("auth", "login", "sso", "identity", "idp", "account", "cdn.sso")
        for frame in all_frames:
            if any(kw in frame.url.lower() for kw in auth_keywords):
                logger.debug("  → auth iframe detected: %s", frame.url)
                return True

        # ------------------------------------------------------------------
        # 3. Check main-frame page source for known login strings
        # ------------------------------------------------------------------
        try:
            content = page.content()
            login_strings = (
                "Enter your email to continue",
                "Log in to Walt Disney World",
                "MyDisney",
                "my.disney.go.com",
            )
            for s in login_strings:
                if s in content:
                    logger.debug("  → login string found in page source: %r", s)
                    return True
        except Exception:
            pass

        logger.debug("  → no login modal detected")
        return False
    except Exception as exc:
        logger.debug("_login_modal_visible error: %s", exc)
        return False


def _handle_login(page, email: str, password: str) -> None:
    """
    Complete the MyDisney login flow including optional MFA step:
        Step 1 — enter email and click Continue
        Step 2 — enter password and click Sign In  (may be skipped if MFA first)
        Step 3 — (optional) 6-digit email verification code for new devices

    The form may live in the main frame or an auth iframe — we check both.
    """
    from playwright.sync_api import TimeoutError as PWTimeout  # noqa: PLC0415
    import time as _time  # noqa: PLC0415

    EMAIL_SELECTOR = (
        "input[type='email'], "
        "input[type='text'][placeholder*='email' i], "
        "input[placeholder*='email' i], "
        "input[name*='email' i], "
        "input[autocomplete='email']"
    )
    PW_SELECTOR = "input[type='password']"
    # Disney OTP screen uses 6 individual single-char boxes
    OTP_DIGIT_SELECTOR = "input[maxlength='1']"

    def _find_in_frames(selector: str):
        """Return (frame, element) for the first matching visible element."""
        for frame in page.frames:
            try:
                el = frame.query_selector(selector)
                if el:
                    try:
                        if el.is_visible():
                            return frame, el
                    except Exception:
                        pass
            except Exception:
                continue
        return None, None

    def _find_all_in_frames(selector: str):
        """Return (frame, [elements]) for the first frame with visible matches."""
        for frame in page.frames:
            try:
                els = frame.query_selector_all(selector)
                visible = [e for e in els if e.is_visible()]
                if visible:
                    return frame, visible
            except Exception:
                continue
        return None, []

    def _detect_screen(timeout_ms: int = 12_000) -> tuple:
        """
        Poll until we see either the password field or OTP screen.
        Returns ('password', frame, element) or ('otp', frame, [inputs]) or ('unknown', None, None).

        OTP detection uses two strategies:
          1. DOM: look for individual digit boxes (multiple selectors tried)
          2. Text: scan frame HTML for Disney's OTP heading text
        """
        _OTP_INPUT_SELECTORS = [
            "input[maxlength='1']",
            "input[type='number']",
            "input[type='tel']",
        ]
        deadline = _time.monotonic() + timeout_ms / 1000
        while _time.monotonic() < deadline:
            # --- password screen? ---
            f, el = _find_in_frames(PW_SELECTOR)
            if el:
                return "password", f, el

            # --- OTP via DOM selectors ---
            for otp_sel in _OTP_INPUT_SELECTORS:
                f, els = _find_all_in_frames(otp_sel)
                if len(els) >= 4:
                    logger.debug("OTP inputs found via selector '%s' (%d els)", otp_sel, len(els))
                    return "otp", f, els

            # --- OTP via page text (handles any DOM structure) ---
            for frame in page.frames:
                try:
                    html = frame.content()
                    if "Check your email" in html or "6-digit" in html:
                        logger.debug("OTP screen detected by page text (frame: %s)", frame.url)
                        # Try to find any usable inputs
                        for otp_sel in _OTP_INPUT_SELECTORS + ["input"]:
                            f2, els2 = _find_all_in_frames(otp_sel)
                            # 4–8 → individual boxes; 1 → single OTP input (styled as boxes)
                            if 1 <= len(els2) <= 8:
                                logger.debug("OTP inputs found via fallback '%s' (%d els)", otp_sel, len(els2))
                                return "otp", f2, els2
                        # Screen confirmed but no inputs — will use keyboard
                        return "otp", frame, []
                except Exception:
                    pass

            page.wait_for_timeout(400)

        frame_urls = [f.url for f in page.frames]
        logger.debug("_detect_screen timed out. Active frames: %s", frame_urls)
        return "unknown", None, None

    def _fill_otp(otp_frame, digit_inputs: list) -> None:
        """Prompt the user for the 6-digit code and submit it."""
        import sys as _sys  # noqa: PLC0415
        logger.info("MFA verification required — check your email for a 6-digit code.")
        _sys.stdout.write(
            "\n" + "=" * 60 + "\n"
            "Disney sent a 6-digit code to your email.\n"
            "Enter the code (no spaces): "
        )
        _sys.stdout.flush()
        try:
            code = input().strip().replace(" ", "").replace("-", "")
        except EOFError:
            logger.warning("Could not read MFA code from stdin (run without pipes).")
            return
        if not code or not code.isdigit() or len(code) < 6:
            logger.warning("No valid MFA code entered; skipping.")
            return

        if digit_inputs:
            if len(digit_inputs) == 1:
                # Single input styled as 6 boxes — fill the whole code at once
                try:
                    digit_inputs[0].fill(code)
                    logger.debug("Filled OTP into single input")
                except Exception:
                    pass
            else:
                # Individual boxes — fill one digit each
                for i, box in enumerate(digit_inputs[:6]):
                    try:
                        box.fill(code[i])
                        page.wait_for_timeout(80)
                    except Exception:
                        pass
                logger.debug("Filled OTP into %d individual boxes", min(len(digit_inputs), 6))
        else:
            # No inputs found — click into the OTP frame area and type
            logger.debug("No OTP inputs found; using keyboard.type fallback")
            if otp_frame:
                try:
                    inputs = otp_frame.query_selector_all("input")
                    if inputs:
                        inputs[0].click()
                        page.wait_for_timeout(200)
                except Exception:
                    pass
            page.keyboard.type(code, delay=80)

        _click_button_in_frame(otp_frame or page, ["Continue", "Verify", "Submit", "Next", "Confirm"])
        page.wait_for_timeout(3_000)

    try:
        # --- Step 1: email ---
        frame, email_input = _find_in_frames(EMAIL_SELECTOR)
        if email_input is None:
            email_input = page.wait_for_selector(EMAIL_SELECTOR, timeout=10_000)
            frame = page.main_frame
        email_input.fill(email)
        logger.debug("Filled email in frame: %s", getattr(frame, "url", "?"))

        _click_button_in_frame(frame or page, ["Continue", "Next"])
        page.wait_for_timeout(2_500)

        # --- Step 2: detect what Disney shows next ---
        screen, s_frame, s_el = _detect_screen(timeout_ms=12_000)

        if screen == "otp":
            # New-device challenge appeared before password step
            _fill_otp(s_frame, s_el)
            # After OTP, Disney may still show the password screen
            screen2, s_frame, s_el = _detect_screen(timeout_ms=8_000)
            if screen2 == "password":
                screen, s_frame, s_el = screen2, s_frame, s_el
            else:
                screen = "done"  # logged in without password step

        if screen == "password":
            s_el.fill(password)
            logger.debug("Filled password")
            _click_button_in_frame(s_frame or page, ["Sign In", "Log In", "Login", "Continue"])
            page.wait_for_timeout(3_000)

            # After password, check one more time for OTP (some accounts get it here)
            screen3, s_frame3, s_el3 = _detect_screen(timeout_ms=6_000)
            if screen3 == "otp":
                _fill_otp(s_frame3, s_el3)

        if screen == "unknown":
            logger.warning("Could not detect password or OTP screen after email step.")

        # Wait for the login modal to disappear
        try:
            page.wait_for_selector(EMAIL_SELECTOR, state="detached", timeout=20_000)
        except PWTimeout:
            pass

        # Give the SPA time to re-render after auth
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PWTimeout:
            pass
        page.wait_for_timeout(2_000)
        logger.debug("Login completed. Current URL: %s", page.url)

    except Exception as exc:
        logger.warning("Login flow error: %s", exc)


def _click_button_in_frame(frame_or_page, labels: list[str]) -> None:
    """Click the first visible button in *frame_or_page* that matches a label."""
    for label in labels:
        try:
            btn = frame_or_page.query_selector(
                f"button:has-text('{label}'), "
                f"input[type='submit'][value*='{label}' i]"
            )
            if btn and btn.is_visible():
                btn.click()
                return
        except Exception:
            continue


def _try_set_party_size(page, party_size: int) -> None:
    """Click the party-size circle button or fill an input, ignoring failures."""
    try:
        # Disney's dine-res page renders party size as numbered circle buttons.
        # Try clicking the button whose visible text matches the party size.
        circle_selectors = [
            # Scoped to the party-size widget first
            f"[class*='party' i] button:text-is('{party_size}')",
            f"[class*='party' i] [role='button']:text-is('{party_size}')",
            f"[aria-label*='party' i] button:text-is('{party_size}')",
            # Broader: any button whose full text is exactly the digit
            f"button:text-is('{party_size}')",
            f"[role='button']:text-is('{party_size}')",
        ]
        for sel in circle_selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    logger.debug("Clicked party size circle button %d (sel: %s)", party_size, sel)
                    page.wait_for_timeout(1_500)   # let calendar panel open
                    return
            except Exception:
                continue

        # Fallback: legacy input / select approach
        input_selectors = [
            "input[aria-label*='party' i]",
            "input[aria-label*='guest' i]",
            "input[name*='party' i]",
            "select[aria-label*='party' i]",
            "select[aria-label*='guest' i]",
            "[data-testid*='party']",
            "[placeholder*='party' i]",
        ]
        for sel in input_selectors:
            el = page.query_selector(sel)
            if el:
                tag = el.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    el.select_option(str(party_size))
                else:
                    el.triple_click()
                    el.type(str(party_size), delay=50)
                logger.debug("Set party size to %d via input selector: %s", party_size, sel)
                page.wait_for_timeout(1_500)
                return

        logger.debug("Could not find any party size control for value %d", party_size)
    except Exception as exc:
        logger.debug("Could not set party size: %s", exc)


def _try_navigate_calendar(page, target: datetime) -> None:
    """
    Try to navigate the date picker to the target month and click the date.
    Silently ignores failures — the page may not have a calendar yet.
    """
    import re as _re  # noqa: PLC0415

    def _calendar_h2_visible() -> bool:
        """Return True when at least one h2 containing a 4-digit year is in the DOM and rendered."""
        try:
            return bool(page.evaluate(
                "() => [...document.querySelectorAll('h2')]"
                ".some(h => /\\d{4}/.test(h.innerText) && h.offsetParent !== null)"
            ))
        except Exception:
            return False

    # Poll for up to 12 seconds for the calendar month heading to appear
    deadline = 12
    for _ in range(deadline * 2):
        if _calendar_h2_visible():
            break
        page.wait_for_timeout(500)
    else:
        logger.debug("Calendar not visible yet — skipping date navigation")
        return

    logger.debug("Calendar heading found, proceeding with date navigation")

    try:
        # Navigate to the correct month
        _navigate_to_month(page, target)

        # Click the target day cell
        day_str = str(target.day)
        month_name = target.strftime("%B")
        year_str = str(target.year)
        # Try specific then broad selectors; skip disabled/greyed cells
        day_selectors = [
            f"[aria-label*='{month_name}' i][aria-label*='{day_str}']:not([aria-disabled='true'])",
            f"[aria-label*='{month_name} {day_str}' i]",
            f"[aria-label*='{month_name} {day_str}, {year_str}' i]",
            f"td:not([class*='unavailable' i]):not([class*='disabled' i]) button:text-is('{day_str}')",
            f"td:not([class*='unavailable' i]):not([class*='disabled' i]) span:text-is('{day_str}')",
            f"[role='gridcell']:not([aria-disabled='true']) :text-is('{day_str}')",
            # Broadest fallback: any visible element whose full text is the day number
            f"button:text-is('{day_str}')",
        ]
        for sel in day_selectors:
            try:
                cell = page.query_selector(sel)
                if cell:
                    cell.click()
                    logger.debug("Clicked day %s in calendar", day_str)
                    page.wait_for_timeout(1500)
                    return
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Calendar navigation failed: %s", exc)


def _navigate_to_month(page, target: datetime) -> None:
    """Advance the calendar to the target month using calculated click count."""
    from datetime import date as _date  # noqa: PLC0415
    today = _date.today()
    months_to_advance = (target.year - today.year) * 12 + (target.month - today.month)
    if months_to_advance <= 0:
        return

    logger.debug("Calendar: need to advance %d month(s) to reach %s %d",
                 months_to_advance, target.strftime("%B"), target.year)

    # Dump all visible buttons so we can identify the calendar next button
    JS_DUMP_BUTTONS = """
    () => {
        return [...document.querySelectorAll('button')]
            .filter(b => b.offsetParent !== null)
            .map(b => {
                const r = b.getBoundingClientRect();
                return {
                    text: b.innerText.trim().slice(0, 30),
                    ariaLabel: b.getAttribute('aria-label') || '',
                    cls: b.className.slice(0, 60),
                    x: Math.round(r.left), y: Math.round(r.top),
                    w: Math.round(r.width), h: Math.round(r.height)
                };
            });
    }
    """
    try:
        buttons = page.evaluate(JS_DUMP_BUTTONS)
        for b in buttons:
            logger.debug("BTN x=%d y=%d w=%d h=%d text=%r aria=%r cls=%r",
                         b['x'], b['y'], b['w'], b['h'],
                         b['text'], b['ariaLabel'], b['cls'])
    except Exception as exc:
        logger.debug("Button dump failed: %s", exc)

    # Click the calendar next button by finding it near the right-hand month heading.
    # Strategy: find the rightmost h2 (right calendar panel header), then click the
    # button that is to the right of and vertically aligned with it.
    JS_CLICK_NEXT = r"""
    () => {
        // Find all h2 elements that look like month headings
        const h2s = [...document.querySelectorAll('h2')]
            .filter(h => /[A-Z][a-z]+ \d{4}/.test(h.innerText) && h.offsetParent);
        if (h2s.length === 0) return 'no-month-h2';

        // Take the rightmost heading (right calendar panel)
        const rightH2 = h2s.reduce((a, b) =>
            b.getBoundingClientRect().left > a.getBoundingClientRect().left ? b : a
        );
        const h2r = rightH2.getBoundingClientRect();

        // Find a button to the right of this heading, within ±80px vertically
        const btns = [...document.querySelectorAll('button')]
            .filter(b => b.offsetParent !== null);
        const next = btns.filter(b => {
            const r = b.getBoundingClientRect();
            return r.left > h2r.right - 10
                && Math.abs((r.top + r.height/2) - (h2r.top + h2r.height/2)) < 80;
        });
        if (next.length === 0) {
            // Fallback: rightmost button with small width on same row as any month h2
            const anyH2 = h2s[0].getBoundingClientRect();
            const rowBtns = btns.filter(b => {
                const r = b.getBoundingClientRect();
                return Math.abs((r.top + r.height/2) - (anyH2.top + anyH2.height/2)) < 80
                    && r.width < 80;
            });
            if (rowBtns.length === 0) return 'no-next-btn';
            const rightmost = rowBtns.reduce((a, b) =>
                b.getBoundingClientRect().left > a.getBoundingClientRect().left ? b : a
            );
            rightmost.click();
            return 'fallback:' + rightmost.outerHTML.slice(0, 80);
        }
        // Click the leftmost of these (in case multiple)
        const btn = next.reduce((a, b) =>
            b.getBoundingClientRect().left < a.getBoundingClientRect().left ? b : a
        );
        btn.click();
        return 'h2-relative:' + btn.outerHTML.slice(0, 80);
    }
    """
    for i in range(months_to_advance):
        result = page.evaluate(JS_CLICK_NEXT)
        logger.debug("Calendar next click %d/%d: %s", i + 1, months_to_advance, result)
        page.wait_for_timeout(800)
        if result in ("no-month-h2", "no-next-btn"):
            logger.debug("Calendar: stopping — could not find next button")
            break


def _parse_slots(
    captured: list[dict], start_time: str, end_time: str, date: str = ""
) -> list[dict[str, Any]]:
    """Extract time slots from captured API responses and filter by time range."""
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt   = datetime.strptime(end_time,   "%H:%M")

    slots: list[dict] = []
    for item in captured:
        body = item.get("body", {})
        if not isinstance(body, dict):
            continue
        if body.get("code") == 404:
            continue

        raw_slots = (
            body.get("offerDetails")
            or body.get("timeSlots")
            or body.get("times")
            or body.get("slots")
            or body.get("offers")
            or []
        )

        # Some responses wrap slots inside nested keys
        if not raw_slots and "availability" in body:
            avail = body["availability"]
            if isinstance(avail, list):
                raw_slots = avail
            elif isinstance(avail, dict):
                for v in avail.values():
                    if isinstance(v, list):
                        raw_slots.extend(v)
                    elif isinstance(v, dict):
                        raw_slots.extend(v.get("times") or v.get("slots") or [])

        # Disney dine-res availability API: {'restaurants': {'YYYY-MM-DD': [{mealPeriodType, startTime, endTime, ...}]}}
        # Presence on the target date means that meal period has bookable availability.
        if not raw_slots and "restaurants" in body:
            restaurants_data = body["restaurants"]
            if date and date in restaurants_data:
                for period in restaurants_data[date]:
                    if isinstance(period, dict):
                        raw_slots.append(period)
            elif not date:
                for periods in restaurants_data.values():
                    for period in periods:
                        if isinstance(period, dict):
                            raw_slots.append(period)

        for slot in raw_slots:
            if isinstance(slot, str):
                slot = {"time": slot}
            if not isinstance(slot, dict):
                continue

            # Extract time string
            t_str = slot.get("time") or slot.get("startTime") or slot.get("label")
            if not t_str:
                slots.append(slot)
                continue

            # Parse and filter by requested time window
            t_str_clean = re.sub(r"\s*(AM|PM)\s*$", "", str(t_str), flags=re.I).strip()
            # Strip trailing seconds component (e.g. "17:00:00" → "17:00")
            if re.match(r"^\d{1,2}:\d{2}:\d{2}$", t_str_clean):
                t_str_clean = t_str_clean[:5]
            try:
                if ":" in t_str_clean:
                    t = datetime.strptime(t_str_clean, "%H:%M")
                else:
                    # 12-hour without AM/PM marker — include it
                    slots.append(slot)
                    continue
                if start_dt <= t <= end_dt:
                    slots.append(slot)
            except ValueError:
                slots.append(slot)  # Include slots we can't parse

    return slots


def _scrape_dom_slots(page, start_time: str, end_time: str) -> list[dict]:
    """
    Last-resort DOM scrape: look for time-slot buttons/links that are not
    disabled or marked unavailable.
    """
    time_pattern = re.compile(r"\b\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\b")
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt   = datetime.strptime(end_time,   "%H:%M")

    slots: list[dict] = []
    try:
        elements = page.query_selector_all(
            "button:not([disabled]):not([aria-disabled='true']), "
            "a[role='button']:not([aria-disabled='true'])"
        )
        for el in elements:
            try:
                text = el.inner_text().strip()
                m = time_pattern.search(text)
                if not m:
                    continue
                t_str = m.group()
                slots.append({"time": t_str, "source": "dom"})
            except Exception:
                continue
    except Exception as exc:
        logger.debug("DOM scrape failed: %s", exc)

    return slots


# ---------------------------------------------------------------------------
# CLI for manual testing
# ---------------------------------------------------------------------------


def _cli() -> None:
    from dotenv import load_dotenv  # noqa: PLC0415
    load_dotenv()  # Load .env so DISNEYRES_EMAIL / DISNEYRES_PASSWORD are available

    p = argparse.ArgumentParser(description="Test Disney dining availability via Playwright")
    p.add_argument("--slug",     required=True, help="e.g. be-our-guest-restaurant")
    p.add_argument("--date",     required=True, help="YYYY-MM-DD")
    p.add_argument("--party",    type=int, default=2)
    p.add_argument("--start",    default="07:00")
    p.add_argument("--end",      default="23:00")
    p.add_argument("--visible",  action="store_true", help="Show browser window")
    p.add_argument("--verbose",  action="store_true")
    p.add_argument("--email",    default="", help="MyDisney account email")
    p.add_argument("--password", default="", help="MyDisney account password")
    args = p.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s  %(message)s")

    result = check_availability(
        slug=args.slug,
        date=args.date,
        party_size=args.party,
        start_time=args.start,
        end_time=args.end,
        headless=not args.visible,
        email=args.email,
        password=args.password,
    )
    found = result["found"]
    slots = result["slots"]
    if result.get("need_login"):
        print("\nERROR: Disney login required. Re-run with --email and --password (or set DISNEYRES_EMAIL / DISNEYRES_PASSWORD).")
        return
    print(f"\nFound: {found}  |  Slots: {len(slots)}")
    for s in slots[:20]:
        print(f"  {s}")
    if not found and not slots:
        print("\nRaw captured responses:")
        for r in result["raw"]:
            print(f"  {r['url'][-80:]}  status={r['status']}  body={str(r['body'])[:200]}")


if __name__ == "__main__":
    _cli()
