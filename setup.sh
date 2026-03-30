#!/usr/bin/env bash
set -e

echo ""
echo " ====================================================="
echo "  Disney World Dining Reservation Monitor — Setup"
echo " ====================================================="
echo ""

# ── 1. Check Python ────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo " ERROR: python3 is not installed."
    echo " macOS:  brew install python"
    echo " Ubuntu: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PYVER=$(python3 --version)
echo " Python found: $PYVER"

# ── 2. Create virtual environment ──────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo ""
    echo " Creating virtual environment..."
    python3 -m venv .venv
    echo " Virtual environment created."
else
    echo " Virtual environment already exists, skipping creation."
fi

# ── 3. Install dependencies ────────────────────────────────────────────────────
echo ""
echo " Installing Python dependencies..."
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt
echo " Dependencies installed."

# ── 4. Install Playwright browser ─────────────────────────────────────────────
echo ""
echo " Installing Playwright browser (this may take a minute)..."
.venv/bin/python -m playwright install chromium
echo " Playwright browser installed."

# ── 5. Copy .env if not present ───────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo ""
    echo " Copying .env.example to .env ..."
    cp .env.example .env
    echo " Created .env  <<< EDIT THIS FILE with your Disney credentials >>>"
else
    echo ""
    echo " .env already exists, skipping copy."
fi

# ── 6. Done ───────────────────────────────────────────────────────────────────
echo ""
echo " ====================================================="
echo "  Setup complete!"
echo " ====================================================="
echo ""
echo " Next steps:"
echo "   1. Edit .env and fill in your MyDisney credentials"
echo "   2. Run the agent:"
echo ""
echo "      .venv/bin/python main.py"
echo ""
echo " Or for a one-time check:"
echo ""
echo '      .venv/bin/python main.py --check-once --restaurant "be our guest" --date 2026-06-15 --party 2'
echo ""
