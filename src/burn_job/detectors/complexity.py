"""
AST & Pattern Complexity Analyzer for Java Source Code.
"""

import argparse
import json
import logging
import os
import re
import sys

logger = logging.getLogger("complexity_analyzer")


def _strip_comments(code: str) -> str:
    in_string = False
    string_char = None
    i = 0
    result = []
    n = len(code)
    while i < n:
        if in_string:
            result.append(code[i])
            if code[i] == '\\':
                i += 1
                if i < n:
                    result.append(code[i])
            elif code[i] == string_char:
                in_string = False
            i += 1
            continue
        if code[i] in ('"', "'"):
            in_string = True
            string_char = code[i]
            result.append(code[i])
            i += 1
            continue
        if code[i:i+2] == '//':
            while i < n and code[i] != '\n':
                i += 1
            continue
        if code[i:i+2] == '/*':
            i += 2
            while i < n and code[i:i+2] != '*/':
                i += 1
            i += 2
            continue
        result.append(code[i])
        i += 1
    return ''.join(result)


def _detect_loop_nesting(code_stripped: str):
    open_loops = []
    nesting_info = []
    max_nesting = 0
    i = 0
    n = len(code_stripped)
    brace_depth = 0
    paren_depth = 0

    while i < n:
        ch = code_stripped[i]

        if ch == '(':
            paren_depth += 1
        elif ch == ')':
            paren_depth -= 1
        elif ch == '{':
            brace_depth += 1
            open_loops.append({'type': 'block'})
        elif ch == '}':
            brace_depth -= 1
            while open_loops:
                top = open_loops.pop()
                if top['type'] == 'block':
                    break
                nesting_info.append(top)
        elif ch == ';' and paren_depth == 0:
            while open_loops and open_loops[-1]['type'] == 'loop' and not open_loops[-1]['has_brace']:
                nesting_info.append(open_loops.pop())
        else:
            kw = re.match(r'\b(for|while)\s*\(', code_stripped[i:])
            if kw and paren_depth == 0:
                start = i + kw.start()
                i += kw.end()
                p_depth = 1
                while i < n and p_depth > 0:
                    if code_stripped[i] == '(':
                        p_depth += 1
                    elif code_stripped[i] == ')':
                        p_depth -= 1
                    i += 1
                while i < n and code_stripped[i] in ' \n\r\t':
                    i += 1
                has_brace = i < n and code_stripped[i] == '{'
                open_loops.append({
                    'type': 'loop',
                    'start': start,
                    'keyword': kw.group(1),
                    'brace_depth': brace_depth,
                    'has_brace': has_brace,
                })
                max_nesting = max(max_nesting, len([x for x in open_loops if x['type'] == 'loop']))
                continue

        i += 1

    while open_loops:
        top = open_loops.pop()
        if top['type'] == 'loop':
            nesting_info.append(top)

    return nesting_info, max_nesting


def _get_containers_in_region(code: str, start: int, end: int):
    return set(re.findall(r'\b(\w+)\s*(?:\[|\.get\(|\.contains\()', code[start:end]))


def _detect_container_in_nested_loops(code_stripped: str, nesting_info: list):
    issues = []
    sorted_loops = sorted(nesting_info, key=lambda x: x['start'])
    for i, inner in enumerate(sorted_loops):
        for j, outer in enumerate(sorted_loops[:i]):
            inner_vars = _get_containers_in_region(code_stripped, inner['start'], min(inner['start'] + 200, len(code_stripped)))
            outer_vars = _get_containers_in_region(code_stripped, outer['start'], min(outer['start'] + 200, len(code_stripped)))
            shared = outer_vars & inner_vars
            for var in shared:
                if var and len(var) > 1:
                    issues.append({
                        'type': 'nested_loop_same_container',
                        'container': var,
                        'severity': 'high',
                        'description': f"Nested loops accessing same container '{var}'",
                    })
    return issues


def _check_region_for_patterns(code: str, start: int, end: int):
    issues = []
    region = code[start:end]
    if re.search(r'\bif\s*\(', region) and re.search(r'\bbreak\b', region):
        issues.append({
            'type': 'linear_search_in_loop',
            'container': '',
            'severity': 'medium',
            'description': 'Linear search pattern detected (loop with conditional break)',
        })
    if re.search(r'\bif\s*\(', region) and re.search(r'\b(?:swap|temp|tmp)', region):
        issues.append({
            'type': 'quadratic_sort',
            'container': '',
            'severity': 'high',
            'description': 'Nested loop with conditional swap (likely O(N^2) sort)',
        })
    if re.search(r'\+=\s*\w+\s*\+', region) or re.search(r'\bconcat\b', region) or re.search(r'\+\s*"\s*', region):
        issues.append({
            'type': 'string_concatenation_in_loop',
            'container': '',
            'severity': 'medium',
            'description': 'String concatenation inside loop (possible O(N^2) copying)',
        })
    if re.search(r'\.contains\(|\.indexOf\(', region):
        issues.append({
            'type': 'linear_lookup_in_loop',
            'container': '',
            'severity': 'high',
            'description': 'Linear lookup (List.contains / indexOf) inside loop',
        })
    return issues


