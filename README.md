# DisneyRes — WDW Dining Reservation Monitor

An automated agent that continuously polls the Walt Disney World dining
availability API every 5 minutes and alerts you the moment a reservation
slot opens at your chosen restaurant.

---

## Features

- **Interactive CLI** — guided prompts walk you through every option
- **Non-interactive / scripted mode** — pass all options as CLI flags
- **Playwright-powered** — uses a real Chrome browser to replicate exactly what Disney's own website does, bypassing bot-detection
- **MyDisney login** — logs in automatically using your account credentials; session is cached so you are not asked to log in on every run
- **5-minute polling** with ±30-second random jitter
- **Email alerts** — notifies you when a search starts, when a slot is found, and when the search ends without finding anything; supports multiple recipients
- **Desktop notification** (Windows / macOS / Linux) via `plyer`
- **Booking-window validation** — rejects dates outside Disney's 60-day advance reservation window
- **Error back-off** — slows down automatically after repeated failures
- **60+ restaurants** pre-loaded (parks, resorts, and Disney Springs)

---

## Requirements

- **Python 3.10 or later** — <https://www.python.org/downloads/>
- **Google Chrome** — must already be installed on the machine (the agent drives your real Chrome installation, not a bundled browser)
- **A MyDisney account** — <https://disneyworld.disney.go.com/>

---

## Installation

### Windows

```bat
git clone https://github.com/kromerm/DisneyRes.git
cd DisneyRes
setup.bat
```

`setup.bat` will:
1. Create a Python virtual environment (`.venv`)
2. Install all Python dependencies
3. Download the Playwright Chromium driver
4. Copy `.env.example` → `.env` (only if `.env` does not already exist)

### macOS / Linux

```bash
git clone https://github.com/kromerm/DisneyRes.git
cd DisneyRes
chmod +x setup.sh
./setup.sh
```

### Manual installation (any platform)

```bash
git clone https://github.com/kromerm/DisneyRes.git
cd DisneyRes
python -m venv .venv

# Windows
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m playwright install chromium

# macOS / Linux
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

---

## Configuration

Copy `.env.example` to `.env` (the setup scripts do this for you) and fill in your values:

```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS / Linux
```

### Required

```dotenv
DISNEYRES_EMAIL=you@example.com
DISNEYRES_PASSWORD=your_disney_password
```

These are your **Walt Disney World / MyDisney** account credentials.

### Optional — Email alerts

When all four values are set, the agent sends emails when a search starts, when a slot is found, and when the search ends.

```dotenv
DISNEYRES_SMTP_HOST=smtp.gmail.com       # default
DISNEYRES_SMTP_PORT=587                  # default (STARTTLS)
DISNEYRES_SMTP_USER=you@gmail.com
DISNEYRES_SMTP_PASS=xxxx xxxx xxxx xxxx  # Gmail App Password
DISNEYRES_EMAIL_TO=you@example.com, partner@example.com  # comma-separated
```

> **Gmail users:** You must use an [App Password](https://myaccount.google.com/apppasswords), not your regular Gmail password.
> Enable 2-Step Verification on your Google account first, then create an App Password.

### Optional — Polling interval

```dotenv
CHECK_INTERVAL_SECONDS=300   # default: 5 minutes
```

---

## Usage

Activate the virtual environment first:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Then run:

### Interactive mode (recommended for first use)

```bash
python main.py
```

The agent guides you through four steps:
1. Search for a restaurant
2. Pick a date (must be within Disney's 60-day booking window)
3. Choose a time window — Breakfast / Lunch / Dinner / All day / Custom
4. Enter party size

It then polls every ~5 minutes and alerts you when a slot appears.

### Non-interactive / scripted mode

```bash
# Watch Be Our Guest for a dinner slot for 2 people
python main.py --restaurant "be our guest" --date 2026-06-15 --start 17:00 --end 23:00 --party 2

# One-time check (useful in Task Scheduler / cron)
python main.py --check-once --restaurant ohana --date 2026-05-20 --party 3

# Keep monitoring after the first slot is found
python main.py --restaurant "space 220" --date 2026-04-10 --party 4 --keep-going

