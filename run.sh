#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"

# Use .venv python if present, otherwise system python3 / python
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

if [ $# -eq 0 ]; then
    exec "$PYTHON_BIN" -m burn_job.cli run-cycle
else
    exec "$PYTHON_BIN" -m burn_job.cli "$@"
fi
