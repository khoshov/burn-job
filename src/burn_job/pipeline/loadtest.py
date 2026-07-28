"""Load Test Generator Module."""

import json
import os
from typing import List

from burn_job.domain.endpoint import EndpointInfo
from burn_job.core.logging import setup_logger

logger = setup_logger("LoadtestGenerator")

class LoadtestGenerator:
    """Generates Python load test scripts for scanned Spring endpoints."""

    @staticmethod
    def generate_script(endpoints: List[EndpointInfo], output_script_path: str):
        os.makedirs(os.path.dirname(output_script_path), exist_ok=True)
        endpoints_json = json.dumps([e.to_dict() for e in endpoints], indent=2)

        script_code = f'''#!/usr/bin/env python3
"""Auto-generated API Load Test Suite."""
import sys
import time
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor

ENDPOINTS = {endpoints_json}

def run_request(host, ep, count):
    url = host.rstrip("/") + ep["path"]
    for _ in range(count):
        try:
            req = urllib.request.Request(url, headers={{"User-Agent": "LoadTestRunner/1.0"}})
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:
            pass

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    requests_per_worker = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    print(f"Running load test against {{host}} (Concurrency: {{concurrency}})...")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for ep in ENDPOINTS:
            futures.append(executor.submit(run_request, host, ep, requests_per_worker))
        for f in futures:
            f.result()
    print("Load test execution complete.")

if __name__ == "__main__":
    main()
'''
        with open(output_script_path, "w", encoding="utf-8") as f:
            f.write(script_code)
        logger.info(f"Generated load test script: {output_script_path}")
