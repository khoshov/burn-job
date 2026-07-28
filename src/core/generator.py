"""
Spring Controller Scanner & Loadtest Generator Module.
"""

import os
import re
import sys
import json
import urllib.request
from typing import List, Dict, Any, Optional

from models.endpoint import EndpointInfo
from models.metrics import MicrometerMetrics, LatencyStats
from logging_config import setup_logger

logger = setup_logger("Generator")


class ControllerScanner:
    """Scans Java source files in src/main/java for Spring `@RestController` mappings."""

    @staticmethod
    def scan_directory(src_dir: str) -> List[EndpointInfo]:
        endpoints: List[EndpointInfo] = []
        if not os.path.exists(src_dir):
            logger.warning(f"Source directory does not exist: {src_dir}")
            return endpoints

        mapping_pattern = re.compile(
            r'@(Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?(?:path\s*=\s*)?["\']([^"\']+)["\']',
            re.IGNORECASE
        )
        class_mapping_pattern = re.compile(
            r'@(Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?(?:path\s*=\s*)?["\']([^"\']+)["\']',
            re.IGNORECASE
        )
        class_name_pattern = re.compile(r'class\s+([A-Za-z0-9_]+)')
        method_name_pattern = re.compile(r'public\s+[A-Za-z0-9_<>,\s]+\s+([A-Za-z0-9_]+)\s*\(')

        for root, _, files in os.walk(src_dir):
            for f in files:
                if not f.endswith(".java"):
                    continue
                file_path = os.path.join(root, f)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = fp.readlines()

                content = "".join(lines)
                if "@RestController" not in content and "@Controller" not in content:
                    continue

                class_name = f[:-5]
                class_match = class_name_pattern.search(content)
                if class_match:
                    class_name = class_match.group(1)

                base_path = ""
                base_match = class_mapping_pattern.search(content[:content.find("class ")]) if "class " in content else None
                if base_match:
                    base_path = base_match.group(2)

                for idx, line in enumerate(lines, 1):
                    m = mapping_pattern.search(line)
                    if m:
                        http_verb = m.group(1).upper()
                        if http_verb == "REQUEST":
                            http_verb = "GET"
                        sub_path = m.group(2)
                        full_path = (base_path + sub_path).replace("//", "/")
                        if not full_path.startswith("/"):
                            full_path = "/" + full_path

                        method_name = "handlerMethod"
                        for ahead in lines[idx:idx + 5]:
                            mm = method_name_pattern.search(ahead)
                            if mm:
                                method_name = mm.group(1)
                                break

                        endpoints.append(EndpointInfo(
                            path=full_path,
                            http_method=http_verb,
                            controller_class=class_name,
                            method_name=method_name,
                            file_path=file_path,
                            line_number=idx,
                        ))

        return endpoints


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

    print(f"🚀 Running load test against {{host}} (Concurrency: {{concurrency}})...")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for ep in ENDPOINTS:
            futures.append(executor.submit(run_request, host, ep, requests_per_worker))
        for f in futures:
            f.result()
    print("✅ Load test execution complete.")

if __name__ == "__main__":
    main()
'''
        with open(output_script_path, "w", encoding="utf-8") as f:
            f.write(script_code)
        logger.info(f"Generated load test script: {output_script_path}")
