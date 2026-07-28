#!/usr/bin/env python3
"""
Auto-generated API Load Test Suite.
Target Endpoints: 16
"""

import concurrent.futures
import time
import urllib.request
import urllib.error
import sys

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
REQUESTS_PER_ENDPOINT = int(sys.argv[2]) if len(sys.argv) > 2 else 50
CONCURRENCY = int(sys.argv[3]) if len(sys.argv) > 3 else 5

ENDPOINTS = [
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/n-plus-one"
    },
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/n-plus-one/bad"
    },
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/n-plus-one/good"
    },
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/in-memory-filter"
    },
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/in-memory-filter/bad"
    },
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/in-memory-filter/good"
    },
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/entity-fetch"
    },
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/entity-fetch/bad"
    },
    {
        "controller": "AntipatternController.java",
        "method": "GET",
        "path": "/api/demo/entity-fetch/good"
    },
    {
        "controller": "AntipatternController.java",
        "method": "POST",
        "path": "/api/demo/save-in-loop"
    },
    {
        "controller": "AntipatternController.java",
        "method": "POST",
        "path": "/api/demo/save-in-loop/compare"
    },
    {
        "controller": "ProfilerController.java",
        "method": "GET",
        "path": "/api/profiler/status"
    },
    {
        "controller": "ProfilerController.java",
        "method": "POST",
        "path": "/api/profiler/start"
    },
    {
        "controller": "ProfilerController.java",
        "method": "POST",
        "path": "/api/profiler/stop"
    },
    {
        "controller": "ProfilerController.java",
        "method": "POST",
        "path": "/api/profiler/profile"
    },
    {
        "controller": "HomeController.java",
        "method": "GET",
        "path": "/"
    }
]

def make_request(ep):
    url = f"{BASE_URL}{ep['path']}"
    method = ep['method']
    start = time.time()
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception:
        status = 500
    elapsed = (time.time() - start) * 1000
    return ep['path'], method, status, elapsed

def main():
    print(f"🚀 Starting API Load Test: {BASE_URL} (Concurrency={CONCURRENCY}, Requests/EP={REQUESTS_PER_ENDPOINT})")
    start_time = time.time()
    results = []

    tasks = []
    for ep in ENDPOINTS:
        for _ in range(REQUESTS_PER_ENDPOINT):
            tasks.append(ep)

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(make_request, ep) for ep in tasks]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    total_time = time.time() - start_time
    total_reqs = len(results)
    rps = total_reqs / max(total_time, 0.001)

    print(f"✅ Load Test Completed in {total_time:.2f}s | Total Reqs: {total_reqs} | Overall RPS: {rps:.1f}")

if __name__ == "__main__":
    main()
