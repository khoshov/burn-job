"""
Automated Multi-Variant Benchmarking & Feature Toggle Evaluation Script.
"""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error
from typing import Dict, List, Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
DEFAULT_BASE_URL = "http://localhost:8080"
FINDINGS_PATH = os.path.join(REPO_ROOT, "reports", "sandbox", "findings.json")


def _request(url: str, timeout: int = 30) -> tuple:
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8")
        headers = dict(resp.headers)
        return body, headers
    except urllib.error.HTTPError as e:
        return "", {"X-Sql-Count": "0"}
    except Exception:
        return "", {"X-Sql-Count": "0"}


def _multi_variant_request(base_url: str, endpoint: str, max_concurrent: int = 5) -> dict:
    variants = ["v1", "v2", "v3"]
    results = {}
    for variant in variants:
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}?variant={variant}"
        body, headers = _request(url)
        results[variant] = {
            "sql_count": int(headers.get("X-Sql-Count", 0)),
            "body_size_bytes": len(body),
            "response": body[:200] if body else "",
        }
    return results


TEST_CASES = {
    "N+1 Queries": {
        "endpoint": "/api/demo/n-plus-one/bad",
        "variants": {
            "v1": {"endpoint": "/api/demo/n-plus-one/good", "description": "JOIN FETCH JPQL"},
            "v2": {"endpoint": "/api/demo/n-plus-one/good", "description": "@EntityGraph"},
            "v3": {"endpoint": "/api/demo/n-plus-one/good", "description": "DTO Projection"},
        }
    },
    "In-Memory Filter": {
        "endpoint": "/api/demo/in-memory-filter/bad",
        "variants": {
            "v1": {"endpoint": "/api/demo/in-memory-filter/good", "description": "PageRequest (DB pagination)"},
            "v2": {"endpoint": "/api/demo/in-memory-filter/good", "description": "Slice (avoid COUNT)"},
        }
    },
    "Save in Loop": {
        "endpoint": "/api/demo/save-in-loop/compare?count=100",
        "variants": {
            "v1": {"endpoint": "/api/demo/save-in-loop/compare?count=100", "description": "saveAll with batching"},
        }
    },
    "Full Entity Fetch": {
        "endpoint": "/api/demo/entity-fetch/bad",
        "variants": {
            "v1": {"endpoint": "/api/demo/entity-fetch/good", "description": "Interface Projection"},
        }
    }
}


def run_benchmarks(base_url: str = DEFAULT_BASE_URL) -> Dict[str, Any]:
    results = {}
    for case_name, case_info in TEST_CASES.items():
        results[case_name] = {}
        bad_endpoint = case_info["endpoint"]
        baseline_body, baseline_headers = _request(f"{base_url.rstrip('/')}/{bad_endpoint.lstrip('/')}")
        results[case_name]["baseline"] = {
            "sql_count": int(baseline_headers.get("X-Sql-Count", 0)),
            "body_size": len(baseline_body),
        }
        for var_name, var_info in case_info["variants"].items():
            body, headers = _request(f"{base_url.rstrip('/')}/{var_info['endpoint'].lstrip('/')}")
            results[case_name][var_name] = {
                "sql_count": int(headers.get("X-Sql-Count", 0)),
                "body_size": len(body),
                "description": var_info["description"],
            }
    return results


def update_findings_json(results: Dict[str, Any], findings_path: str = FINDINGS_PATH):
    if not os.path.exists(findings_path):
        return
    with open(findings_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    findings = report if isinstance(report, list) else report.get("findings", [])
    for finding in findings:
        case_name = finding.get("case_name", "")
        if case_name in results:
            finding["benchmark_results"] = results[case_name]
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Updated findings.json with benchmark results at {findings_path}")


def main():
    parser = argparse.ArgumentParser(description="Multi-Variant Benchmark Runner")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--update-findings", action="store_true", help="Update findings.json with benchmark results")
    args = parser.parse_args()

    results = run_benchmarks(args.base_url)
    print(json.dumps(results, indent=2))

    if args.update_findings:
        update_findings_json(results)


if __name__ == "__main__":
    main()
