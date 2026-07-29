"""Shared utilities for all detectors — consolidated from duplicate implementations."""

import functools
import os
import re
from typing import Dict, List, Optional, Tuple

from burn_job.core.config import DEFAULT_SRC_DIR

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
SRC_ROOT = DEFAULT_SRC_DIR


@functools.lru_cache(maxsize=1)
def iter_java_files(src_root: str = SRC_ROOT) -> List[str]:
    if not os.path.isdir(src_root):
        return []
    files = []
    for dirpath, _dirs, filenames in os.walk(src_root):
        for fname in filenames:
            if fname.endswith(".java"):
                files.append(os.path.join(dirpath, fname))
    return files


@functools.lru_cache(maxsize=None)
def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def scan_matched(text: str, open_index: int, open_char: str = "{", close_char: str = "}") -> int:
    depth = 0
    i = open_index
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
            elif c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return n - 1


def scan_braces(text: str, open_index: int) -> int:
    return scan_matched(text, open_index, "{", "}")


def strip_comments(code: str) -> str:
    out = []
    i = 0
    n = len(code)
    in_line_comment = in_block_comment = in_string = in_char = False
    while i < n:
        c = code[i]
        nxt = code[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
                out.append(c)
            else:
                out.append(" ")
        elif in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                out.append("  ")
                i += 1
            else:
                out.append(c if c == "\n" else " ")
        elif in_string:
            out.append(c)
            if c == "\\":
                i += 1
                if i < n:
                    out.append(code[i])
            elif c == '"':
                in_string = False
        elif in_char:
            out.append(c)
            if c == "\\":
                i += 1
                if i < n:
                    out.append(code[i])
            elif c == "'":
                in_char = False
        else:
            if c == "/" and nxt == "/":
                in_line_comment = True
                out.append("  ")
                i += 1
            elif c == "/" and nxt == "*":
                in_block_comment = True
                out.append("  ")
                i += 1
            elif c == '"':
                in_string = True
                out.append(c)
            elif c == "'":
                in_char = True
                out.append(c)
            else:
                out.append(c)
        i += 1
    return "".join(out)


def class_simple_name(file_path: str) -> str:
    return os.path.basename(file_path)[: -len(".java")]


def read_source_window(file_rel_path: str, line_from: int, before: int = 3, after: int = 2) -> Optional[str]:
    try:
        with open(os.path.join(REPO_ROOT, file_rel_path), "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    start = max(0, line_from - 1 - before)
    end = min(len(lines), line_from + after)
    return "\n".join(lines[start:end])


def span_end(text: str, start: int) -> int:
    depth = 0
    opened = False
    i = start
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
            elif c in "({[":
                depth += 1
                opened = True
            elif c in ")}]":
                depth -= 1
                if opened and depth == 0:
                    return i + 1
            elif c == ";" and depth == 0:
                return i + 1
        i += 1
    return n


_METHOD_SIGNATURE_RE = re.compile(r"\b(\w+)\s*\([^)]*\)\s*$")

_TYPE_DECL_RE = re.compile(r"\b(?:class|interface)\s+([A-Za-z_$]\w*)\b")


def extract_top_level_statements(class_body_text: str) -> List[str]:
    statements = []
    buf: List[str] = []
    depth = 0
    in_line_comment = in_block_comment = in_string = in_char = False
    n = len(class_body_text)
    i = 0
    while i < n:
        c = class_body_text[i]
        nxt = class_body_text[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
        elif in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_string:
            if depth == 0:
                buf.append(c)
            if c == "\\":
                i += 1
                if depth == 0 and i < n:
                    buf.append(class_body_text[i])
            elif c == '"':
                in_string = False
        elif in_char:
            if depth == 0:
                buf.append(c)
            if c == "\\":
                i += 1
                if depth == 0 and i < n:
                    buf.append(class_body_text[i])
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
                if depth == 0:
                    buf.append(c)
            elif c == "'":
                in_char = True
                if depth == 0:
                    buf.append(c)
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == ";" and depth == 0:
                statements.append("".join(buf).strip())
                buf = []
            elif depth == 0:
                buf.append(c)
        i += 1
    return statements


_METHOD_DECL_RE = re.compile(
    r"(?:public|private|protected|static|final|synchronized|abstract|default|\s)*"
    r"[\w<>\[\],.?\s]+?\s([A-Za-z_$][\w$]*)\s*\(([^;{}]*)\)\s*(?:throws\s+[\w,.\s]+)?\s*\{",
)


def iter_method_bodies(source_text: str) -> List[Tuple[str, str, int]]:
    clean = strip_comments(source_text)
    results = []
    for m in _METHOD_DECL_RE.finditer(clean):
        method_name = m.group(1)
        if method_name in ("if", "for", "while", "switch", "catch", "synchronized", "try", "do"):
            continue
        open_brace = m.end() - 1
        close_brace = scan_braces(clean, open_brace)
        body = source_text[open_brace + 1: close_brace]
        results.append((method_name, body, line_of(source_text, open_brace)))
    return results
