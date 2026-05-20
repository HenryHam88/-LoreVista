#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "   LoreVista - Starting Backend + Frontend"
echo "=========================================="
echo

# Kill background jobs on Ctrl-C / exit so users don't get orphan processes.
BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
    if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Stopping backend (PID $BACKEND_PID) ..."
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "Stopping frontend (PID $FRONTEND_PID) ..."
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# ----- Pick Python (prefer backend/.venv if it exists) -----
if [[ -x "$SCRIPT_DIR/backend/.venv/bin/python" ]]; then
    PY="$SCRIPT_DIR/backend/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    PY=python
fi

# ----- Backend -----
echo "[1/3] Starting backend (FastAPI) on http://127.0.0.1:8000 ..."
(
    cd "$SCRIPT_DIR/backend"
    "$PY" main.py
) &
BACKEND_PID=$!

# ----- Wait for backend port -----
echo "[2/3] Waiting for backend to be ready ..."
for i in {1..30}; do
    if (echo > /dev/tcp/127.0.0.1/8000) 2>/dev/null; then
        echo "      Backend is up."
        break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        echo "[WARN] Backend did not respond after 30s, but continuing anyway."
    fi
done

# ----- Frontend -----
echo "[3/3] Starting frontend (Vite) on http://localhost:5173 ..."
(
    cd "$SCRIPT_DIR/frontend"
    npm run dev
) &
FRONTEND_PID=$!

# ----- Open browser (best-effort, non-fatal) -----
sleep 4
URL="http://localhost:5173"
if command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 || true            # macOS
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true        # Linux
fi

echo
echo "=========================================="
echo "   Running!"
echo "   Backend : http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "=========================================="
echo "Press Ctrl-C to stop both."
echo

# Block here until either child exits.
wait -n