# Show all known restaurants
python main.py --list
```

### All flags

| Flag | Default | Description |
|------|---------|-------------|
| `--restaurant NAME` | — | Restaurant name or partial search term |
| `--date YYYY-MM-DD` | — | Desired reservation date (within 60-day window) |
| `--start HH:MM` | `07:00` | Earliest acceptable time slot (24-hour) |
| `--end HH:MM` | `23:00` | Latest acceptable time slot (24-hour) |
| `--party N` | — | Party size 1–20 |
| `--interval SECONDS` | `300` | Seconds between polls |
| `--check-once` | off | Run one check and exit |
| `--keep-going` | off | Continue after the first slot is found |
| `--list` | — | Print all known restaurants and exit |
| `--verbose` | off | Enable debug logging |
| `--email EMAIL` | `.env` | Override MyDisney email |
| `--password PASS` | `.env` | Override MyDisney password |

---

## Automating with Task Scheduler (Windows)

To run automatically in the background:

1. Open **Task Scheduler** → *Create Basic Task*
2. Set the trigger (e.g., daily at 8 AM)
3. Set the action to:
   - **Program:** `C:\path\to\DisneyRes\.venv\Scripts\python.exe`
   - **Arguments:** `main.py --restaurant "be our guest" --date 2026-06-15 --party 2 --check-once`
   - **Start in:** `C:\path\to\DisneyRes`

Or wrap it in a `.bat` file:

```bat
@echo off
cd /d C:\path\to\DisneyRes
.venv\Scripts\python main.py --restaurant "be our guest" --date 2026-06-15 --party 2
```

## Automating with cron (macOS / Linux)

```cron
# Check every 5 minutes, 7 AM – 11 PM
*/5 7-23 * * * cd /path/to/DisneyRes && .venv/bin/python main.py --check-once --restaurant "be our guest" --date 2026-06-15 --party 2 >> /tmp/disneyres.log 2>&1
```

---

## Supported Restaurants

Run `python main.py --list` for the full current list. Pre-loaded areas:

| Area | Example restaurants |
|------|---------------------|
| Magic Kingdom | Be Our Guest, Cinderella's Royal Table, Crystal Palace |
| EPCOT | Space 220, Coral Reef, Garden Grill, Akershus, Teppan Edo, … |
| Hollywood Studios | Sci-Fi Dine-In, Brown Derby, Oga's Cantina |
| Animal Kingdom | Tiffins, Tusker House, Yak & Yeti |
| WDW Resorts | 'Ohana, California Grill, Topolino's Terrace, Jiko, Sanaa, … |
| Disney Springs | The BOATHOUSE, Paddlefish, STK, Jaleo, Homecomin', … |

### Adding a restaurant

1. Find the restaurant on <https://disneyworld.disney.go.com/dining/>
2. Note the URL slug (e.g., `boathouse-restaurant`)
3. Add an entry to `RESTAURANTS` in `restaurants.py`:

```python
"my restaurant": {
    "id": "",                     # optional — fill in from DevTools if needed
    "name": "My Restaurant Name",
    "park": "Disney Springs",
    "slug": "my-restaurant-slug", # from the Disney URL
},
```

---

## Troubleshooting

**Login fails / MFA prompt**
- Make sure `DISNEYRES_EMAIL` and `DISNEYRES_PASSWORD` in `.env` are correct
- If Disney sends a 6-digit email code, the agent will prompt you to enter it in the terminal
- Once logged in successfully, the session is saved to `browser_session.json` and reused on future runs

**"Date is outside Disney's 60-day booking window"**
- Disney only opens reservations 60 days in advance; set `--date` to within that window

**No slots found but you know some exist**
- Run with `--verbose` to see all captured API responses
- Disney's availability API returns date-keyed data — make sure your `--start` / `--end` window covers the meal period times

**Email not sending**
- Check that all four `DISNEYRES_SMTP_*` and `DISNEYRES_EMAIL_TO` values are set in `.env`
- Gmail requires an [App Password](https://myaccount.google.com/apppasswords) — 2-Step Verification must be enabled first

---

## Project Structure

```
DisneyRes/
├── main.py               CLI entry point (interactive + flag modes)
├── monitor.py            Polling loop, email alerts, back-off logic
├── playwright_checker.py Real-browser availability checker (primary)
├── wdw_api.py            Direct HTTP API fallback client
├── restaurants.py        Restaurant name → slug / facility ID directory
├── requirements.txt      Python dependencies
├── setup.bat             One-step Windows installer
├── setup.sh              One-step macOS / Linux installer
├── .env.example          Environment variable template
└── .gitignore            Excludes .env, browser_session.json, logs
```

---

## Security Notes

- `.env` and `browser_session.json` are listed in `.gitignore` and will **never** be committed
- Your Disney password is only stored locally in `.env` and is never logged or transmitted anywhere other than the Disney login page
- Use a [Gmail App Password](https://myaccount.google.com/apppasswords) rather than your real Gmail password for SMTP

