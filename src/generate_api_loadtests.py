#!/usr/bin/env python3
"""
Spring REST Controller Scanner & Load Test Generator Wrapper.
Forwards to core.generator.
"""

import sys
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.generator import ControllerScanner, LoadtestGenerator


def scan_spring_controllers(src_dir: str):
    endpoints = ControllerScanner.scan_directory(src_dir)
    return [e.to_dict() for e in endpoints]


def generate_loadtest_script(endpoints: list, output_script_path: str):
    from models.endpoint import EndpointInfo
    ep_objs = [
        EndpointInfo(
            path=e["path"],
            http_method=e.get("http_method", "GET"),
            controller_class=e.get("controller_class", ""),
            method_name=e.get("method_name", ""),
            file_path=e.get("file_path", ""),
            line_number=e.get("line_number", 0),
        )
        for e in endpoints
    ]
    LoadtestGenerator.generate_script(ep_objs, output_script_path)


def fetch_micrometer_metrics(host: str = "http://localhost:8080") -> dict:
    return {"latency_p95": 0.0, "rps": 0.0, "error_count": 0}


def generate_report(endpoints, before_metrics, after_metrics, duration_sec, md_report_path, json_report_path):
    os.makedirs(os.path.dirname(json_report_path) or ".", exist_ok=True)
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump({"endpoints": len(endpoints), "duration_sec": duration_sec}, f, indent=2)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "src", "main", "java")
    eps = scan_spring_controllers(src)
    print(f"Scanned {len(eps)} endpoints.")
