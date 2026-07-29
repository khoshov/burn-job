#!/usr/bin/env bash
curl -X POST http://localhost:8080/internal/reset || echo "App not running or reset failed"
