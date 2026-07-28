#!/usr/bin/env python3
"""
findings.json Generator.

Builds the findings.json schema TASK/SUBMISSION.md requires directly from a real KùzuDB analysis
run (analyze_anomalies.py's T1-T9 + Section 7 output), instead of a hand-written literal. See
plan/004-findings-json-generator.md for the spec this implements.
"""

import argparse
import datetime
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from analyze_anomalies import analyze_anomalies  # noqa: E402
from source_mapping import resolve_source_location  # noqa: E402
from differential_analysis import compare_runs, list_run_ids  # noqa: E402


# taxonomy_id -> allowed SUBMISSION.md `family` value (db|cpu|memory|algo|redundant).
TAXONOMY_TO_FAMILY = {
    "T1": "redundant",
    "T2": "algo",
    "T3": "memory",
    "T4": "memory",
    "T6": "db",
    "T7": "memory",
    "T8": "memory",
    "T9": "cpu",
}

# T5 ("Избыточные проверки и блоки кода") is mapped per-type rather than uniformly, per spec 004 —
# currently every T5 type happens to land on "redundant", but this stays a per-type table so a
# future T5 type (e.g. something closer to dead-weight memory) isn't forced into the wrong family.
T5_TYPE_TO_FAMILY = {
    "DEAD_OR_UNREACHABLE_CODE": "redundant",
    "DUPLICATE_LAYER_VALIDATION": "redundant",
    "CODE_STYLE_FORMATTING": "redundant",
}

# Generic, taxonomy-level fix guidance keyed by the anomaly's specific `type` — deliberately not
# tied to any sandbox class/method name (see TASK/SUBMISSION.md's penalty for project-hardcoded rules).
FIX_SUGGESTIONS = {
    "SAVE_IN_LOOP_UNBATCHED": "Accumulate the entities and persist them in one batched call (e.g. saveAll with JDBC batching enabled) instead of saving one at a time inside the loop.",
    "EXCESSIVE_STRING_CONCAT": "Reuse a single StringBuilder outside the loop instead of repeated concatenation, or avoid building the string at all if it isn't used every iteration.",
    "LINEAR_SEARCH_IN_LOOP": "Replace the linear List.contains/indexOf lookup with a Set or Map keyed for O(1) membership checks.",
    "QUADRATIC_NESTED_LOOP": "Precompute a lookup structure (Set/Map) before the outer loop instead of scanning the inner collection on every iteration.",
    "HEAVY_ENTITY_FETCH": "Fetch only the fields actually needed via a projection/DTO instead of loading the full managed entity.",
    "FULL_FETCH_FOR_EXISTENCE_CHECK": "Replace the full fetch with an existsBy...()/COUNT query that never materializes the entity.",
    "BOXED_WRAPPER_OVERHEAD": "Use primitive collections/arrays where possible to avoid per-element boxing allocation.",
    "ARRAY_ALLOCATION_PRESSURE": "Reuse or pre-size the buffer instead of repeatedly reallocating large arrays.",
    "DEAD_OR_UNREACHABLE_CODE": "Remove the unreachable code path, or add a test/entry point that actually exercises it if it's still needed.",
    "DUPLICATE_LAYER_VALIDATION": "Consolidate the repeated check into a single layer instead of validating the same condition at every call site.",
    "CODE_STYLE_FORMATTING": "No functional fix needed — this is a style-only observation.",
    "N_PLUS_ONE_QUERIES": "Use JOIN FETCH or an @EntityGraph to load the association in the same query instead of triggering N lazy-loads.",
    "CONNECTION_POOL_STARVATION": "Increase the pool size or shorten held-connection time so waiters aren't blocked on exhaustion.",
    "RETAINED_OBJECT_ACCUMULATION": "Ensure the referenced objects are released/evicted — check for a missing bound on how long they're retained.",
    "UNBOUNDED_CACHE_OR_COLLECTION_GROWTH": "Bound the collection with a max size and eviction policy (e.g. an LRU cache) instead of growing it unconditionally.",
    "IN_MEMORY_FILTERING": "Push the filter/pagination down to the database query (WHERE/LIMIT) instead of loading everything into memory first.",
    "EXCESSIVE_STRING_ALLOCATIONS": "Reduce string churn — reuse a StringBuilder or avoid intermediate string creation in the hot path.",
    "BOUNDED_REQUEST_COLLECTION": "No fix needed — the collection size is already bounded by the request contract.",
    "THREAD_LOCK_CONTENTION": "Shrink the critical section, or replace the lock with a finer-grained/lock-free alternative if contention is the bottleneck.",
    "CPU_HOTSPOT_METHOD": "Profile this method further and optimize its hot path (algorithmic change or caching) since it dominates CPU time.",
    "MICROBENCHMARK_REGEX_COMPILE": "Compile the Pattern once (e.g. as a static final field) instead of recompiling it on every call.",
}
DEFAULT_FIX_SUGGESTION = "Investigate the mechanism described above and address it at the identified call site."


