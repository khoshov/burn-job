#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="$SCRIPT_DIR/.venv/bin/burn-job"

if [ -f "$VENV_BIN" ]; then
    CMD="$VENV_BIN"
else
    CMD="burn-job"
fi

if [ $# -eq 0 ]; then
    exec "$CMD" run-cycle
else
    exec "$CMD" "$@"
fi
