"""
Static bytecode call graph + entry-point reachability.
"""

import os
import re
import subprocess
from collections import deque
from typing import Dict, List, Set, Tuple

METHOD_LEVEL_ENTRY_ANNOTATIONS = (
    "org.springframework.web.bind.annotation.RequestMapping",
    "org.springframework.web.bind.annotation.GetMapping",
    "org.springframework.web.bind.annotation.PostMapping",
    "org.springframework.web.bind.annotation.PutMapping",
    "org.springframework.web.bind.annotation.DeleteMapping",
    "org.springframework.web.bind.annotation.PatchMapping",
    "org.junit.jupiter.api.Test",
    "org.junit.Test",
)
CLASS_LEVEL_ENTRY_ANNOTATIONS = (
    "org.springframework.web.bind.annotation.RestController",
    "org.springframework.stereotype.Controller",
    "org.springframework.web.bind.annotation.Controller",
)

_INVOKE_TARGET_RE = re.compile(
    r'invoke(?:virtual|special|static|interface)\s+#\d+\s*(?:,\s*\d+\s*)?//\s+(?:Interface)?Method\s+(.+):(\(.*)$'
)
_METHOD_HEADER_RE = re.compile(r'([A-Za-z_$][\w$]*)\s*\([^;{]*\)[^;{]*;\s*$')


def _find_classes(classpath_dir: str) -> List[str]:
    fqns = []
    for dirpath, _dirs, filenames in os.walk(classpath_dir):
        for fname in filenames:
            if not fname.endswith(".class"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fname), classpath_dir)
            fqns.append(rel[: -len(".class")].replace(os.sep, "."))
    return fqns


def _javap_dump(classpath_dir: str, class_fqn: str) -> str:
    try:
        res = subprocess.run(
            ["javap", "-v", "-c", "-p", "-classpath", classpath_dir, class_fqn],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return ""
    return res.stdout if res.returncode == 0 else ""


def _split_member_blocks(dump: str) -> Tuple[List[str], str]:
    lines = dump.splitlines()
    try:
        open_idx = lines.index("{")
    except ValueError:
        return [], dump

    depth = 0
    close_idx = None
    for i in range(open_idx, len(lines)):
        if lines[i] == "{":
            depth += 1
        elif lines[i] == "}":
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    if close_idx is None:
        return [], dump

    body = "\n".join(lines[open_idx + 1: close_idx])
    tail = "\n".join(lines[close_idx + 1:])
    blocks = [b for b in re.split(r"\n\s*\n", body) if b.strip()]
    return blocks, tail


def _is_method_block(first_line: str) -> bool:
    stripped = first_line.strip()
    return "(" in stripped and stripped.endswith(";")


def _method_name_from_header(first_line: str) -> str:
    m = _METHOD_HEADER_RE.search(first_line.strip())
    return m.group(1) if m else ""


def _invoke_targets(block: str, current_class_slash: str) -> List[str]:
    targets = []
    for line in block.splitlines():
        m = _INVOKE_TARGET_RE.search(line)
        if not m:
            continue
        owner_and_method = m.group(1)
        if '."' in owner_and_method:
            owner, method = owner_and_method.split('."', 1)
            method = method.rstrip('"')
        elif "." in owner_and_method:
            owner, method = owner_and_method.rsplit(".", 1)
        else:
            owner, method = current_class_slash, owner_and_method
        targets.append(f"{owner}.{method}")
    return targets


def build_static_call_graph(classpath_dir: str) -> Tuple[Dict[str, Set[str]], Set[str]]:
    call_graph: Dict[str, Set[str]] = {}
    entry_points: Set[str] = set()

    if not os.path.isdir(classpath_dir):
        return call_graph, entry_points

    for class_fqn in _find_classes(classpath_dir):
        dump = _javap_dump(classpath_dir, class_fqn)
        if not dump:
            continue
        class_slash = class_fqn.replace(".", "/")
        blocks, tail = _split_member_blocks(dump)
        class_is_entry_type = any(anno in tail for anno in CLASS_LEVEL_ENTRY_ANNOTATIONS)

        simple_class_name = class_fqn.rsplit(".", 1)[-1]
        for block in blocks:
            block_lines = block.splitlines()
            if not block_lines:
                continue
            first_line = block_lines[0]
            if not _is_method_block(first_line):
                continue
            method_name = _method_name_from_header(first_line)
            if not method_name:
                continue
            if method_name == simple_class_name:
                method_name = "<init>"
            method_id = f"{class_slash}.{method_name}"
            call_graph.setdefault(method_id, set()).update(_invoke_targets(block, class_slash))

            is_public = "ACC_PUBLIC" in block
            is_static = "ACC_STATIC" in block
            has_method_entry_anno = any(anno in block for anno in METHOD_LEVEL_ENTRY_ANNOTATIONS)
            is_main_method = method_name == "main" and is_public and is_static

            if has_method_entry_anno or is_main_method or (class_is_entry_type and is_public):
                entry_points.add(method_id)

    return call_graph, entry_points


def compute_reachable(call_graph: Dict[str, Set[str]], entry_points: Set[str]) -> Set[str]:
    reachable: Set[str] = set(entry_points)
    queue = deque(entry_points)
    while queue:
        current = queue.popleft()
        for target in call_graph.get(current, ()):
            if target not in reachable:
                reachable.add(target)
                queue.append(target)
    return reachable


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Static bytecode call graph & entry-point reachability")
    parser.add_argument("classpath_dir", help="Directory containing compiled .class files (e.g. target/classes)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    call_graph, entry_points = build_static_call_graph(args.classpath_dir)
    reachable = compute_reachable(call_graph, entry_points)

    if args.json:
        print(json.dumps({
            "entry_points": sorted(entry_points),
            "reachable": sorted(reachable),
            "declared_methods": sorted(call_graph.keys()),
        }, indent=2))
    else:
        print(f"Entry points ({len(entry_points)}):")
        for e in sorted(entry_points):
            print(f"  {e}")
        print(f"Reachable methods: {len(reachable)} / {len(call_graph)} declared")


if __name__ == "__main__":
    main()
