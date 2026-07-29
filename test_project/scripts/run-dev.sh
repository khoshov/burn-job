#!/usr/bin/env bash
set -e

./scripts/kill-app.sh 2>/dev/null || true
echo "Starting sensorhub with dev profile (H2 in-memory)..."
mvn spring-boot:run -Dspring-boot.run.profiles=dev
