#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# 1. Auto-create virtual environment if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating virtual environment (.venv)..."
    python3 -m venv "$VENV_DIR"
fi

# 2. Auto-install dependencies if CLI is missing
if [ ! -f "$VENV_DIR/bin/burn-job" ]; then
    echo "[*] Installing dependencies..."
    "$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
    "$VENV_DIR/bin/pip" install -q -e "$SCRIPT_DIR"
fi

# 3. Default command if no arguments provided is run-cycle
if [ $# -eq 0 ]; then
    echo "[*] No command specified. Running full autonomous optimization cycle..."
    exec "$VENV_DIR/bin/burn-job" run-cycle
fi

# 4. Execute passed CLI command
exec "$VENV_DIR/bin/burn-job" "$@"
