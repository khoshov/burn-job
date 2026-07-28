"""
Static (source-level) object field layout estimator.
"""

import os
import re
from typing import Dict, List, Tuple

from burn_job.detectors.source_mapping import _scan_braces

_HEADER_SIZE = 12
_OBJECT_ALIGNMENT = 8
_REFERENCE_SIZE = 4

_PRIMITIVE_SIZES = {
    "boolean": 1, "byte": 1,
    "char": 2, "short": 2,
    "int": 4, "float": 4,
    "long": 8, "double": 8,
}


def _field_size(java_type: str) -> int:
    base = java_type.strip()
    if base.endswith("[]") or "<" in base:
        return _REFERENCE_SIZE
    return _PRIMITIVE_SIZES.get(base, _REFERENCE_SIZE)


def _pack(sized_fields: List[Tuple[str, int]]) -> int:
    offset = _HEADER_SIZE
    for _name, size in sized_fields:
        remainder = offset % size
        if remainder != 0:
            offset += size - remainder
        offset += size
    remainder = offset % _OBJECT_ALIGNMENT
    if remainder != 0:
        offset += _OBJECT_ALIGNMENT - remainder
    return offset


def compute_static_object_layout(fields: List[Tuple[str, str]]) -> Dict:
    sized_fields = [(name, _field_size(t)) for name, t in fields]
    declared_size = _pack(sized_fields)
    optimal_fields = sorted(sized_fields, key=lambda nf: -nf[1])
    optimal_size = _pack(optimal_fields)
    return {
        "declared_size": declared_size,
        "optimal_size": optimal_size,
        "wasted_bytes": max(0, declared_size - optimal_size),
        "optimal_order": [name for name, _ in optimal_fields],
    }


_ANNOTATION_RE = re.compile(r"@\w+(\([^)]*\))?")
_FIELD_DECL_RE = re.compile(
    r"^(?:public|private|protected|final|transient|volatile|static|\s)*"
    r"([A-Za-z_$][\w.]*(?:<[^>]*>)?(?:\[\])*)\s+"
    r"([A-Za-z_$]\w*)\s*(?:=.*)?$"
)
_STATIC_MODIFIER_RE = re.compile(r"\bstatic\b")


def _extract_top_level_statements(class_body_text: str) -> List[str]:
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


def extract_instance_fields(source_text: str, simple_class_name: str) -> List[Tuple[str, str]]:
    class_re = re.compile(r"\b(?:class|record)\s+" + re.escape(simple_class_name) + r"\b")
    m = class_re.search(source_text)
    if not m:
        return []
    body_start = source_text.find("{", m.end())
    if body_start == -1:
        return []

    body_end = _scan_braces(source_text, body_start)
    class_body = source_text[body_start + 1: body_end]

    fields = []
    for stmt in _extract_top_level_statements(class_body):
        if not stmt or "(" in stmt:
            continue
        if _STATIC_MODIFIER_RE.search(stmt):
            continue
        cleaned = _ANNOTATION_RE.sub("", stmt).strip()
        m2 = _FIELD_DECL_RE.match(cleaned)
        if not m2:
            continue
        field_type, field_name = m2.group(1), m2.group(2)
        fields.append((field_name, field_type))
    return fields


def compute_layout_for_source_file(file_path: str, simple_class_name: str) -> Dict:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    fields = extract_instance_fields(text, simple_class_name)
    layout = compute_static_object_layout(fields)
    layout["fields"] = [name for name, _ in fields]
    return layout


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Static field-layout heuristic for a single Java class")
    parser.add_argument("file", help="Path to a .java source file")
    parser.add_argument("class_name", help="Simple (unqualified) class name to inspect")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: file '{args.file}' not found")
        return
    print(json.dumps(compute_layout_for_source_file(args.file, args.class_name), indent=2))


if __name__ == "__main__":
    main()
