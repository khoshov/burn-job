"""
findings.json Generator.
"""

import argparse
import datetime
import json
import os
import re
import sys

from burn_job.detectors.orchestrate import analyze_anomalies
from burn_job.detectors.source_mapping import resolve_source_location
from burn_job.detectors.differential import compare_runs, list_run_ids


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

T5_TYPE_TO_FAMILY = {
    "DEAD_OR_UNREACHABLE_CODE": "redundant",
    "DUPLICATE_LAYER_VALIDATION": "redundant",
    "CODE_STYLE_FORMATTING": "redundant",
}

ANOMALY_TYPE_TO_TAXONOMY_CODES = {
    "N_PLUS_ONE_QUERIES": ["T6", "T2"],
    "SAVE_IN_LOOP_UNBATCHED": ["T1", "T6"],
    "HEAVY_ENTITY_FETCH": ["T3", "T4"],
    "IN_MEMORY_FILTERING": ["T8", "T3"],
}

FIX_SUGGESTIONS = {
    "SAVE_IN_LOOP_UNBATCHED": "Accumulate the entities and persist them in one batched call (e.g. saveAll with JDBC batching enabled) instead of saving one at a time inside the loop.",
    "EXCESSIVE_STRING_CONCAT": "Reuse a single StringBuilder outside the loop instead of repeated concatenation, or avoid building the string at all if it is not used every iteration.",
    "LINEAR_SEARCH_IN_LOOP": "Replace the linear List.contains/indexOf lookup with a Set or Map keyed for O(1) membership checks.",
    "QUADRATIC_NESTED_LOOP": "Precompute a lookup structure (Set/Map) before the outer loop instead of scanning the inner collection on every iteration.",
    "HEAVY_ENTITY_FETCH": "Fetch only the fields actually needed via a projection/DTO instead of loading the full managed entity.",
    "FULL_FETCH_FOR_EXISTENCE_CHECK": "Replace the full fetch with an existsBy...()/COUNT query that never materializes the entity.",
    "BOXED_WRAPPER_OVERHEAD": "Use primitive collections/arrays where possible to avoid per-element boxing allocation.",
    "ARRAY_ALLOCATION_PRESSURE": "Reuse or pre-size the buffer instead of repeatedly reallocating large arrays.",
    "DEAD_OR_UNREACHABLE_CODE": "Remove the unreachable code path, or add a test/entry point that actually exercises it if it is still needed.",
    "DUPLICATE_LAYER_VALIDATION": "Consolidate the repeated check into a single layer instead of validating the same condition at every call site.",
    "CODE_STYLE_FORMATTING": "No functional fix needed - this is a style-only observation.",
    "N_PLUS_ONE_QUERIES": "Use JOIN FETCH or an @EntityGraph to load the association in the same query instead of triggering N lazy-loads.",
    "CONNECTION_POOL_STARVATION": "Increase the pool size or shorten held-connection time so waiters are not blocked on exhaustion.",
    "RETAINED_OBJECT_ACCUMULATION": "Ensure the referenced objects are released/evicted - check for a missing bound on how long they are retained.",
    "UNBOUNDED_CACHE_OR_COLLECTION_GROWTH": "Bound the collection with a max size and eviction policy (e.g. an LRU cache) instead of growing it unconditionally.",
    "IN_MEMORY_FILTERING": "Push the filter/pagination down to the database query (WHERE/LIMIT) instead of loading everything into memory first.",
    "EXCESSIVE_STRING_ALLOCATIONS": "Reduce string churn - reuse a StringBuilder or avoid intermediate string creation in the hot path.",
    "BOUNDED_REQUEST_COLLECTION": "No fix needed - the collection size is already bounded by the request contract.",
    "THREAD_LOCK_CONTENTION": "Shrink the critical section, or replace the lock with a finer-grained/lock-free alternative if contention is the bottleneck.",
    "CPU_HOTSPOT_METHOD": "Profile this method further and optimize its hot path (algorithmic change or caching) since it dominates CPU time.",
    "MICROBENCHMARK_REGEX_COMPILE": "Compile the Pattern once (e.g. as a static final field) instead of recompiling it on every call.",
}
DEFAULT_FIX_SUGGESTION = "Investigate the mechanism described above and address it at the identified call site."


