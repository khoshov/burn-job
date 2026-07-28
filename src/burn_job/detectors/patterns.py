"""
Static (source-level) structural pattern detectors for T1/T2/T3/T6.
"""

import difflib
import os
import re
from typing import Dict, List, Optional, Tuple

from burn_job.detectors.object_layout import _extract_top_level_statements

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
SRC_ROOT = os.path.join(REPO_ROOT, "java", "src", "main", "java")


def _iter_java_files(src_root: str = SRC_ROOT):
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


def _strip_comments_and_annotation_args(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    in_line_comment = in_block_comment = in_string = in_char = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
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
                    out.append(text[i])
            elif c == '"':
                in_string = False
        elif in_char:
            out.append(c)
            if c == "\\":
                i += 1
                if i < n:
                    out.append(text[i])
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


_METHOD_DECL_RE = re.compile(
    r"(?:public|private|protected|static|final|synchronized|abstract|default|\s)*"
    r"[\w<>\[\],.?\s]+?\s([A-Za-z_$][\w$]*)\s*\(([^;{}]*)\)\s*(?:throws\s+[\w,.\s]+)?\s*\{",
)


def iter_method_bodies(source_text: str) -> List[Tuple[str, str, int]]:
    clean = _strip_comments_and_annotation_args(source_text)
    results = []
    for m in _METHOD_DECL_RE.finditer(clean):
        method_name = m.group(1)
        if method_name in ("if", "for", "while", "switch", "catch", "synchronized", "try", "do"):
            continue
        open_brace = m.end() - 1
        close_brace = _scan_braces(clean, open_brace)
        body = source_text[open_brace + 1: close_brace]
        results.append((method_name, body, _line_of(source_text, open_brace)))
    return results


def _class_simple_name(file_path: str) -> str:
    return os.path.basename(file_path)[: -len(".java")]


def _span_end(text: str, start: int) -> int:
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


_LAZY_COLLECTION_FIELD_RE = re.compile(
    r"@(OneToMany|ManyToMany)\s*(\([^)]*\))?[\s\S]{0,300}?"
    r"(?:private|protected|public)?\s+[\w<>\[\],.\s]+?\s(\w+)\s*[=;]"
)
_REPO_FIND_ASSIGN_RE = re.compile(r"\b(\w+)\s*=\s*[\w.]+\.(find\w*)\s*\(")
_REPO_FIND_CHAIN_RE = re.compile(r"[\w.]+\.(find\w*)\s*\([^)]*\)\s*\.\s*(?:stream\s*\(\s*\)|forEach\s*\()")


def _find_lazy_collection_getters(src_root: str = SRC_ROOT) -> Dict[str, str]:
    getters: Dict[str, str] = {}
    for path in _iter_java_files(src_root):
        text = _strip_comments_and_annotation_args(_read(path))
        entity_name = _class_simple_name(path)
        for m in _LAZY_COLLECTION_FIELD_RE.finditer(text):
            _anno_type, anno_args, field_name = m.group(1), m.group(2) or "", m.group(3)
            if "EAGER" in anno_args:
                continue
            getter = "get" + field_name[0:1].upper() + field_name[1:]
            getters[getter] = entity_name
    return getters


_TYPE_DECL_RE = re.compile(r"\b(?:class|interface)\s+([A-Za-z_$]\w*)\b")
_METHOD_SIGNATURE_RE = re.compile(r"\b(\w+)\s*\([^)]*\)\s*$")


def _find_eager_fetch_repo_methods(src_root: str = SRC_ROOT) -> set:
    safe = set()
    for path in _iter_java_files(src_root):
        text = _strip_comments_and_annotation_args(_read(path))
        for type_match in _TYPE_DECL_RE.finditer(text):
            body_start = text.find("{", type_match.end())
            if body_start == -1:
                continue
            body_end = _scan_braces(text, body_start)
            body = text[body_start + 1: body_end]
            for stmt in _extract_top_level_statements(body):
                sig_match = _METHOD_SIGNATURE_RE.search(stmt)
                if not sig_match:
                    continue
                method_name = sig_match.group(1)
                if "@EntityGraph" in stmt:
                    safe.add(method_name)
                elif re.search(r'@Query\(\s*"[^"]*JOIN\s+FETCH', stmt, re.IGNORECASE):
                    safe.add(method_name)
    return safe


def detect_n_plus_one(src_root: str = SRC_ROOT) -> List[dict]:
    anomalies = []
    lazy_getters = _find_lazy_collection_getters(src_root)
    if not lazy_getters:
        return anomalies
    eager_fetch_methods = _find_eager_fetch_repo_methods(src_root)

    for path in _iter_java_files(src_root):
        text = _read(path)
        clean = _strip_comments_and_annotation_args(text)
        rel_path = os.path.relpath(path, REPO_ROOT)

        for method_name, body, start_line in iter_method_bodies(text):
            clean_body = _strip_comments_and_annotation_args(body)
            candidate_vars = [
                (m.group(1), m.group(2)) for m in _REPO_FIND_ASSIGN_RE.finditer(clean_body)
            ]
            inline_hits = list(_REPO_FIND_CHAIN_RE.finditer(clean_body))

            hit_getter = None
            hit_pos = None
            for var, find_method in candidate_vars:
                if find_method in eager_fetch_methods:
                    continue
                pat = r"\b" + re.escape(var) + r"\s*\.\s*(?:stream\s*\(\s*\)|forEach\s*\()"
                consume_re = re.compile(pat)
                for cm in consume_re.finditer(clean_body):
                    span_end = _span_end(clean_body, cm.end())
                    window = clean_body[cm.start():span_end]
                    for getter in lazy_getters:
                        if re.search(r"\." + re.escape(getter) + r"\s*\(", window):
                            hit_getter, hit_pos = getter, cm.start()
                            break
                    if hit_getter:
                        break
                if hit_getter:
                    break

            if not hit_getter:
                for im in inline_hits:
                    if im.group(1) in eager_fetch_methods:
                        continue
                    span_end = _span_end(clean_body, im.end())
                    window = clean_body[im.start():span_end]
                    for getter in lazy_getters:
                        if re.search(r"\." + re.escape(getter) + r"\s*\(", window):
                            hit_getter, hit_pos = getter, im.start()
                            break
                    if hit_getter:
                        break

            if hit_getter:
                line = start_line + clean_body.count("\n", 0, hit_pos)
                entity = lazy_getters[hit_getter]
                anomalies.append({
                    "taxonomy_id": "T6",
                    "category": "DATABASE_QUERIES",
                    "type": "N_PLUS_ONE_QUERIES",
                    "severity": "HIGH",
                    "caller": f"{rel_path}:{start_line}",
                    "callee": f"{rel_path}:{line}",
                    "sample_count": 0,
                    "percentage": 0.0,
                    "description": (
                        f"'{method_name}' iterates a repository query result and calls the lazy "
                        f"'{hit_getter}()' accessor of '{entity}' (a @OneToMany/@ManyToMany field "
                        f"without fetch=EAGER) inside the loop."
                    ),
                })

    return anomalies


_REPO_CALL_ASSIGN_RE = re.compile(r"\b(\w+)\s*=\s*\w*[Rr]epository\w*\.\w+\s*\([^;]*\)\s*;")

_EXISTENCE_CHECK_USAGE_RE = re.compile(
    r"^\s*(?:"
    r"(?:!=|==)\s*null"
    r"|\.\s*isEmpty\s*\(\s*\)"
    r"|\.\s*isPresent\s*\(\s*\)"
    r"|\.\s*isNotEmpty\s*\(\s*\)"
    r"|\.\s*size\s*\(\s*\)\s*(?:==|!=|>=|<=|>|<)"
    r")"
)


def detect_existence_check_full_fetch(src_root: str = SRC_ROOT) -> List[dict]:
    anomalies = []
    for path in _iter_java_files(src_root):
        text = _read(path)
        rel_path = os.path.relpath(path, REPO_ROOT)

        for method_name, body, start_line in iter_method_bodies(text):
            clean_body = _strip_comments_and_annotation_args(body)
            for am in _REPO_CALL_ASSIGN_RE.finditer(clean_body):
                var = am.group(1)
                usage_re = re.compile(r"\b" + re.escape(var) + r"\b")
                usages_after = [
                    um for um in usage_re.finditer(clean_body, am.end()) if um.start() != am.start()
                ]
                if not usages_after:
                    continue

                all_existence_checks = True
                for um in usages_after:
                    tail = clean_body[um.end(): um.end() + 40]
                    if not _EXISTENCE_CHECK_USAGE_RE.match(tail):
                        all_existence_checks = False
                        break

                if all_existence_checks:
                    line = start_line + clean_body.count("\n", 0, am.start())
                    anomalies.append({
                        "taxonomy_id": "T3",
                        "category": "IMPROPER_FUNCTION_USAGE",
                        "type": "FULL_FETCH_FOR_EXISTENCE_CHECK",
                        "severity": "HIGH",
                        "caller": f"{rel_path}:{start_line}",
                        "callee": f"{rel_path}:{line}",
                        "sample_count": 0,
                        "percentage": 0.0,
                        "description": (
                            f"'{method_name}' assigns a repository call result to '{var}', whose "
                            f"only use{'s are' if len(usages_after) > 1 else ' is'} a null/empty/"
                            f"present/size check."
                        ),
                    })

    return anomalies


_FOREACH_HEADER_RE = re.compile(r"for\s*\(\s*(?:final\s+)?[\w<>\[\],.\s]+?\s+(\w+)\s*:\s*")


def _find_foreach_loops(text: str) -> List[Tuple[str, str, int, int]]:
    loops = []
    for m in _FOREACH_HEADER_RE.finditer(text):
        paren_open = text.find("(", m.start())
        if paren_open == -1:
            continue
        paren_close = _scan_matched(text, paren_open, "(", ")")
        iterable_expr = text[m.end(): paren_close]

        j = paren_close + 1
        while j < len(text) and text[j] in " \t\r\n":
            j += 1
        if j < len(text) and text[j] == "{":
            body_start, body_end = j + 1, _scan_braces(text, j)
        else:
            body_start = j
            body_end = _span_end(text, j)
        loops.append((m.group(1), iterable_expr, body_start, body_end))
    return loops


def detect_nested_loops(src_root: str = SRC_ROOT) -> List[dict]:
    anomalies = []
    for path in _iter_java_files(src_root):
        text = _read(path)
        rel_path = os.path.relpath(path, REPO_ROOT)

        for method_name, body, start_line in iter_method_bodies(text):
            clean_body = _strip_comments_and_annotation_args(body)
            for outer_var, _outer_iter, b_start, b_end in _find_foreach_loops(clean_body):
                inner_region = clean_body[b_start:b_end]
                for inner_var, inner_iter_expr, _ibs, _ibe in _find_foreach_loops(inner_region):
                    if re.search(r"\b" + re.escape(outer_var) + r"\b", inner_iter_expr):
                        line = start_line + clean_body.count("\n", 0, b_start)
                        anomalies.append({
                            "taxonomy_id": "T2",
                            "category": "INEFFICIENT_ALGORITHMS",
                            "type": "QUADRATIC_NESTED_LOOP",
                            "severity": "HIGH",
                            "caller": f"{rel_path}:{start_line}",
                            "callee": f"{rel_path}:{line}",
                            "sample_count": 0,
                            "percentage": 0.0,
                            "description": (
                                f"'{method_name}' has a loop over '{inner_var}' whose collection "
                                f"expression depends on the outer loop variable '{outer_var}'."
                            ),
                        })

    return anomalies


_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_$][\w$]*\b")
_JAVA_KEYWORDS = {
    "if", "else", "for", "while", "do", "switch", "case", "default", "return", "break", "continue",
    "new", "this", "super", "null", "true", "false", "try", "catch", "finally", "throw", "throws",
    "class", "interface", "extends", "implements", "public", "private", "protected", "static",
    "final", "void", "int", "long", "double", "float", "boolean", "char", "byte", "short", "var",
    "instanceof", "synchronized", "enum", "abstract", "native", "transient", "volatile", "assert",
}

