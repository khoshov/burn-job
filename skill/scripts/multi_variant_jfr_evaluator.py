#!/usr/bin/env python3
"""
Multi-Variant JFR Evaluator Module & CLI.
Runs benchmark load tests against candidate code implementations while capturing Java Flight Recorder (JFR) profiling data.
Evaluates CPU sample counts, database SQL queries (X-Sql-Count), and latency to select the optimal variant.
"""

import sys
import os
import time
import json
import subprocess
import tempfile
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Tuple, Optional

# Import JFR helper converter from jfr_to_graph if available
try:
    from jfr_to_graph import parse_collapsed_stack, convert_jfr_if_needed
    HAS_JFR_PARSER = True
except ImportError:
    # Add skill/scripts to sys.path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from jfr_to_graph import parse_collapsed_stack, convert_jfr_if_needed
        HAS_JFR_PARSER = True
    except ImportError:
        HAS_JFR_PARSER = False

DEFAULT_BASE_URL = "http://localhost:8080"
MEASUREMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "measurements")

class JFRProfiler:
    def __init__(self, output_dir: str = MEASUREMENTS_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def find_java_pid(self) -> Optional[int]:
        """Finds PID of running Spring Boot application."""
        try:
            res = subprocess.run(["jps", "-l"], capture_output=True, text=True)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "badhibernate" in line or "Application" in line or "bad-hibernate-demo" in line:
                        parts = line.split()
                        if parts and parts[0].isdigit():
                            return int(parts[0])
        except Exception:
            pass
        return None

    def record_jfr(self, pid: int, duration_sec: int, filename: str) -> Optional[str]:
        """Triggers JFR recording via jcmd for pid."""
        jfr_path = os.path.join(self.output_dir, filename)
        try:
            # Start JFR
            start_cmd = ["jcmd", str(pid), "JFR.start", f"name={filename}", f"duration={duration_sec}s", f"filename={jfr_path}"]
            subprocess.run(start_cmd, capture_output=True, text=True, timeout=10)
            return jfr_path
        except Exception as e:
            print(f"Warning: Could not start JFR recording via jcmd: {e}")
            return None

    def parse_jfr_samples(self, jfr_path: str) -> int:
        """Parses JFR recording file and returns total execution CPU samples."""
        if not jfr_path or not os.path.exists(jfr_path) or not HAS_JFR_PARSER:
            return 0
        try:
            collapsed_path = convert_jfr_if_needed(jfr_path)
            _, _, total_samples = parse_collapsed_stack(collapsed_path)
            return total_samples
        except Exception as e:
            print(f"Warning: Failed to parse JFR file {jfr_path}: {e}")
            return 0

def benchmark_endpoint(endpoint: str, method: str = "GET", params: Dict[str, str] = None, base_url: str = DEFAULT_BASE_URL, iterations: int = 5) -> Dict[str, Any]:
    """Runs a series of HTTP requests against endpoint and calculates average metrics."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    if params:
        query_str = urllib.parse.urlencode(params)
        if method.upper() == "GET":
            url += f"?{query_str}"

    sql_counts = []
    elapsed_times = []
    success_count = 0
    body_size = 0

    for _ in range(iterations):
        data = None
        if method.upper() == "POST" and params:
            data = urllib.parse.urlencode(params).encode("utf-8")

        req = urllib.request.Request(url, data=data, method=method.upper())
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                body = resp.read()
                body_size = len(body)
                
                sql_header = resp.headers.get("X-Sql-Count")
                elapsed_header = resp.headers.get("X-Elapsed-Ms")
                
                if sql_header and sql_header.isdigit():
                    sql_counts.append(int(sql_header))
                
                server_time = float(elapsed_header) if elapsed_header and elapsed_header.isdigit() else elapsed_ms
                elapsed_times.append(server_time)
                success_count += 1
        except Exception as e:
            pass

    avg_sql = sum(sql_counts) / len(sql_counts) if sql_counts else 0
    avg_elapsed = sum(elapsed_times) / len(elapsed_times) if elapsed_times else 9999.0

    return {
        "success_rate": success_count / float(iterations),
        "avg_sql_count": avg_sql,
        "avg_elapsed_ms": avg_elapsed,
        "body_bytes": body_size
    }

def evaluate_variant_candidates(candidates: Dict[str, str], endpoint: Optional[str] = None, apply_func = None, verify_func = None) -> Dict[str, Any]:
    """
    Evaluates candidate code implementations:
    - Applies candidate patch
    - Verifies Maven build / test
    - Measures endpoint performance & JFR execution samples
    - Computes efficiency score and selects winner.
    """
    results = {}
    profiler = JFRProfiler()
    pid = profiler.find_java_pid()

    best_candidate = None
    best_score = float("inf")

    for name, candidate_code in candidates.items():
        print(f"  ➜ Evaluating Candidate: [{name}]")
        
        # Apply candidate patch
        if apply_func:
            applied = apply_func(candidate_code)
            if not applied:
                print(f"    ❌ Failed to apply variant [{name}]. Skipping.")
                continue

        # Verify build / test
        if verify_func:
            passed = verify_func()
            if not passed:
                print(f"    ❌ Variant [{name}] failed compilation/test. Discarding.")
                results[name] = {"valid": False, "reason": "Compilation/Test failure"}
                continue

        # Start JFR profiling if PID active
        jfr_file = None
        if pid:
            jfr_file = profiler.record_jfr(pid=pid, duration_sec=5, filename=f"variant_{name}.jfr")

        # Run benchmark workload
        metrics = {}
        if endpoint:
            metrics = benchmark_endpoint(endpoint=endpoint, iterations=5)
        else:
            metrics = {"avg_sql_count": 0, "avg_elapsed_ms": 1.0, "success_rate": 1.0}

        # Parse JFR samples
        jfr_samples = profiler.parse_jfr_samples(jfr_file) if jfr_file else 0
        metrics["jfr_cpu_samples"] = jfr_samples

        # Calculate efficiency score (Lower is better)
        # Score formula: (SQL queries * 1000) + Avg Latency (ms) + (JFR CPU Samples * 2)
        score = (metrics["avg_sql_count"] * 1000.0) + metrics["avg_elapsed_ms"] + (jfr_samples * 2.0)
        metrics["score"] = score
        metrics["valid"] = True

        results[name] = metrics
        print(f"    ✅ Variant [{name}] -> Score: {score:.2f} | SQL: {metrics['avg_sql_count']} | Time: {metrics['avg_elapsed_ms']:.1f}ms | JFR CPU Samples: {jfr_samples}")

        if score < best_score:
            best_score = score
            best_candidate = name

    return {
        "winning_candidate": best_candidate,
        "best_score": best_score,
        "evaluations": results
    }

if __name__ == "__main__":
    print("=== Multi-Variant JFR Evaluator Module Loaded ===")