def _log(run_log_path: str, level: str, message: str):
    if not run_log_path:
        return
    os.makedirs(os.path.dirname(run_log_path) or ".", exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    with open(run_log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")


def _family_for(anomaly: dict) -> str:
    taxonomy_id = anomaly.get("taxonomy_id", "")
    if taxonomy_id == "T5":
        return T5_TYPE_TO_FAMILY.get(anomaly.get("type", ""), "redundant")
    return TAXONOMY_TO_FAMILY.get(taxonomy_id, "redundant")


_FILE_LINE_RE = re.compile(r"^(.+\.java):(\d+)$")


def _resolve_one(value: str):
    """
    Resolves a single caller/callee value to (file, line_from, line_to). Handles both the
    Method.id convention used by the Cypher-based analyzers (resolved via resolve_source_location)
    and the "path/File.java:line" convention the static detectors (spec 009) already produce
    natively — those don't need re-resolving, just parsing back out.
    """
    m = _FILE_LINE_RE.match(value)
    if m:
        line = int(m.group(2))
        return m.group(1), line, line
    return resolve_source_location(value)


def _resolve_location_for_anomaly(anomaly: dict):
    """Prefers the callee (where the problematic action actually happens) over the caller."""
    callee = anomaly.get("callee", "")
    caller = anomaly.get("caller", "")
    loc = _resolve_one(callee) if callee else None
    if loc is not None:
        return loc
    loc = _resolve_one(caller) if caller else None
    return loc


def build_schema_report(set_name: str, level_name: str, findings: list, checked_but_not_an_issue: list) -> dict:
    return {
        "set": set_name,
        "level": level_name,
        "findings": findings,
        "checked_but_not_an_issue": checked_but_not_an_issue,
    }


def _build_diff_index(diffs: list):
    """
    Indexes compare_runs() output for lookup by anomaly caller/callee: CALLS.count entries are
    keyed by the full "caller -> callee" edge (exact match) and, as a fallback, by callee alone;
    Allocation.bytes/RetainedObject.count entries (single-method, no caller) are keyed by method.
    """
    by_edge, by_method = {}, {}
    for d in diffs:
        if d["metric"] == "CALLS.count" and " -> " in d["method"]:
            by_edge[d["method"]] = d
            callee = d["method"].rsplit(" -> ", 1)[-1]
            by_method.setdefault(callee, d)
        else:
            by_method.setdefault(d["method"], d)
    return by_edge, by_method


def _find_diff_for_anomaly(by_edge: dict, by_method: dict, anomaly: dict):
    edge_key = f"{anomaly.get('caller', '')} -> {anomaly.get('callee', '')}"
    if edge_key in by_edge:
        return by_edge[edge_key]
    return by_method.get(anomaly.get("callee", ""))


def build_findings_from_anomalies(
    anomalies: list,
    run_log_path: str = None,
    diff_entries: list = None,
    baseline_run_id: str = None,
    candidate_run_id: str = None,
):
    """
    Splits a real analyze_anomalies() result into (findings, checked_but_not_an_issue), resolving
    every anomaly's file/line via resolve_source_location() and dropping (with a log entry) any
    anomaly whose caller/callee both fail to resolve to project source.

    When diff_entries (from differential_analysis.compare_runs(), spec 011) is provided, findings
    whose caller/callee match a real cross-run delta get that measured before/after as evidence
    instead of the single-run sample-count placeholder.
    """
    findings = []
    checked_but_not_an_issue = []
    skipped = 0
    by_edge, by_method = _build_diff_index(diff_entries) if diff_entries else ({}, {})

    for anomaly in anomalies:
        location = _resolve_location_for_anomaly(anomaly)
        taxonomy_id = anomaly.get("taxonomy_id", "TAX")
        anomaly_type = anomaly.get("type", "UNKNOWN")

        if location is None:
            skipped += 1
            _log(
                run_log_path,
                "WARNING",
                f"Skipped {taxonomy_id}/{anomaly_type} anomaly (caller={anomaly.get('caller')!r}, "
                f"callee={anomaly.get('callee')!r}): neither frame resolves to project source under src/main/java.",
            )
            continue

        file_path, line_from, line_to = location

        if anomaly.get("status") == "NON_DEFECT":
            checked_but_not_an_issue.append({
                "file": file_path,
                "claim": anomaly.get("description", ""),
                "why_not": anomaly.get("non_defect_justification", ""),
            })
            continue

        sample_count = anomaly.get("sample_count", 0)
        percentage = anomaly.get("percentage", 0.0)
        severity = anomaly.get("severity", "MEDIUM")
        category = anomaly.get("category", "")

        diff = _find_diff_for_anomaly(by_edge, by_method, anomaly)
        if diff is not None:
            evidence = {
                "channel": diff["metric"],
                "before": diff["before"],
                "after": diff["after"],
                "how": (
                    f"Differential comparison between runId={baseline_run_id!r} (before) and "
                    f"runId={candidate_run_id!r} (after) in the same profiling database"
                    + (f"; measured delta {diff['delta_pct']:+.1f}%." if diff["delta_pct"] is not None else ".")
                ),
            }
        else:
            evidence = {
                "channel": "Profiler-Sample-Count",
                "before": sample_count,
                "after": None,
                "how": (
                    f"Single profiling run, {percentage}% of total samples on this edge/method; "
                    f"not a measured before/after comparison — see plan/011-relative-thresholds-and-multirun-diff.md "
                    f"for real differential evidence."
                ),
            }

        findings.append({
            "file": file_path,
            "line_from": line_from,
            "line_to": line_to,
            "family": _family_for(anomaly),
            "pdf_taxonomy": [taxonomy_id],
            "mechanism": anomaly.get("description", ""),
            "impact": f"{severity} severity {category.lower().replace('_', ' ')} — {sample_count} profiled samples ({percentage}% of the run).",
            "fix": FIX_SUGGESTIONS.get(anomaly_type, DEFAULT_FIX_SUGGESTION),
            "evidence": evidence,
        })

    if run_log_path:
        _log(run_log_path, "INFO", f"findings.json generation: {len(findings)} findings, {len(checked_but_not_an_issue)} checked_but_not_an_issue, {skipped} anomalies skipped (unresolvable location).")

    return findings, checked_but_not_an_issue, skipped


def _detect_run_ids(db_path: str, explicit_baseline: str, explicit_candidate: str, run_log_path: str):
    """
    Returns (baseline_run_id, candidate_run_id, diff_entries) — or (None, None, None) if
    differential evidence isn't available. Explicit --baseline-run-id/--candidate-run-id win;
    otherwise, if the database happens to hold exactly two distinct runId values (e.g. a `/bad` vs
    `/good` load-test pair, or a before/after fix comparison), they're used automatically, ordered
    by the Run node's timestamp. Any other case (0, 1, or 3+ runs without explicit selection) keeps
    the existing single-run placeholder evidence (spec 004) — this is the regression path spec 011
    requires: no crash, just no differential evidence to offer.
    """
    import kuzu as _kuzu

    db = _kuzu.Database(db_path)
    conn = _kuzu.Connection(db)

    if explicit_baseline and explicit_candidate:
        baseline, candidate = explicit_baseline, explicit_candidate
    else:
        run_ids = list_run_ids(conn)
        if len(run_ids) != 2:
            return None, None, None
        res = conn.execute("MATCH (r:Run) WHERE r.id IN $ids RETURN r.id, r.timestamp", {"ids": run_ids})
        timestamps = {}
        while res.has_next():
            rid, ts = res.get_next()
            timestamps[rid] = ts
        ordered = sorted(run_ids, key=lambda r: timestamps.get(r) or r)
        baseline, candidate = ordered[0], ordered[1]

    diff_entries = compare_runs(conn, baseline, candidate)
    _log(run_log_path, "INFO", f"Differential evidence: comparing runId={baseline!r} (baseline) vs runId={candidate!r} (candidate), {len(diff_entries)} deltas found.")
    return baseline, candidate, diff_entries


def main():
    parser = argparse.ArgumentParser(description="Generate findings.json from a real KùzuDB anomaly analysis run")
    parser.add_argument("--db-path", required=True, help="Path to the KùzuDB database to analyze")
    parser.add_argument("--set", dest="set_name", default="sandbox", help="Value for the 'set' field (default: sandbox)")
    parser.add_argument("--level", dest="level_name", default="hard", help="Value for the 'level' field (default: hard)")
    parser.add_argument("--category", help="Comma-separated taxonomy IDs to run (default: all T1-T9)")
    parser.add_argument("--baseline-run-id", help="Run to treat as 'before' for differential evidence (auto-detected if exactly 2 runs exist in the DB)")
    parser.add_argument("--candidate-run-id", help="Run to treat as 'after' for differential evidence")
    parser.add_argument("--output", default=os.path.join(REPO_ROOT, "reports", "sandbox", "findings.json"), help="Where to write findings.json")
    parser.add_argument("--run-log", default=os.path.join(REPO_ROOT, "runlog", "agent_run.log"), help="Audit log to append skip/summary entries to")
    args = parser.parse_args()

    selected = [c.strip().upper() for c in args.category.split(",")] if args.category else None
    anomalies = analyze_anomalies(args.db_path, selected)

    baseline_run_id, candidate_run_id, diff_entries = _detect_run_ids(
        args.db_path, args.baseline_run_id, args.candidate_run_id, args.run_log
    )

    findings, checked_but_not_an_issue, skipped = build_findings_from_anomalies(
        anomalies, args.run_log, diff_entries, baseline_run_id, candidate_run_id
    )
    report = build_schema_report(args.set_name, args.level_name, findings, checked_but_not_an_issue)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(findings)} findings and {len(checked_but_not_an_issue)} checked_but_not_an_issue entries to {args.output}")
    if skipped:
        print(f"Skipped {skipped} anomalies with no resolvable source location (see {args.run_log})")


if __name__ == "__main__":
    main()
