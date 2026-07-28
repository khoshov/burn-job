#!/usr/bin/env python3
"""
Automated Multi-Variant Benchmarking & Feature Toggle Evaluation Script.
Iterates over all candidate fix variants from FIX_VARIANTS.md for each detected anomaly,
measures performance (X-Sql-Count, latency, response size), identifies the optimal winning variant,
and updates evidence in findings.json.
"""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error
from typing import Dict, List, Any

DEFAULT_BASE_URL = "http://localhost:8080"
FINDINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports", "sandbox", "findings.json")

CASES = {
    "n-plus-one": {
        "title": "N+1 Query Problem (Department Employees)",
        "endpoint": "/api/demo/n-plus-one",
        "method": "GET",
        "variants": {
            "suboptimal": "1 + N Queries (findAll + lazy loop)",
            "v1": "JPQL JOIN FETCH (Variant 1.1)",
            "v2": "@EntityGraph Annotation (Variant 1.2)",
            "v3": "DTO Constructor Expression (Variant 1.4)"
        },
        "findings_file": "java/src/main/java/com/example/badhibernate/service/NPlusOneService.java"
    },
    "in-memory-filter": {
        "title": "In-Memory Filtering & Pagination Bloat",
        "endpoint": "/api/demo/in-memory-filter",
        "method": "GET",
        "params": {"status": "SHIPPED", "page": "0", "size": "10"},
        "variants": {
            "suboptimal": "Full table load into JVM Heap + Stream API",
            "v1": "Spring Data Pageable (Variant 8.1)",
            "v2": "Slice Pagination without COUNT(*) (Variant 3.3)",
            "v3": "Keyset / Seek Cursor Pagination (Variant 8.2)"
        },
        "findings_file": "java/src/main/java/com/example/badhibernate/service/InMemoryFilterService.java"
    },
    "save-in-loop": {
        "title": "Save Entities In Loop Without JDBC Batching",
        "endpoint": "/api/demo/save-in-loop",
        "method": "POST",
        "params": {"count": "200"},
        "variants": {
            "suboptimal": "N separate JDBC round-trips & INSERTs",
            "v1": "saveAll() with JDBC Batching (Variant 3.1)",
            "v2": "Spring JdbcTemplate batchUpdate (Variant 3.2)",
            "v3": "Hibernate StatelessSession Batch (Variant 3.3)"
        },
        "findings_file": "java/src/main/java/com/example/badhibernate/service/SaveInLoopService.java"
    },
    "entity-fetch": {
        "title": "Full Entity & LOB Fetching for DTOs",
        "endpoint": "/api/demo/entity-fetch",
        "method": "GET",
        "variants": {
            "suboptimal": "Full @Entity load with heavy @Lob column",
            "v1": "Spring Data Interface Projection (Variant 4.1)",
            "v2": "JPQL DTO Constructor Expression (Variant 4.2)"
        },
        "findings_file": "java/src/main/java/com/example/badhibernate/service/FullEntityFetchService.java"
    }
}

def make_request(base_url: str, endpoint: str, method: str = "GET", params: Dict[str, str] = None) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{endpoint}"
    if params:
        query_str = urllib.parse.urlencode(params)
        if method.upper() == "GET":
            url += f"?{query_str}"

    data = None
    if method.upper() == "POST" and params:
        data = urllib.parse.urlencode(params).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method.upper())
    
    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            body = resp.read()
            sql_count_header = resp.headers.get("X-Sql-Count")
            elapsed_header = resp.headers.get("X-Elapsed-Ms")
            
            sql_count = int(sql_count_header) if sql_count_header and sql_count_header.isdigit() else None
            server_elapsed = int(elapsed_header) if elapsed_header and elapsed_header.isdigit() else elapsed_ms

            return {
                "status": resp.status,
                "elapsed_ms": server_elapsed,
                "sql_count": sql_count,
                "body_bytes": len(body),
                "success": True
            }
    except Exception as e:
        return {
            "status": 500,
            "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
            "sql_count": None,
            "body_bytes": 0,
            "success": False,
            "error": str(e)
        }

def run_benchmarks(base_url: str) -> Dict[str, Any]:
    results = {}
    print("=========================================================")
    print("   AUTOMATED MULTI-VARIANT BENCHMARKING ENGINE          ")
    print("=========================================================\n")

    for case_id, case_info in CASES.items():
        print(f"📌 Evaluating: {case_info['title']} ({case_info['endpoint']})")
        results[case_id] = {
            "title": case_info["title"],
            "variants": {}
        }
        
        best_variant = None
        best_metric = float("inf")

        for var_id, var_desc in case_info["variants"].items():
            req_params = dict(case_info.get("params", {}))
            req_params["variant"] = var_id
            
            res = make_request(base_url, case_info["endpoint"], case_info["method"], req_params)
            results[case_id]["variants"][var_id] = {
                "description": var_desc,
                "metrics": res
            }

            metric_val = res["sql_count"] if res["sql_count"] is not None else res["elapsed_ms"]
            print(f"  └─ Variant [{var_id:10s}] -> SQL Queries: {str(res['sql_count']):5s} | Time: {res['elapsed_ms']:4d} ms | Bytes: {res['body_bytes']}")

            if var_id != "suboptimal" and metric_val < best_metric:
                best_metric = metric_val
                best_variant = var_id

        results[case_id]["winning_variant"] = best_variant
        print(f"  🏆 Winner Selected: [{best_variant}] ({case_info['variants'].get(best_variant, '')})\n")

    return results

def update_findings_json(results: Dict[str, Any], findings_path: str):
    if not os.path.exists(findings_path):
        print(f"Warning: findings.json not found at {findings_path}")
        return

    with open(findings_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for finding in data.get("findings", []):
        file_path = finding.get("file", "")
        for case_id, res in results.items():
            case_file = CASES[case_id]["findings_file"]
            if case_file in file_path:
                sub_opt = res["variants"]["suboptimal"]["metrics"]
                winner_id = res["winning_variant"]
                winner_metrics = res["variants"][winner_id]["metrics"]

                finding["evidence"]["before"] = sub_opt["sql_count"] if sub_opt["sql_count"] is not None else sub_opt["elapsed_ms"]
                finding["evidence"]["after"] = winner_metrics["sql_count"] if winner_metrics["sql_count"] is not None else winner_metrics["elapsed_ms"]
                finding["evidence"]["winning_variant"] = winner_id
                finding["evidence"]["how"] = f"Multi-variant feature toggle benchmark ({winner_id} selected as optimal)"

    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Updated {findings_path} with benchmark evidence!")

def main():
    parser = argparse.ArgumentParser(description="Multi-Variant Auto-Benchmarking Suite")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="Base URL of running Spring Boot application")
    parser.add_argument("--update-findings", action="store_true", help="Update findings.json with benchmark evidence")
    args = parser.parse_args()

    results = run_benchmarks(args.url)
    if args.update_findings:
        update_findings_json(results, FINDINGS_PATH)

if __name__ == "__main__":
    main()