def analyze_complexity(source_code: str, language: str = 'java') -> dict:
    try:
        code = _strip_comments(source_code)
    except Exception as e:
        logger.error(f"Failed to strip comments: {e}")
        code = source_code

    nesting_info, max_nesting = _detect_loop_nesting(code)

    if max_nesting == 0:
        complexity = "O(1)"
    elif max_nesting == 1:
        complexity = "O(N)"
    elif max_nesting == 2:
        complexity = "O(N^2)"
    elif max_nesting == 3:
        complexity = "O(N^3)"
    else:
        complexity = f"O(N^{max_nesting})"

    issues = []
    issues.extend(_detect_container_in_nested_loops(code, nesting_info))
    for loop in nesting_info:
        issues.extend(_check_region_for_patterns(code, loop['start'], min(loop['start'] + 300, len(code))))
    if re.search(r'\b(fibonacci|fib|factorial)\s*\(', code, re.IGNORECASE) and re.search(r'\bfor\b|\bwhile\b', code):
        issues.append({
            'type': 'recursive_recomputation',
            'container': '',
            'severity': 'high',
            'description': 'Naive recursive function called inside loop (exponential recomputation)',
        })

    seen_suggestions = set()
    suggestions = []
    for issue in issues:
        if issue['type'] == 'nested_loop_same_container':
            text = (
                f"Container '{issue['container']}' is accessed in nested loops, "
                f"suggesting O(N^2) or worse complexity. Consider: (1) sorting + linear pass, "
                f"(2) HashSet/HashMap for O(1) lookup, (3) single pass restructuring."
            )
        elif issue['type'] == 'quadratic_sort':
            text = (
                "Nested loop with conditional swap (possible O(N^2) sort). "
                "Replace with Arrays.sort() / Collections.sort() for O(N log N)."
            )
        elif issue['type'] == 'linear_search_in_loop':
            text = (
                "Linear search pattern detected inside loop. "
                "Replace repeated lookups with a HashSet / HashMap for O(1) average access."
            )
        elif issue['type'] == 'linear_lookup_in_loop':
            text = (
                "Linear lookup (.contains / .indexOf) inside loop. "
                "Convert collection to Set/Map before the loop for O(1) membership checks."
            )
        elif issue['type'] == 'string_concatenation_in_loop':
            text = (
                "String concatenation inside loop. "
                "Use StringBuilder instead of string addition to avoid repeated array allocations."
            )
        elif issue['type'] == 'recursive_recomputation':
            text = (
                "Naive recursive function called in a loop, causing exponential recomputation. "
                "Apply memoization or replace with an iterative algorithm."
            )
        else:
            text = issue['description']

        if text not in seen_suggestions:
            seen_suggestions.add(text)
            suggestions.append(text)

    if max_nesting >= 2 and not issues:
        suggestions.append(
            f"Loop nesting depth is {max_nesting} but no specific O(N^2) pattern was identified. "
            "Review inner loop for redundant computations that can be hoisted."
        )

    return {
        'estimated_complexity': complexity,
        'max_nesting_depth': max_nesting,
        'num_loops': len(nesting_info),
        'issues': issues,
        'suggestions': suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description="AST Complexity Analyzer for Java Source Code")
    parser.add_argument("--file", help="Path to Java source file to analyze")
    parser.add_argument("--code", help="Raw Java source code string")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
    elif args.code:
        code = args.code
    else:
        parser.error("Either --file or --code must be specified")

    res = analyze_complexity(code)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"Estimated Complexity: {res['estimated_complexity']}")
        print(f"Max Loop Nesting Depth: {res['max_nesting_depth']}")
        print(f"Number of Loops: {res['num_loops']}")
        print(f"Issues Detected: {len(res['issues'])}")
        for i, issue in enumerate(res['issues'], 1):
            print(f"  {i}. [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
        print(f"Suggestions: {len(res['suggestions'])}")
        for i, sug in enumerate(res['suggestions'], 1):
            print(f"  {i}. {sug}")


if __name__ == "__main__":
    main()
