"""
Multi-Variant JFR Evaluator Module & CLI.
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

from burn_job.graph.ingest import parse_collapsed_stack, convert_jfr_if_needed


class JFRProfiler:
    def __init__(self, java_pid: str = None):
        self.pid = java_pid or self._find_java_pid()
        self.recording_name = f"variant_recording_{int(time.time())}"

    def _find_java_pid(self) -> str:
        try:
            res = subprocess.run(["jps", "-l"], capture_output=True, text=True, timeout=10)
            for line in res.stdout.splitlines():
                if "spring" in line.lower() or "application" in line.lower() or "jar" in line.lower():
                    return line.split()[0]
            return None
        except Exception:
            return None

    def start_recording(self, duration_sec: int = 15):
        if not self.pid:
            return None
        try:
            subprocess.run(
                ["jcmd", self.pid, f"JFR.start", f"name={self.recording_name}", f"duration={duration_sec}s"],
                capture_output=True, text=True, timeout=10
            )
        except Exception:
            pass

    def stop_recording(self) -> str:
        if not self.pid:
            return None
        tmp = tempfile.NamedTemporaryFile(suffix=".jfr", delete=False)
        try:
            subprocess.run(
                ["jcmd", self.pid, f"JFR.stop", f"name={self.recording_name}",
                 f"filename={tmp.name}"],
                capture_output=True, text=True, timeout=10
            )
            if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 0:
                return tmp.name
        except Exception:
            pass
        return None

    def get_cpu_samples(self, jfr_path: str) -> int:
        try:
            data = convert_jfr_if_needed(jfr_path)
            total = sum(data.values()) if data else 0
            return total
        except Exception:
            return 0


def benchmark_endpoint(base_url: str, endpoint: str, concurrency: int = 5, duration_sec: int = 5) -> dict:
    import urllib.request
    import time

    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    latencies = []
    sql_counts = []
    success = 0
    total = 0
    start = time.time()

    while time.time() - start < duration_sec:
        try:
            req = urllib.request.Request(url)
            t0 = time.time()
            resp = urllib.request.urlopen(req, timeout=10)
            elapsed = time.time() - t0
            latencies.append(elapsed * 1000)
            sql_count = int(resp.headers.get("X-Sql-Count", 0))
            sql_counts.append(sql_count)
            success += 1
        except Exception:
            pass
        total += 1

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    avg_sql = sum(sql_counts) / len(sql_counts) if sql_counts else 0

    return {
        "endpoint": endpoint,
        "avg_latency_ms": avg_latency,
        "avg_sql_count": avg_sql,
        "success_rate": (success / total * 100) if total else 0,
    }


def evaluate_variant_candidates(candidates: Dict[str, str], apply_func, verify_func,
                                 endpoint: str = None, base_url: str = "http://localhost:8080",
                                 enable_jfr: bool = False) -> dict:
    results = {}
    profiler = JFRProfiler() if enable_jfr else None

    for var_name, code in candidates.items():
        print(f"Evaluating {var_name}...")

        if not apply_func(code):
            results[var_name] = {"success": False, "error": "apply_failed"}
            continue

        if not verify_func():
            results[var_name] = {"success": False, "error": "verification_failed"}
            continue

        score = 0
        evidence = {}

        if endpoint:
            bench = benchmark_endpoint(base_url, endpoint)
            evidence["benchmark"] = bench
            score += 1000 - bench.get("avg_sql_count", 0) * 100
            score += 100 - bench.get("avg_latency_ms", 0)

        if profiler:
            jfr_path = profiler.stop_recording()
            if jfr_path:
                cpu_samples = profiler.get_cpu_samples(jfr_path)
                evidence["jfr_cpu_samples"] = cpu_samples
                score += 1000 - cpu_samples * 2
                os.unlink(jfr_path)

        results[var_name] = {
            "success": True,
            "score": max(score, 0),
            "evidence": evidence,
        }

    winner = max(results, key=lambda v: results[v].get("score", 0)) if results else None

    return {
        "winning_candidate": winner,
        "best_score": results[winner].get("score", 0) if winner else 0,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-Variant JFR Evaluator")
    parser.add_argument("--candidates", help="JSON file with candidate variants")
    parser.add_argument("--endpoint", help="REST endpoint to benchmark")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--jfr", action="store_true", help="Enable JFR profiling")
    args = parser.parse_args()

    if args.candidates:
        with open(args.candidates) as f:
            candidates = json.load(f)
    else:
        candidates = {"v1": "// empty"}

    def apply_patch(code: str) -> bool:
        return True

    def verify_build() -> bool:
        return True

    result = evaluate_variant_candidates(
        candidates=candidates,
        endpoint=args.endpoint,
        base_url=args.base_url,
        apply_func=apply_patch,
        verify_func=verify_build,
        enable_jfr=args.jfr,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
