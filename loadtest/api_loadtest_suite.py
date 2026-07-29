#!/usr/bin/env python3
"""Auto-generated API Load Test Suite."""
import sys
import time
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor

ENDPOINTS = [
  {
    "path": "/api/light/compute",
    "http_method": "GET",
    "controller_class": "LightController",
    "method_name": "compute",
    "file_path": "test_project_light/src/main/java/com/lighttest/web/LightController.java",
    "line_number": 16,
    "query_params": []
  },
  {
    "path": "/api/light/match",
    "http_method": "GET",
    "controller_class": "LightController",
    "method_name": "match",
    "file_path": "test_project_light/src/main/java/com/lighttest/web/LightController.java",
    "line_number": 25,
    "query_params": []
  }
]

def run_request(host, ep, count):
    url = host.rstrip("/") + ep["path"]
    for _ in range(count):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LoadTestRunner/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:
            pass

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    requests_per_worker = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    print(f"Running load test against {host} (Concurrency: {concurrency})...")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for ep in ENDPOINTS:
            futures.append(executor.submit(run_request, host, ep, requests_per_worker))
        for f in futures:
            f.result()
    print("Load test execution complete.")

if __name__ == "__main__":
    main()