def generate_burn_job_report():
    return build_schema_report("burn-job", "hard", [], [])


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


def _channel_for(family: str, taxonomy_id: str, diff_metric: str = None) -> str:
    VALID_ENUM = {"X-Sql-Count", "X-Elapsed-Ms", "jvm.memory.used", "jvm.memory.usage.after.gc", "JFR"}
    if diff_metric and diff_metric in VALID_ENUM:
        return diff_metric
    if diff_metric == "CALLS.count":
        return "X-Sql-Count" if family == "db" else "X-Elapsed-Ms"
    elif diff_metric == "Allocation.bytes":
        return "jvm.memory.used"
    elif diff_metric == "RetainedObject.count":
        return "jvm.memory.usage.after.gc"

    if family == "db":
        return "X-Sql-Count"
    elif family == "cpu":
        return "JFR"
    elif family == "memory":
        if taxonomy_id == "T7":
            return "jvm.memory.usage.after.gc"
        return "jvm.memory.used"
    else:
        return "X-Elapsed-Ms"


_FILE_LINE_RE = re.compile(r"^(.+\.java):(\d+)$")


def _resolve_one(value: str):
    m = _FILE_LINE_RE.match(value)
    if m:
        line = int(m.group(2))
        return m.group(1), line, line
    return resolve_source_location(value)


def _resolve_location_for_anomaly(anomaly: dict):
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
        family = _family_for(anomaly)

        diff = _find_diff_for_anomaly(by_edge, by_method, anomaly)
        if diff is not None:
            channel = _channel_for(family, taxonomy_id, diff.get("metric"))
            evidence = {
                "channel": channel,
                "before": diff["before"],
                "after": diff["after"],
                "how": (
                    f"Differential comparison between runId={baseline_run_id!r} (before) and "
                    f"runId={candidate_run_id!r} (after) in profiling database"
                    + (f"; measured delta {diff['delta_pct']:+.1f}%." if diff["delta_pct"] is not None else ".")
                ),
            }
        else:
            channel = _channel_for(family, taxonomy_id)
            evidence = {
                "channel": channel,
                "before": sample_count,
                "after": 0,
                "how": (
                    f"Single profiling run ({sample_count} samples, {percentage}% of total run). "
                    f"The 'after' value (0) is a predicted post-fix projection pending differential multi-run comparison."
                ),
            }

        pdf_taxonomy = ANOMALY_TYPE_TO_TAXONOMY_CODES.get(anomaly_type, [taxonomy_id])

        findings.append({
            "file": file_path,
            "line_from": line_from,
            "line_to": line_to,
            "family": family,
            "pdf_taxonomy": pdf_taxonomy,
            "mechanism": anomaly.get("description", ""),
            "impact": f"{severity} severity {category.lower().replace('_', ' ')} - {sample_count} profiled samples ({percentage}% of the run).",
            "fix": FIX_SUGGESTIONS.get(anomaly_type, DEFAULT_FIX_SUGGESTION),
            "evidence": evidence,
        })

    if run_log_path:
        _log(run_log_path, "INFO", f"findings.json generation: {len(findings)} findings, {len(checked_but_not_an_issue)} checked_but_not_an_issue, {skipped} anomalies skipped (unresolvable location).")

    return findings, checked_but_not_an_issue, skipped


def _detect_run_ids(db_path: str, explicit_baseline: str, explicit_candidate: str, run_log_path: str):
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
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))

    parser = argparse.ArgumentParser(description="Generate findings.json from a real KuzuDB anomaly analysis run")
    parser.add_argument("--db-path", required=True, help="Path to the KuzuDB database to analyze")
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
