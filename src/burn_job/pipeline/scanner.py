"""Spring Controller Scanner Module."""

import os
import re
from typing import List

from burn_job.domain.endpoint import EndpointInfo
from burn_job.core.logging import setup_logger

logger = setup_logger("Scanner")

class ControllerScanner:
    """Scans Java source files for Spring REST Controller endpoints."""

    @staticmethod
    def scan_directory(src_dir: str) -> List[EndpointInfo]:
        endpoints: List[EndpointInfo] = []
        if not os.path.exists(src_dir):
            logger.warning(f"Source directory does not exist: {src_dir}")
            return endpoints

        mapping_pattern = re.compile(
            r'@(Get|Post|Put|Delete|Patch|Request)Mapping(?:\s*\(\s*(?:value\s*=\s*)?(?:path\s*=\s*)?["\']([^"\']*)["\']|\s*\([^)]*\)|\s*)',
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
                class_line_idx = -1

                for idx, line in enumerate(lines):
                    cm = class_name_pattern.search(line)
                    if cm:
                        class_name = cm.group(1)
                        class_line_idx = idx
                        break

                if class_line_idx == -1:
                    continue

                # Find base path from annotations above class definition
                base_path = ""
                header_text = "".join(lines[:class_line_idx])
                base_match = re.search(
                    r'@(?:[A-Za-z0-9_]+Mapping)\s*\(\s*(?:value\s*=\s*)?(?:path\s*=\s*)?["\']([^"\']+)["\']',
                    header_text,
                    re.IGNORECASE
                )
                if base_match:
                    base_path = base_match.group(1)

                # Scan method mappings inside class body
                for idx in range(class_line_idx + 1, len(lines)):
                    line = lines[idx]
                    m = mapping_pattern.search(line)
                    if m:
                        http_verb = m.group(1).upper()
                        if http_verb == "REQUEST":
                            http_verb = "GET"
                        sub_path = m.group(2) if m.group(2) is not None else ""

                        full_path = (base_path + "/" + sub_path).replace("//", "/")
                        if not full_path.startswith("/"):
                            full_path = "/" + full_path

                        method_name = "handlerMethod"
                        for ahead in lines[idx + 1:idx + 6]:
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
                            line_number=idx + 1,
                        ))

        return endpoints
