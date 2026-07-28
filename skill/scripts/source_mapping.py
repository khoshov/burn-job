#!/usr/bin/env python3
"""
Method (FQN) -> source file / line range resolver.

Turns Method.id-style identifiers from the KùzuDB graph (e.g.
"com/example/badhibernate/service/NPlusOneService.getDepartmentsSubOptimal", the pkg/Class.method
convention used throughout jfr_to_graph.py) into (file, line_from, line_to) relative to the repo
root. This is the piece findings.json generation (plan/004) needs to stop hardcoding locations.

Only resolves methods that live under src/main/java in this repo — JDK/framework frames
(java.*, org.hibernate.*, ...) are not part of the index and resolve to None.
"""

import os
import re
import subprocess
import functools
from typing import Dict, Optional, Tuple

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
SRC_ROOT = os.path.join(REPO_ROOT, "src", "main", "java")
TARGET_CLASSES = os.path.join(REPO_ROOT, "target", "classes")

# javac names the synthetic wrapper class for a lambda "Outer$$Lambda$N.0x<hash>"; the frame's
# "method" is the functional-interface method (accept/test/apply/...), not useful on its own.
_LAMBDA_CLASS_RE = re.compile(r"\$\$Lambda\$")
# javac names the synthetic method holding the actual lambda body "lambda$outerMethod$N".
_LAMBDA_METHOD_RE = re.compile(r"^lambda\$([A-Za-z0-9_]+)\$\d+$")


def _build_class_index(src_root: str) -> Dict[str, str]:
    """Maps dotted top-level class FQN -> source file path relative to REPO_ROOT."""
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


@functools.lru_cache(maxsize=1)
def _class_index() -> Dict[str, str]:
    return _build_class_index(SRC_ROOT)


@functools.lru_cache(maxsize=None)
def _read_source(file_rel_path: str) -> str:
    with open(os.path.join(REPO_ROOT, file_rel_path), "r", encoding="utf-8") as f:
        return f.read()


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _scan_braces(text: str, open_brace_index: int) -> int:
    """Given the index of a '{', returns the index of its matching '}', skipping comments/strings/chars."""
    depth = 0
    i = open_brace_index
    n = len(text)
    in_line_comment = in_block_comment = in_string = in_char = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
        elif in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_string:
            if c == "\\":
                i += 1
            elif c == '"':
                in_string = False
        elif in_char:
            if c == "\\":
                i += 1
            elif c == "'":
                in_char = False
        else:
            if c == "/" and nxt == "/":
                in_line_comment = True
                i += 1
            elif c == "/" and nxt == "*":
                in_block_comment = True
                i += 1
            elif c == '"':
                in_string = True
            elif c == "'":
                in_char = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return n - 1


def _find_method_body_range(text: str, method_name: str) -> Optional[Tuple[int, int]]:
    """
    Regex fallback: finds a method DECLARATION (not a call site) by name and returns
    (line_from, line_to) as (declaration line, closing-brace line).
    """
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
        if text[j : j + 6] == "throws":
            k = j
            while k < n and text[k] not in "{;":
                k += 1
            j = k
            while j < n and text[j] in " \t\r\n":
                j += 1

        if j < n and text[j] == "{":
            decl_line = _line_of(text, m.start())
            body_end = _scan_braces(text, j)
            return decl_line, _line_of(text, body_end)
        # Followed by ';' (call site or interface/abstract signature) — not a declaration body, keep looking.
    return None


def _find_class_body_range(text: str, simple_class_name: str) -> Optional[Tuple[int, int]]:
    pattern = re.compile(r"\b(?:class|interface|enum|record)\s+" + re.escape(simple_class_name) + r"\b")
    m = pattern.search(text)
    if not m:
        return None
    brace_index = text.find("{", m.end())
    if brace_index == -1:
        return None
    body_end = _scan_braces(text, brace_index)
    return _line_of(text, m.start()), _line_of(text, body_end)


def _parse_javap_line_table(class_fqn: str, method_name: str, classpath: str) -> Optional[Tuple[int, int]]:
    """Runs `javap -l -p` on a compiled class and extracts the LineNumberTable for one method."""
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


def _resolve_method_in_class(class_fqn: str, method_name: str) -> Optional[Tuple[str, int, int]]:
    top_level_class = class_fqn.split("$")[0]
    file_rel_path = _class_index().get(top_level_class)
    if file_rel_path is None:
        return None  # Not project code (JDK/framework/etc.) — nothing to resolve.

    if os.path.isdir(TARGET_CLASSES):
        rng = _parse_javap_line_table(class_fqn, method_name, TARGET_CLASSES)
        if rng is not None:
            return file_rel_path, rng[0], rng[1]

    text = _read_source(file_rel_path)
    rng = _find_method_body_range(text, method_name)
    if rng is None:
        return None
    return file_rel_path, rng[0], rng[1]


def _resolve_class_only(class_fqn: str) -> Optional[Tuple[str, int, int]]:
    top_level_class = class_fqn.split("$")[0]
    file_rel_path = _class_index().get(top_level_class)
    if file_rel_path is None:
        return None
    text = _read_source(file_rel_path)
    simple_name = top_level_class.rsplit(".", 1)[-1]
    rng = _find_class_body_range(text, simple_name)
    if rng is None:
        return None
    return file_rel_path, rng[0], rng[1]


@functools.lru_cache(maxsize=None)
def resolve_source_location(method_fqn: str) -> Optional[Tuple[str, int, int]]:
    """
    Resolves a Method.id-style FQN to (file_path_relative_to_repo_root, line_from, line_to).
    Accepts both "pkg/Class.method" (the graph's native convention) and "pkg.Class.method".
    Returns None for anything not indexed under src/main/java, or on any resolution failure.
    """
    normalized = method_fqn.replace("/", ".")
    if "." not in normalized:
        return None
    class_fqn, method_name = normalized.rsplit(".", 1)

    if _LAMBDA_CLASS_RE.search(class_fqn):
        enclosing_class = _LAMBDA_CLASS_RE.split(class_fqn)[0]
        return _resolve_class_only(enclosing_class)

    lambda_method_match = _LAMBDA_METHOD_RE.match(method_name)
    if lambda_method_match:
        method_name = lambda_method_match.group(1)

    return _resolve_method_in_class(class_fqn, method_name)


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
