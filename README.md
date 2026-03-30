# DisneyRes — WDW Dining Reservation Monitor

An automated agent that continuously polls the Walt Disney World dining
availability API every 5 minutes and alerts you the moment a reservation
slot opens at your chosen restaurant.

---

## Features

- **Interactive CLI** — guided prompts walk you through every option
- **Non-interactive mode** — pass all options as flags for scripting
- **5-minute polling** with ±30-second jitter so requests look organic
- **Desktop notification** (Windows/macOS/Linux) via `plyer`
- **Audio alert** on Windows (three beeps via `winsound`)
- **Email notification** (optional — configure SMTP in `.env`)
- **Error back-off** — slows down automatically after repeated API failures
- **40+ restaurants** pre-loaded; add more by dropping facility IDs into `restaurants.py`

---

## Quick Start

### 1. Install dependencies

```bash
cd DisneyRes
pip install -r requirements.txt
python -m playwright install chromium   # one-time download
```

### 2. Set your MyDisney credentials

Disney's booking site requires a logged-in account to view availability.
Copy `.env.example` to `.env` and fill in your credentials:

```bash
copy .env.example .env
```

Edit `.env`:
```
DISNEYRES_EMAIL=you@example.com
DISNEYRES_PASSWORD=your_disney_password_here
```

Alternatively you can pass `--email` / `--password` on the command line,
or the agent will prompt you interactively if they're not set.

### 3. Run

**Interactive mode** (recommended for first use):

```bash
python main.py
```

You will be guided through four steps:
1. Search for a restaurant
2. Pick a date
3. Choose a time window (Breakfast / Lunch / Dinner / All day / Custom)
4. Enter party size

The agent then polls every 5 minutes and alerts you when a slot appears.

---

## Command-Line Reference

```
python main.py [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--restaurant NAME` | Restaurant name or search term |
| `--date YYYY-MM-DD` | Desired reservation date |
| `--start HH:MM` | Earliest acceptable time (24-hour, default `07:00`) |
| `--end HH:MM` | Latest acceptable time (24-hour, default `22:00`) |
| `--party N` | Party size 1–20 |
| `--interval SECONDS` | Poll interval (default `300`) |
| `--check-once` | Run one check and exit (exit 0 = found, exit 1 = none) |
| `--keep-going` | Don't stop after the first availability; keep monitoring |
| `--list` | Print all known restaurants and exit |
| `--verbose` | Enable debug logging to console and `disneyres.log` |

### Examples

```bash
# Watch Be Our Guest for a dinner slot in June for 2 people
python main.py --restaurant "be our guest" --date 2026-06-15 --start 17:00 --end 21:00 --party 2

# One-time check for 'Ohana availability (useful in scripts or Task Scheduler)
python main.py --check-once --restaurant ohana --date 2026-05-20 --party 3

# Show all known restaurants
python main.py --list
```

---

## Supported Restaurants

Run `python main.py --list` for the full current list.  Pre-loaded parks:

| Park / Resort | Example restaurants |
|---------------|---------------------|
| Magic Kingdom | Be Our Guest, Cinderella's Royal Table, Crystal Palace |
| EPCOT | Space 220, Le Cellier, Coral Reef, Garden Grill, Akershus, … |
| Hollywood Studios | Sci-Fi Dine-In, Brown Derby, Oga's Cantina |
| Animal Kingdom | Tiffins, Tusker House, Yak & Yeti |
| Resorts | 'Ohana, California Grill, Topolino's Terrace, Jiko, Sanaa, … |

### Adding a restaurant

1. Find the restaurant on <https://disneyworld.disney.go.com/dining/>
2. Open DevTools → Network → filter XHR/Fetch
3. Search for availability — note the `id` query parameter used
4. Add an entry to `RESTAURANTS` in `restaurants.py`:

```python
"my restaurant": {
    "id": "12345678",
    "name": "My Full Restaurant Name",
    "park": "Park / Resort Name",
},
```

---

## API Notes

Disney does not publish a public API. This tool uses the internal endpoint
used by their own dining finder page (`/finder/api/v1/dining/nextAvailabilitySearch/`).

**If the endpoint stops working:**
1. Open `https://disneyworld.disney.go.com/dining/` in Chrome
2. DevTools → Network → filter by Fetch/XHR
3. Trigger an availability search and inspect the request URL + parameters
4. Update `AVAILABILITY_URL` in `wdw_api.py` (or set env var `DISNEYRES_AVAILABILITY_URL`)

---

## Files

```
DisneyRes/
├── main.py          — CLI entry point (interactive + argument modes)
├── monitor.py       — Polling loop, notifications, back-off logic
├── wdw_api.py       — HTTP client for the WDW dining availability API
├── restaurants.py   — Restaurant name → facility ID directory
├── requirements.txt — Python dependencies
├── .env.example     — Environment variable template
└── disneyres.log    — Created at runtime; contains API debug output
```
