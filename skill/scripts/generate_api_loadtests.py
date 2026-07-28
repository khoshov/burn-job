#!/usr/bin/env python3
"""
API Load Test Generator & Micrometer Report Collector Skill.

Scans Spring Boot REST controllers in src/main/java, generates executable API load tests,
executes them against the application, queries Micrometer metrics (/actuator/metrics/http.server.requests),
and outputs a comprehensive performance report.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))


def scan_spring_controllers(src_dir: str) -> list:
    """Scans Java source files under src_dir for Spring @RestController / @RequestMapping annotations."""
    endpoints = []

    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith(".java"):
                continue

            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if "@RestController" not in content and "@Controller" not in content:
                continue

            # Class-level base path
            base_path = ""
            base_match = re.search(r'@RequestMapping\s*\(\s*["\']([^"\']+)["\']\s*\)', content)
            if base_match:
                base_path = base_match.group(1).rstrip("/")

            # Method-level mappings
            patterns = [
                (r'@GetMapping\s*\(\s*["\']([^"\']+)["\']\s*\)', "GET"),
                (r'@PostMapping\s*\(\s*["\']([^"\']+)["\']\s*\)', "POST"),
                (r'@PutMapping\s*\(\s*["\']([^"\']+)["\']\s*\)', "PUT"),
                (r'@DeleteMapping\s*\(\s*["\']([^"\']+)["\']\s*\)', "DELETE"),
                (r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']\s*,\s*method\s*=\s*RequestMethod\.(\w+)', "DYNAMIC"),
            ]

            for pattern, method in patterns:
                for match in re.finditer(pattern, content):
                    path = match.group(1)
                    http_method = method if method != "DYNAMIC" else match.group(2)
                    full_url_path = f"{base_path}/{path.lstrip('/')}"
                    endpoints.append({
                        "controller": file,
                        "method": http_method,
                        "path": full_url_path,
                    })

    return endpoints


def generate_loadtest_script(endpoints: list, output_script: str):
    """Generates a standalone Python API load-test script that can execute requests at scale."""
    os.makedirs(os.path.dirname(output_script) or ".", exist_ok=True)

    script_content = f'''#!/usr/bin/env python3
"""
Auto-generated API Load Test Suite.
Target Endpoints: {len(endpoints)}
"""

import concurrent.futures
import time
import urllib.request
import urllib.error
import sys

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
REQUESTS_PER_ENDPOINT = int(sys.argv[2]) if len(sys.argv) > 2 else 50
CONCURRENCY = int(sys.argv[3]) if len(sys.argv) > 3 else 5

ENDPOINTS = {json.dumps(endpoints, indent=4)}

def make_request(ep):
    url = f"{{BASE_URL}}{{ep['path']}}"
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
    print(f"🚀 Starting API Load Test: {{BASE_URL}} (Concurrency={{CONCURRENCY}}, Requests/EP={{REQUESTS_PER_ENDPOINT}})")
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

    print(f"✅ Load Test Completed in {{total_time:.2f}}s | Total Reqs: {{total_reqs}} | Overall RPS: {{rps:.1f}}")

if __name__ == "__main__":
    main()
'''
    with open(output_script, "w", encoding="utf-8") as f:
        f.write(script_content)

    os.chmod(output_script, 0o755)


def fetch_micrometer_metrics(base_url: str) -> dict:
    """Fetches Micrometer metrics from Spring Boot Actuator endpoint."""
    metrics_url = f"{base_url.rstrip('/')}/actuator/metrics/http.server.requests"
    try:
        req = urllib.request.Request(metrics_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def generate_report(endpoints: list, before_metrics: dict, after_metrics: dict, duration_sec: float, output_markdown: str, output_json: str):
    """Generates Markdown and JSON reports incorporating Micrometer results and RPS metrics."""
    timestamp = datetime.datetime.now().isoformat()

    def _extract_count(m_dict):
        if not m_dict or "measurements" not in m_dict:
            return 0
        for m in m_dict["measurements"]:
            if m.get("statistic") == "COUNT":
                return m.get("value", 0)
        return 0

    count_before = _extract_count(before_metrics)
    count_after = _extract_count(after_metrics)
    delta_count = max(0, count_after - count_before)
    rps = delta_count / max(duration_sec, 0.001)

    report_data = {
        "timestamp": timestamp,
        "duration_seconds": round(duration_sec, 2),
        "total_requests": int(delta_count),
        "overall_rps": round(rps, 1),
        "endpoints_scanned": len(endpoints),
        "endpoints": endpoints,
        "micrometer_metrics_after": after_metrics,
    }

    os.makedirs(os.path.dirname(output_json) or ".", exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    markdown_content = f"""# 📈 API Load Test & Micrometer Performance Report

