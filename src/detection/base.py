"""Base scanner utilities for structural pattern detection."""

import os
from typing import Iterator

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
SRC_ROOT = os.path.join(REPO_ROOT, "java", "src", "main", "java")


def _iter_java_files(src_root: str = SRC_ROOT) -> Iterator[str]:
    if not os.path.isdir(src_root):
        return
    for dirpath, _dirs, filenames in os.walk(src_root):
        for fname in filenames:
            if fname.endswith(".java"):
                yield os.path.join(dirpath, fname)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _scan_matched(text: str, open_index: int, open_char: str, close_char: str) -> int:
    """Returns the index of the char matching text[open_index] (open_char), skipping comments/strings/chars."""
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


def _scan_braces(text: str, open_index: int) -> int:
    return _scan_matched(text, open_index, "{", "}")


class BaseDetector:
    """Abstract base detector class."""

    def __init__(self, src_root: str = SRC_ROOT):
        self.src_root = src_root

    def detect(self):
        raise NotImplementedError