_MIN_NORMALIZED_BODY_LEN = 40
_SIMILARITY_THRESHOLD = 0.85


def _normalize_body(body_text: str) -> str:
    clean = _strip_comments_and_annotation_args(body_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return _IDENTIFIER_RE.sub(lambda m: m.group(0) if m.group(0) in _JAVA_KEYWORDS else "ID", clean)


def detect_duplicate_methods(src_root: str = SRC_ROOT) -> List[dict]:
    candidates = []
    for path in _iter_java_files(src_root):
        text = _read(path)
        rel_path = os.path.relpath(path, REPO_ROOT)
        for method_name, body, start_line in iter_method_bodies(text):
            normalized = _normalize_body(body)
            if len(normalized) >= _MIN_NORMALIZED_BODY_LEN:
                candidates.append((rel_path, method_name, start_line, normalized))

    anomalies = []
    seen_pairs = set()
    for i in range(len(candidates)):
        path_a, name_a, line_a, norm_a = candidates[i]
        for j in range(i + 1, len(candidates)):
            path_b, name_b, line_b, norm_b = candidates[j]
            if (path_a, line_a) == (path_b, line_b):
                continue
            ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
            if ratio >= _SIMILARITY_THRESHOLD:
                pair_key = tuple(sorted([f"{path_a}:{line_a}", f"{path_b}:{line_b}"]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                anomalies.append({
                    "taxonomy_id": "T1",
                    "category": "REDUNDANT_OPERATIONS",
                    "type": "DUPLICATE_METHOD_BODY",
                    "severity": "MEDIUM",
                    "caller": f"{path_a}:{line_a}",
                    "callee": f"{path_b}:{line_b}",
                    "sample_count": 0,
                    "percentage": round(ratio * 100, 1),
                    "description": (
                        f"'{name_a}' ({path_a}:{line_a}) and '{name_b}' ({path_b}:{line_b}) are "
                        f"{ratio * 100:.0f}% structurally identical."
                    ),
                })

    return anomalies
