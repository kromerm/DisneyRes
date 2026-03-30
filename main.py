"""
Disney World Dining Reservation Monitor
========================================
Interactive CLI agent that watches for open dining reservations and
alerts you the moment a slot becomes available.

Usage
-----
Interactive mode (guided prompts):
    python main.py

Non-interactive / scripted mode:
    python main.py \\
        --restaurant "be our guest" \\
        --date 2026-06-15 \\
        --start 17:00 \\
        --end 21:00 \\
        --party 2

Single check (no loop):
    python main.py --check-once --restaurant "ohana" --date 2026-05-01 --party 4

List all known restaurants:
    python main.py --list

Enable debug logging:
    python main.py --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

import restaurants as resto_db
from monitor import DEFAULT_INTERVAL, ReservationMonitor

load_dotenv()  # Load .env if present (SMTP credentials, custom interval, etc.)  # Load .env if present (SMTP credentials, custom interval, etc.)

console = Console()


# ---------------------------------------------------------------------------
# Interactive helpers
# ---------------------------------------------------------------------------


def select_restaurant() -> dict:
    console.print("\n[bold]Step 1 — Restaurant[/bold]")
    console.print(
        "[dim]Search by name or park, e.g. "
        "[italic]be our guest[/italic], "
        "[italic]ohana[/italic], "
        "[italic]epcot[/italic], "
        "[italic]animal kingdom[/italic][/dim]\n"
    )

    while True:
        query = Prompt.ask("[cyan]Search[/cyan]").strip()
        if not query:
            continue

        matches = resto_db.search(query)
        if not matches:
            console.print(
                f"[yellow]No restaurants found for «{query}». Try again.[/yellow]\n"
            )
            continue

        if len(matches) == 1:
            r = matches[0]
            console.print(
                f"  Found: [bold green]{r['name']}[/bold green]  [dim]({r['park']})[/dim]"
            )
            if Confirm.ask("  Is this correct?", default=True):
                return r
            continue

        # Multiple matches
        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Restaurant")
        table.add_column("Location", style="dim")
        for i, r in enumerate(matches, 1):
            table.add_row(str(i), r["name"], r["park"])
        console.print(table)

        choice_str = Prompt.ask(
            f"[cyan]Select[/cyan] [dim](1–{len(matches)}, or 0 to search again)[/dim]"
        )
        try:
            choice = int(choice_str)
        except ValueError:
            continue
        if choice == 0:
            continue
        if 1 <= choice <= len(matches):
            return matches[choice - 1]


# Disney allows dining reservations up to 60 days in advance.
DISNEY_BOOKING_WINDOW_DAYS = 60


def select_date() -> str:
    console.print("\n[bold]Step 2 — Date[/bold]")
    today = date.today()
    max_future = today + timedelta(days=DISNEY_BOOKING_WINDOW_DAYS)

    while True:
        raw = Prompt.ask("[cyan]Reservation date[/cyan] [dim](YYYY-MM-DD)[/dim]").strip()
        try:
            chosen = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            console.print("[red]Invalid format. Use YYYY-MM-DD (e.g. 2026-06-15).[/red]")
            continue
        if chosen < today:
            console.print("[red]Date cannot be in the past.[/red]")
            continue
        if chosen > max_future:
            console.print(
                f"[red]Disney only opens reservations {DISNEY_BOOKING_WINDOW_DAYS} days in advance.[/red] "
                f"[dim]The furthest bookable date today is {max_future.strftime('%Y-%m-%d')}.[/dim]"
            )
            continue
        return raw


def select_time_range() -> tuple[str, str]:
    console.print("\n[bold]Step 3 — Time Window[/bold]")
    console.print("[dim]Choose a meal period or enter a custom range (24-hour clock).[/dim]\n")

    presets = [
        ("1", "Breakfast    07:30 – 10:30", "07:30", "10:30"),
        ("2", "Lunch        11:30 – 14:30", "11:30", "14:30"),
        ("3", "Dinner       17:00 – 23:00", "17:00", "23:00"),
        ("4", "All day      07:00 – 23:00", "07:00", "23:00"),
        ("5", "Custom range", None, None),
    ]

    table = Table(show_header=False)
    table.add_column("#", style="cyan", width=4)
    table.add_column("")
    for num, label, *_ in presets:
        table.add_row(num, label)
    console.print(table)

    while True:
        choice = Prompt.ask("[cyan]Select[/cyan] [dim](1–5)[/dim]").strip()
        for num, _, start, end in presets:
            if choice == num:
                if start and end:
                    return start, end
                return _custom_time_range()
        console.print("[red]Enter a number between 1 and 5.[/red]")


def _custom_time_range() -> tuple[str, str]:
    while True:
        s_raw = Prompt.ask("[cyan]Start time[/cyan] [dim](HH:MM)[/dim]").strip()
        try:
            start_dt = datetime.strptime(s_raw, "%H:%M")
            break
        except ValueError:
            console.print("[red]Use HH:MM format, e.g. 17:30[/red]")

    while True:
        e_raw = Prompt.ask("[cyan]End time  [/cyan] [dim](HH:MM)[/dim]").strip()
        try:
            end_dt = datetime.strptime(e_raw, "%H:%M")
            if end_dt <= start_dt:
                console.print("[red]End time must be after start time.[/red]")
                continue
            return s_raw, e_raw
        except ValueError:
            console.print("[red]Use HH:MM format, e.g. 21:00[/red]")


def select_party_size() -> int:
    console.print("\n[bold]Step 4 — Party Size[/bold]")
    while True:
        size = IntPrompt.ask("[cyan]Number of guests[/cyan] [dim](1–20)[/dim]")
        if 1 <= size <= 20:
            return size
        console.print("[red]Party size must be between 1 and 20.[/red]")


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def list_restaurants() -> None:
    parks: dict[str, list[dict]] = {}
    for r in resto_db.all_unique():
        parks.setdefault(r["park"], []).append(r)

    console.print(Panel("[bold]Known WDW Restaurants[/bold]", border_style="blue"))
    for park_name in sorted(parks):
        console.print(f"\n[bold]{park_name}[/bold]")
        for r in parks[park_name]:
            console.print(f"  [cyan]•[/cyan] {r['name']}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="disneyres",
        description="Monitor WDW dining reservations and alert when a slot opens.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--restaurant", "-r",
        metavar="NAME",
        help="Restaurant name or search term (e.g. 'be our guest')",
    )
    p.add_argument(
        "--date", "-d",
        metavar="YYYY-MM-DD",
        help="Desired reservation date",
    )
    p.add_argument(
        "--start", "-s",
        metavar="HH:MM",
        help="Earliest acceptable time slot (24-hour)",
        default="07:00",
    )
    p.add_argument(
        "--end", "-e",
        metavar="HH:MM",
        help="Latest acceptable time slot (24-hour)",
        default="23:00",
    )
    p.add_argument(
        "--party", "-p",
        metavar="N",
        type=int,
        help="Party size (1–20)",
    )
    p.add_argument(
        "--interval",
        metavar="SECONDS",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Poll interval in seconds (default: {DEFAULT_INTERVAL})",
    )
    p.add_argument(
        "--check-once",
        action="store_true",
        help="Run a single check and exit (no continuous loop)",
    )
    p.add_argument(
        "--keep-going",
        action="store_true",
        help="Don't stop after the first availability is found; keep monitoring",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List all known restaurants and exit",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    p.add_argument(
        "--email",
        metavar="EMAIL",
        default="",
        help="MyDisney account email (overrides DISNEYRES_EMAIL env var)",
    )
    p.add_argument(
        "--password",
        metavar="PASSWORD",
        default="",
        help="MyDisney account password (overrides DISNEYRES_PASSWORD env var)",
    )
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=[
            logging.FileHandler("disneyres.log", encoding="utf-8"),
        ],
    )
    if args.verbose:
        logging.getLogger().addHandler(logging.StreamHandler())

    if args.list:
        list_restaurants()
        return

    console.print(
        Panel(
            "[bold]Disney World Dining Reservation Monitor[/bold]\n"
            "[dim]Polls the WDW availability API every 5 minutes and alerts "
            "when a slot opens.[/dim]",
            border_style="blue",
            padding=(0, 2),
        )
    )

    # -------------------------------------------------------------------
    # Gather inputs — CLI args take priority; fall back to interactive
    # -------------------------------------------------------------------
    try:
        # Restaurant
        if args.restaurant:
            matches = resto_db.search(args.restaurant)
            if not matches:
                console.print(
                    f"[red]No restaurant found matching «{args.restaurant}». "
                    "Use --list to see all options.[/red]"
                )
                sys.exit(1)
            if len(matches) > 1:
                console.print(
                    f"[yellow]Multiple matches for «{args.restaurant}» — "
                    "using first result:[/yellow]"
                )
            restaurant = matches[0]
            console.print(
                f"  Restaurant: [bold]{restaurant['name']}[/bold]  "
                f"[dim]({restaurant['park']})[/dim]"
            )
        else:
            restaurant = select_restaurant()

        # Date
        if args.date:
            # Validate the supplied date
            try:
                chosen_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            except ValueError:
                console.print("[red]--date must be in YYYY-MM-DD format.[/red]")
                sys.exit(1)
            today = date.today()
            max_future = today + timedelta(days=DISNEY_BOOKING_WINDOW_DAYS)
            if chosen_date < today:
                console.print("[red]--date cannot be in the past.[/red]")
                sys.exit(1)
            if chosen_date > max_future:
                console.print(
                    f"[red]--date is outside Disney's {DISNEY_BOOKING_WINDOW_DAYS}-day booking window.[/red] "
                    f"[dim]The furthest bookable date today is {max_future.strftime('%Y-%m-%d')}.[/dim]"
                )
                sys.exit(1)
            reservation_date = args.date
        else:
            reservation_date = select_date()

        # Time range
        if args.start and args.end and (args.restaurant or args.date):
            # Only skip the prompt if the user is in non-interactive mode
            start_time, end_time = args.start, args.end
        elif args.restaurant and args.date:
            start_time, end_time = args.start, args.end
        else:
            start_time, end_time = select_time_range()

        # Party size
        if args.party:
            if not (1 <= args.party <= 20):
                console.print("[red]Party size must be between 1 and 20.[/red]")
                sys.exit(1)
            party_size = args.party
        else:
            party_size = select_party_size()

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(0)

    # -------------------------------------------------------------------
    # Confirm and start
    # -------------------------------------------------------------------
    # Resolve credentials (CLI > env var).  Prompt interactively if needed.
    import os  # noqa: PLC0415
    disney_email    = args.email    or os.getenv("DISNEYRES_EMAIL",    "")
    disney_password = args.password or os.getenv("DISNEYRES_PASSWORD", "")

    if not disney_email or not disney_password:
        console.print(
            "\n[yellow]Disney credentials not found.[/yellow]  "
            "These are needed to log in to the reservation system.\n"
            "[dim](You can also set DISNEYRES_EMAIL and DISNEYRES_PASSWORD in your .env file.)[/dim]"
        )
        try:
            if not disney_email:
                disney_email = Prompt.ask("[cyan]MyDisney email[/cyan]").strip()
            if not disney_password:
                from rich.prompt import Prompt as _P  # noqa: PLC0415
                disney_password = _P.ask("[cyan]MyDisney password[/cyan]", password=True)
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            sys.exit(0)
    console.print(
        Panel(
            f"[bold]Restaurant:[/bold]  {restaurant['name']}\n"
            f"[bold]Location:[/bold]    {restaurant['park']}\n"
            f"[bold]Date:[/bold]        {reservation_date}\n"
            f"[bold]Time window:[/bold] {start_time} – {end_time}\n"
            f"[bold]Party size:[/bold]  {party_size}\n"
            f"[bold]Mode:[/bold]        "
            + ("Single check" if args.check_once else f"Continuous (every ~{args.interval // 60} min)"),
            title="[bold]Summary[/bold]",
            border_style="green",
            padding=(0, 2),
        )
    )

    if not args.check_once:
        try:
            if not Confirm.ask("\nStart monitoring?", default=True):
                console.print("Cancelled.")
                sys.exit(0)
        except KeyboardInterrupt:
            sys.exit(0)

    monitor = ReservationMonitor(
        restaurant_id=restaurant["id"],
        restaurant_name=restaurant["name"],
        restaurant_slug=resto_db.derive_slug(restaurant),
        date=reservation_date,
        party_size=party_size,
        start_time=start_time,
        end_time=end_time,
        interval=args.interval,
        stop_on_first=not args.keep_going,
        email=disney_email,
        password=disney_password,
    )

    if args.check_once:
        monitor_once = ReservationMonitor(
            restaurant_id=restaurant["id"],
            restaurant_name=restaurant["name"],
            restaurant_slug=resto_db.derive_slug(restaurant),
            date=reservation_date,
            party_size=party_size,
            start_time=start_time,
            end_time=end_time,
            interval=args.interval,
            stop_on_first=True,
            email=disney_email,
            password=disney_password,
        )
        found, slots = monitor_once.check_once()
        if found:
            console.print(
                "\n[bold green]✓ Availability found![/bold green]  "
                "Book at: [link=https://disneyworld.disney.go.com/dining/]"
                "https://disneyworld.disney.go.com/dining/[/link]"
            )
            sys.exit(0)
        else:
            console.print("\n[yellow]No availability at this time.[/yellow]")
            sys.exit(1)
    else:
        monitor.start()


if __name__ == "__main__":
    main()
