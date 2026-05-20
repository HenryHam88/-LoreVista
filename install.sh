#!/usr/bin/env bash
set -euo pipefail

# Resolve the script's own directory so `cd` works regardless of CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "   LoreVista - One-Click Installer (macOS/Linux)"
echo "=========================================="
echo

# ----- Check Python -----
echo "[1/4] Checking Python ..."
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[ERROR] Python 3.10+ not found."
    echo "        macOS:   brew install python@3.11"
    echo "        Ubuntu:  sudo apt install python3 python3-pip python3-venv"
    exit 1
fi
"$PY" --version

# ----- Check Node.js -----
echo
echo "[2/4] Checking Node.js ..."
if ! command -v node >/dev/null 2>&1; then
    echo "[ERROR] Node.js 18+ not found."
    echo "        macOS:   brew install node"
    echo "        Ubuntu:  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs"
    exit 1
fi
node --version
if ! command -v npm >/dev/null 2>&1; then
    echo "[ERROR] npm not found. Please reinstall Node.js."
    exit 1
fi

# ----- Backend deps -----
echo
echo "[3/4] Installing backend dependencies (pip) ..."
echo "This may take a few minutes the first time."
cd "$SCRIPT_DIR/backend"

# Use venv when not running inside an active virtual env, to avoid polluting
# the system Python and to play nicely with PEP 668 (externally-managed envs).
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ ! -d ".venv" ]]; then
        echo "Creating virtual environment at backend/.venv ..."
        "$PY" -m venv .venv
    fi
    # shellcheck source=/dev/null
    source .venv/bin/activate
fi

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# ----- Create .env if missing -----
if [[ ! -f ".env" && -f ".env.example" ]]; then
    echo "Creating backend/.env from .env.example ..."
    cp .env.example .env
fi

# ----- Frontend deps -----
echo
echo "[4/4] Installing frontend dependencies (npm) ..."
cd "$SCRIPT_DIR/frontend"
npm install

echo
echo "=========================================="
echo "   Install completed successfully!"
echo "=========================================="
echo
echo "Next steps:"
echo "  1. The backend defaults to SQLite — no extra database setup needed."
echo "     (To use PostgreSQL, edit backend/.env and set DATABASE_URL.)"
echo "  2. Run ./start.sh to launch the app."
echo "  3. Open http://localhost:5173 and configure API Keys in the UI."
echo
