#!/usr/bin/env bash
set -e

./scripts/kill-app.sh 2>/dev/null || true
echo "Starting sensorhub with load profile (embedded PostgreSQL)..."
mvn spring-boot:run -Dspring-boot.run.profiles=load
