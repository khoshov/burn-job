#!/usr/bin/env bash
PID=$(lsof -ti:8080 || true)
if [ -n "$PID" ]; then
  echo "Killing process on port 8080 (PID: $PID)..."
  kill -9 $PID
else
  echo "No process running on port 8080."
fi
