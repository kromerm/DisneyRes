"""
Reservation monitor — polls the WDW dining API on a fixed interval and
alerts when at least one slot becomes available.
"""

from __future__ import annotations

import logging
import os
import random
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Any

from rich.console import Console
from rich.panel import Panel

from wdw_api import WDWDiningAPI

logger = logging.getLogger(__name__)
console = Console()

# Default poll interval (seconds).  Override with env var CHECK_INTERVAL_SECONDS.
DEFAULT_INTERVAL: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))  # 5 min

# Add up to ±JITTER_SECONDS of random offset so requests don't follow a
# perfectly predictable cadence.
JITTER_SECONDS: int = 30

# How many consecutive API errors before we temporarily back off
ERROR_BACKOFF_THRESHOLD: int = 3
ERROR_BACKOFF_SECONDS: int = 600  # 10 min back-off after repeated failures


class ReservationMonitor:
    """
    Continuously checks for Disney World dining reservation availability.

    Parameters
    ----------
    restaurant_id : str
        WDW facility entity ID.
    restaurant_name : str
        Human-readable name (used in output and notifications).
    date : str
        Reservation date in ``YYYY-MM-DD`` format.
    party_size : int
        Number of guests.
    start_time : str
        Earliest acceptable slot time (``HH:MM`` 24-hour).
    end_time : str
        Latest acceptable slot time (``HH:MM`` 24-hour).
    interval : int
        Seconds between checks (default: 300).
    stop_on_first : bool
        If True, stop monitoring after the first availability is found.
        If False, continue monitoring until interrupted.
    """

    def __init__(
        self,
        restaurant_id: str,
        restaurant_name: str,
        restaurant_slug: str,
        date: str,
        party_size: int,
        start_time: str,
        end_time: str,
        interval: int = DEFAULT_INTERVAL,
        stop_on_first: bool = True,
        email: str = "",
        password: str = "",
    ) -> None:
        self.restaurant_id = restaurant_id
        self.restaurant_name = restaurant_name
        self.restaurant_slug = restaurant_slug
        self.date = date
        self.party_size = party_size
        self.start_time = start_time
        self.end_time = end_time
        self.interval = interval
        self.stop_on_first = stop_on_first
        # Resolve credentials: constructor args override env vars
        self.email    = email    or os.getenv("DISNEYRES_EMAIL",    "")
        self.password = password or os.getenv("DISNEYRES_PASSWORD", "")

        self._api = WDWDiningAPI()
        self._check_count: int = 0
        self._error_streak: int = 0
        self._running: bool = False
        self._found_once: bool = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def check_once(self) -> tuple[bool, list[dict[str, Any]]]:
        """
        Perform a single availability check.

        Tries the Playwright browser-based checker first (most reliable),
        then falls back to the direct HTTP API if Playwright is unavailable.

        Returns
        -------
        (found, slots)
            *found* is True when at least one slot is bookable.
            *slots* is the list of available slot dicts.
        """
        self._check_count += 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(
            f"[dim][{ts}][/dim]  Check [cyan]#{self._check_count}[/cyan]  "
            f"[bold]{self.restaurant_name}[/bold] · {self.date} · "
            f"{self.start_time}–{self.end_time} · party of {self.party_size}"
        )

        try:
            found, slots = self._check_playwright()
        except Exception as exc:
            logger.debug("Playwright check failed (%s), falling back to HTTP API", exc)
            found, slots = self._check_api()

        if found:
            console.print(
                f"  [bold green]✓ AVAILABLE![/bold green]  "
                f"{len(slots)} slot(s) found:"
            )
            for slot in slots[:15]:
                t = slot.get("time") or slot.get("startTime") or "?"
                period = slot.get("mealPeriod", "")
                suffix = f"  [dim]({period})[/dim]" if period else ""
                console.print(f"    [green]→ {t}[/green]{suffix}")
        else:
            console.print("  [yellow]No availability.[/yellow]")

        return found, slots

    def _check_playwright(self) -> tuple[bool, list[dict[str, Any]]]:
        """Use a real browser (via Playwright) to check availability."""
        from playwright_checker import check_availability as pw_check  # noqa: PLC0415

        result = pw_check(
            slug=self.restaurant_slug,
            date=self.date,
            party_size=self.party_size,
            start_time=self.start_time,
            end_time=self.end_time,
            headless=True,
            email=self.email,
            password=self.password,
        )
        return result["found"], result["slots"]

    def _check_api(self) -> tuple[bool, list[dict[str, Any]]]:
        """Fall back to the direct HTTP API check."""
        try:
            data = self._api.check_availability(
                restaurant_id=self.restaurant_id,
                date=self.date,
                party_size=self.party_size,
                start_time=self.start_time,
                end_time=self.end_time,
            )
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            self._error_streak += 1
            console.print(
                f"  [red]API Error:[/red] {exc}"
                + (
                    f"  [dim](streak: {self._error_streak})[/dim]"
                    if self._error_streak > 1
                    else ""
                )
            )
            logger.exception("Availability check failed")
            return False, []

        self._error_streak = 0
        slots = self._api.parse_availability(data)
        return bool(slots), slots

    def start(self) -> None:
        """
        Enter the monitoring loop.  Blocks until the user interrupts or
        (if *stop_on_first* is True) until availability is found.
        """
        self._running = True
        self._found_once = False
        self._print_banner()
        console.print("[dim]Press Ctrl+C to stop.[/dim]\n")
        self._email_started()

        try:
            while self._running:
                found, slots = self.check_once()

                if found:
                    self._found_once = True
                    self._alert(slots)
                    if self.stop_on_first:
                        break
                    # Ask whether to keep watching
                    console.print()
                    try:
                        answer = input("Keep monitoring for more slots? [y/N] ").strip().lower()
                    except EOFError:
                        answer = "n"
                    if answer != "y":
                        break
                    console.print()

                if not self._running:
                    break

                # Back off if the API has been repeatedly failing
                sleep_secs = self._sleep_duration()
                next_at = (datetime.now() + timedelta(seconds=sleep_secs)).strftime("%H:%M:%S")
                console.print(
                    f"  [dim]Next check at {next_at} "
                    f"(~{sleep_secs // 60} min).[/dim]\n"
                )
                time.sleep(sleep_secs)

        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped.[/yellow]")
            if not self._found_once:
                self._email_not_found()
        else:
            # Loop exited normally without ever finding a slot
            if not self._found_once:
                self._email_not_found()
        finally:
            self._running = False
            console.print(f"[dim]Total checks performed: {self._check_count}[/dim]")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sleep_duration(self) -> int:
        """Return sleep seconds, with jitter and optional error back-off."""
        if self._error_streak >= ERROR_BACKOFF_THRESHOLD:
            console.print(
                f"  [yellow]Too many errors — backing off for "
                f"{ERROR_BACKOFF_SECONDS // 60} minutes.[/yellow]"
            )
            return ERROR_BACKOFF_SECONDS
        jitter = random.randint(-JITTER_SECONDS, JITTER_SECONDS)
        return max(60, self.interval + jitter)

    def _print_banner(self) -> None:
        console.print(
            Panel(
                f"[bold]Restaurant:[/bold]  {self.restaurant_name}\n"
                f"[bold]Date:[/bold]        {self.date}\n"
                f"[bold]Time window:[/bold] {self.start_time} – {self.end_time}\n"
                f"[bold]Party size:[/bold]  {self.party_size}\n"
                f"[bold]Poll interval:[/bold] every ~{self.interval // 60} min",
                title="[bold blue]🏰  Disney Reservation Monitor[/bold blue]",
                border_style="blue",
                padding=(0, 2),
            )
        )

    def _alert(self, slots: list[dict[str, Any]]) -> None:
        """Fire all configured alert channels."""
        console.print()
        console.print("=" * 60)
        console.print("[bold green]✨  RESERVATION AVAILABLE — BOOK NOW! ✨[/bold green]")
        console.print(
            "  [link=https://disneyworld.disney.go.com/dining/]"
            "https://disneyworld.disney.go.com/dining/[/link]"
        )
        console.print("=" * 60)
        console.print()

        self._desktop_notification()
        self._email_notification(slots)

    def _desktop_notification(self) -> None:
        try:
            from plyer import notification  # type: ignore[import]

            notification.notify(
                title="🏰 Disney Reservation Available!",
                message=(
                    f"{self.restaurant_name} has openings on {self.date} "
                    f"for {self.party_size} guest(s). Book now!"
                ),
                app_name="DisneyRes",
                timeout=30,
            )
        except Exception as exc:
            logger.debug("Desktop notification failed: %s", exc)

    def _email_notification(self, slots: list[dict[str, Any]]) -> None:
        """Send an availability-found e-mail alert."""
        slot_lines = "\n".join(
            f"  • {s.get('time', s.get('startTime', '?'))}  {s.get('mealPeriod', '')}".strip()
            for s in slots[:20]
        ) or "  (check the Disney site for details)"

        subject = f"🏰 Disney Dining Available: {self.restaurant_name} on {self.date}"
        body = (
            f"A reservation slot is now available!\n\n"
            f"Restaurant : {self.restaurant_name}\n"
            f"Date       : {self.date}\n"
            f"Party size : {self.party_size}\n"
            f"Slots found:\n{slot_lines}\n\n"
            f"Book now → https://disneyworld.disney.go.com/dining/\n"
        )
        self._send_email(subject, body)

    def _email_started(self) -> None:
        """Send a 'monitoring started' e-mail."""
        subject = f"\U0001f50d Disney Dining Search Started: {self.restaurant_name} on {self.date}"
        body = (
            f"The reservation monitor has started searching.\n\n"
            f"Restaurant : {self.restaurant_name}\n"
            f"Date       : {self.date}\n"
            f"Time window: {self.start_time} \u2013 {self.end_time}\n"
            f"Party size : {self.party_size}\n"
            f"Poll interval: every ~{self.interval // 60} min\n\n"
            f"You will receive another email when a slot is found or the search ends.\n"
        )
        self._send_email(subject, body)

    def _email_not_found(self) -> None:
        """Send a 'no reservation found, search stopped' e-mail."""
        subject = f"❌ Disney Dining Search Ended: {self.restaurant_name} on {self.date}"
        body = (
            f"The reservation monitor ran {self._check_count} check(s) "
            f"but found no available slots.\n\n"
            f"Restaurant : {self.restaurant_name}\n"
            f"Date       : {self.date}\n"
            f"Time window: {self.start_time} – {self.end_time}\n"
            f"Party size : {self.party_size}\n\n"
            f"Monitoring has been stopped. You can restart the monitor "
            f"or check manually at:\n"
            f"https://disneyworld.disney.go.com/dining/\n"
        )
        self._send_email(subject, body)

    def _send_email(self, subject: str, body: str) -> None:
        """
        Send an e-mail to all addresses in DISNEYRES_EMAIL_TO
        (comma-separated) if SMTP credentials are configured.
        """
        smtp_host = os.getenv("DISNEYRES_SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("DISNEYRES_SMTP_PORT", "587"))
        smtp_user = os.getenv("DISNEYRES_SMTP_USER", "")
        smtp_pass = os.getenv("DISNEYRES_SMTP_PASS", "")
        email_to_raw = os.getenv("DISNEYRES_EMAIL_TO", "")

        if not all([smtp_user, smtp_pass, email_to_raw]):
            return  # Email not configured — skip silently

        # Support comma-separated list of recipients
        recipients = [addr.strip() for addr in email_to_raw.split(",") if addr.strip()]
        if not recipients:
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            console.print("[green]  Email notification sent.[/green]")
            logger.info("Email alert sent to %s", ", ".join(recipients))
        except Exception as exc:
            logger.warning("Email notification failed: %s", exc)
            console.print(f"  [yellow]Email notification failed:[/yellow] {exc}")
