#!/usr/bin/env bash
set -e

# Load Test Execution Script for Sensorhub / BadHibernate Demo
# Level: Hard Requirement

HOST="${HOST:-localhost:8080}"
CONCURRENCY="${CONCURRENCY:-1}"
REQUESTS="${REQUESTS:-200}"

echo "=========================================="
echo "🚀 Running Load Tests on ${HOST}"
echo "=========================================="

echo "[1/4] Testing N+1 Query Antipattern vs Optimal Endpoint..."
ab -n ${REQUESTS} -c ${CONCURRENCY} "http://${HOST}/api/demo/n-plus-one/good"

echo "[2/4] Testing In-Memory Filter vs Database Pagination Endpoint..."
ab -n ${REQUESTS} -c ${CONCURRENCY} "http://${HOST}/api/demo/in-memory-filter/good"

echo "[3/4] Testing Batch Save Performance Endpoint..."
curl -s -X POST "http://${HOST}/api/demo/save-in-loop/compare?count=${REQUESTS}"

echo ""
echo "[4/4] Testing Entity Projection Endpoint..."
ab -n ${REQUESTS} -c ${CONCURRENCY} "http://${HOST}/api/demo/entity-fetch/good"

echo "=========================================="
echo "✅ Load Test Execution Complete!"
echo "=========================================="
