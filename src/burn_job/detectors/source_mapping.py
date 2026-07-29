"""
Method (FQN) -> source file / line range resolver.
"""

import functools
import os
import re
import subprocess
from typing import Dict, Optional, Tuple

from burn_job.detectors._shared import REPO_ROOT, SRC_ROOT, scan_braces, line_of

TARGET_CLASSES = os.path.join(REPO_ROOT, "java", "target", "classes")

_LAMBDA_CLASS_RE = re.compile(r"\$\$Lambda\$")
_LAMBDA_METHOD_RE = re.compile(r"^lambda\$([A-Za-z0-9_]+)\$\d+$")


def _build_class_index(src_root: str) -> Dict[str, str]:
    index: Dict[str, str] = {}
    if not os.path.isdir(src_root):
        return index
    for dirpath, _dirnames, filenames in os.walk(src_root):
        for fname in filenames:
            if not fname.endswith(".java"):
                continue
            class_name = fname[: -len(".java")]
            rel_dir = os.path.relpath(dirpath, src_root)
            pkg = "" if rel_dir == "." else rel_dir.replace(os.sep, ".")
            fqn = f"{pkg}.{class_name}" if pkg else class_name
            abs_path = os.path.join(dirpath, fname)
            index[fqn] = os.path.relpath(abs_path, REPO_ROOT)
    return index


@functools.lru_cache(maxsize=32)
def get_class_index(src_root: str) -> Dict[str, str]:
    return _build_class_index(src_root)


def _class_index(src_root: Optional[str] = None) -> Dict[str, str]:
    root = src_root or os.getenv("BURN_JOB_SRC_DIR") or SRC_ROOT
    return get_class_index(root)


@functools.lru_cache(maxsize=None)
def _read_source(file_rel_path: str) -> str:
    with open(os.path.join(REPO_ROOT, file_rel_path), "r", encoding="utf-8") as f:
        return f.read()


def _find_method_body_range(text: str, method_name: str) -> Optional[Tuple[int, int]]:
    pattern = re.compile(r"\b" + re.escape(method_name) + r"\s*\(")
    n = len(text)
    for m in pattern.finditer(text):
        paren_index = m.end() - 1
        depth = 0
        i = paren_index
        while i < n:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        else:
            continue

        j = i + 1
        while j < n and text[j] in " \t\r\n":
            j += 1
        if text[j: j + 6] == "throws":
            k = j
            while k < n and text[k] not in "{;":
                k += 1
            j = k
            while j < n and text[j] in " \t\r\n":
                j += 1

        if j < n and text[j] == "{":
            decl_line = line_of(text, m.start())
            body_end = scan_braces(text, j)
            return decl_line, line_of(text, body_end)
    return None


def _find_class_body_range(text: str, simple_class_name: str) -> Optional[Tuple[int, int]]:
    pattern = re.compile(r"\b(?:class|interface|enum|record)\s+" + re.escape(simple_class_name) + r"\b")
    m = pattern.search(text)
    if not m:
        return None
    brace_index = text.find("{", m.end())
    if brace_index == -1:
        return None
    body_end = scan_braces(text, brace_index)
    return line_of(text, m.start()), line_of(text, body_end)


def _parse_javap_line_table(class_fqn: str, method_name: str, classpath: str) -> Optional[Tuple[int, int]]:
    try:
        res = subprocess.run(
            ["javap", "-l", "-p", "-classpath", classpath, class_fqn],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return None
    if res.returncode != 0:
        return None

    header_re = re.compile(r"\b" + re.escape(method_name) + r"\s*\(")
    line_re = re.compile(r"^line (\d+):")

    lines = res.stdout.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        stripped = lines[i].strip()
        if stripped.endswith(";") and "(" in stripped and header_re.search(stripped):
            j = i + 1
            found_table = False
            collected = []
            while j < n:
                s = lines[j].strip()
                if s == "LineNumberTable:":
                    found_table = True
                    j += 1
                    continue
                if found_table:
                    lm = line_re.match(s)
                    if lm:
                        collected.append(int(lm.group(1)))
                        j += 1
                        continue
                    break
                if s == "" or s == "LocalVariableTable:":
                    break
                j += 1
            if collected:
                return min(collected), max(collected)
        i += 1
    return None


def _resolve_method_in_class(class_fqn: str, method_name: str, src_root: Optional[str] = None) -> Optional[Tuple[str, int, int]]:
    top_level_class = class_fqn.split("$")[0]
    file_rel_path = _class_index(src_root).get(top_level_class)
    if file_rel_path is None:
        return None

    if os.path.isdir(TARGET_CLASSES):
        rng = _parse_javap_line_table(class_fqn, method_name, TARGET_CLASSES)
        if rng is not None:
            return file_rel_path, rng[0], rng[1]

    text = _read_source(file_rel_path)
    rng = _find_method_body_range(text, method_name)
    if rng is None:
        return None
    return file_rel_path, rng[0], rng[1]


def _resolve_class_only(class_fqn: str, src_root: Optional[str] = None) -> Optional[Tuple[str, int, int]]:
    top_level_class = class_fqn.split("$")[0]
    file_rel_path = _class_index(src_root).get(top_level_class)
    if file_rel_path is None:
        return None
    text = _read_source(file_rel_path)
    simple_name = top_level_class.rsplit(".", 1)[-1]
    rng = _find_class_body_range(text, simple_name)
    if rng is None:
        return None
    return file_rel_path, rng[0], rng[1]


@functools.lru_cache(maxsize=None)
def resolve_source_location(method_fqn: str, src_root: Optional[str] = None) -> Optional[Tuple[str, int, int]]:
    normalized = method_fqn.replace("/", ".")
    if "." not in normalized:
        return None
    class_fqn, method_name = normalized.rsplit(".", 1)

    if _LAMBDA_CLASS_RE.search(class_fqn):
        enclosing_class = _LAMBDA_CLASS_RE.split(class_fqn)[0]
        return _resolve_class_only(enclosing_class, src_root=src_root)

    lambda_method_match = _LAMBDA_METHOD_RE.match(method_name)
    if lambda_method_match:
        method_name = lambda_method_match.group(1)

    return _resolve_method_in_class(class_fqn, method_name, src_root=src_root)


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Resolve a Method FQN to (file, line_from, line_to)")
    parser.add_argument("method_fqn", help="e.g. com/example/badhibernate/service/NPlusOneService.getDepartmentsSubOptimal")
    args = parser.parse_args()

    result = resolve_source_location(args.method_fqn)
    if result is None:
        print(json.dumps(None))
    else:
        file_path, line_from, line_to = result
        print(json.dumps({"file": file_path, "line_from": line_from, "line_to": line_to}))


if __name__ == "__main__":
    main()