**Timestamp:** `{timestamp}`  
**Scanned Controller Endpoints:** `{len(endpoints)}`  
**Load Test Duration:** `{duration_sec:.2f} s`  
**Micrometer Delta Requests:** `{int(delta_count)}`  
**Measured Overall RPS:** `{rps:.1f} req/s`  

---

## 🎯 Discovered REST Endpoints

| Controller | Method | Endpoint Path |
|---|---|---|
"""
    for ep in endpoints:
        markdown_content += f"| `{ep['controller']}` | `{ep['method']}` | `{ep['path']}` |\n"

    markdown_content += f"""
---

## 📊 Micrometer `http.server.requests` Metrics Summary

```json
{json.dumps(after_metrics, indent=2)}
```

---

## 💡 How to Read RPS and API Results in Micrometer
- **Total Requests (COUNT):** `{count_after}` (Delta during test: `{int(delta_count)}`)
- **Measured RPS:** `{rps:.1f} requests/sec`
- **Prometheus Query for Real-Time RPS:** `sum(rate(http_server_requests_seconds_count[1m]))`
- **Error Rate Query:** `sum(rate(http_server_requests_seconds_count{{status=~"5.."}}[1m])) / sum(rate(http_server_requests_seconds_count[1m])) * 100`
"""

    os.makedirs(os.path.dirname(output_markdown) or ".", exist_ok=True)
    with open(output_markdown, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Wrote Micrometer API report to {output_markdown} and {output_json}")


def main():
    parser = argparse.ArgumentParser(description="API Load Test Generator & Micrometer Collector Skill")
    parser.add_argument("--src-dir", default=os.path.join(REPO_ROOT, "src", "main", "java"), help="Path to Java source code")
    parser.add_argument("--host", default="http://localhost:8080", help="Target application host URL")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent load test threads")
    parser.add_argument("--requests", type=int, default=50, help="Number of requests per endpoint")
    parser.add_argument("--generate-only", action="store_true", help="Generate load test scripts without running them")
    parser.add_argument("--out-script", default=os.path.join(REPO_ROOT, "loadtest", "api_loadtest_suite.py"), help="Output path for load test script")
    parser.add_argument("--out-md", default=os.path.join(REPO_ROOT, "reports", "sandbox", "micrometer_api_report.md"), help="Output Markdown report path")
    parser.add_argument("--out-json", default=os.path.join(REPO_ROOT, "reports", "sandbox", "micrometer_api_results.json"), help="Output JSON results path")
    args = parser.parse_args()

    print(f"🔍 Scanning Spring controllers under: {args.src_dir}")
    endpoints = scan_spring_controllers(args.src_dir)
    print(f"  ✓ Discovered {len(endpoints)} REST API endpoints.")

    generate_loadtest_script(endpoints, args.out_script)
    print(f"  ✓ Generated API load test script at: {args.out_script}")

    if args.generate_only:
        print("Done (generate-only mode).")
        return

    print("📊 Measuring baseline Micrometer metrics...")
    before_metrics = fetch_micrometer_metrics(args.host)

    start_time = time.time()
    print(f"🚀 Executing API Load Test against {args.host}...")
    try:
        subprocess.run([sys.executable, args.out_script, args.host, str(args.requests), str(args.concurrency)], check=True)
    except Exception as e:
        print(f"⚠️ Load test execution note (app might be offline): {e}")

    duration_sec = time.time() - start_time
    print("📊 Measuring post-test Micrometer metrics...")
    after_metrics = fetch_micrometer_metrics(args.host)

    generate_report(endpoints, before_metrics, after_metrics, duration_sec, args.out_md, args.out_json)


if __name__ == "__main__":
    main()
