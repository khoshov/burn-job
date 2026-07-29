#!/usr/bin/env bash
set -e

./scripts/kill-app.sh 2>/dev/null || true
echo "Starting sensorhub with load,leak profile..."
mvn spring-boot:run -Dspring-boot.run.profiles=load,leak
