"""
Cross-run (baseline vs. candidate) differential analysis.
"""

from typing import List


def _delta_pct(before: float, after: float):
    if before:
        return round((after - before) / before * 100, 1)
    return None


def _diff_calls_edges(conn, baseline_run_id: str, candidate_run_id: str) -> List[dict]:
    def _snapshot(run_id):
        res = conn.execute(
            """
            MATCH (a:Method)-[r:CALLS]->(b:Method)
            WHERE r.runId = $rid
            RETURN a.className + '.' + a.methodName AS caller,
                   b.className + '.' + b.methodName AS callee, r.count AS count
            """,
            {"rid": run_id},
        )
        snap = {}
        while res.has_next():
            caller, callee, count = res.get_next()
            snap[(caller, callee)] = int(count)
        return snap

    baseline = _snapshot(baseline_run_id)
    candidate = _snapshot(candidate_run_id)

    diffs = []
    for key in set(baseline) | set(candidate):
        before = baseline.get(key, 0)
        after = candidate.get(key, 0)
        if before == 0 and after == 0:
            continue
        diffs.append({
            "method": f"{key[0]} -> {key[1]}",
            "metric": "CALLS.count",
            "before": before,
            "after": after,
            "delta_pct": _delta_pct(before, after),
        })
    return diffs


def _diff_allocation_bytes(conn, baseline_run_id: str, candidate_run_id: str) -> List[dict]:
    def _snapshot(run_id):
        res = conn.execute(
            """
            MATCH (a:Allocation)-[:ALLOCATED_BY]->(m:Method)
            WHERE a.runId = $rid
            RETURN m.className + '.' + m.methodName AS method, sum(a.bytes) AS totalBytes
            """,
            {"rid": run_id},
        )
        snap = {}
        while res.has_next():
            method, total_bytes = res.get_next()
            snap[method] = int(total_bytes) if total_bytes is not None else 0
        return snap

    baseline = _snapshot(baseline_run_id)
    candidate = _snapshot(candidate_run_id)

    diffs = []
    for method in set(baseline) | set(candidate):
        before = baseline.get(method, 0)
        after = candidate.get(method, 0)
        if before == 0 and after == 0:
            continue
        diffs.append({
            "method": method,
            "metric": "Allocation.bytes",
            "before": before,
            "after": after,
            "delta_pct": _delta_pct(before, after),
        })
    return diffs


def _diff_retained_count(conn, baseline_run_id: str, candidate_run_id: str) -> List[dict]:
    def _snapshot(run_id):
        res = conn.execute(
            """
            MATCH (r:RetainedObject)-[:RETAINED_BY]->(m:Method)
            WHERE r.runId = $rid
            RETURN m.className + '.' + m.methodName AS method, count(r) AS retainedCount
            """,
            {"rid": run_id},
        )
        snap = {}
        while res.has_next():
            method, retained_count = res.get_next()
            snap[method] = int(retained_count)
        return snap

    baseline = _snapshot(baseline_run_id)
    candidate = _snapshot(candidate_run_id)

    diffs = []
    for method in set(baseline) | set(candidate):
        before = baseline.get(method, 0)
        after = candidate.get(method, 0)
        if before == 0 and after == 0:
            continue
        diffs.append({
            "method": method,
            "metric": "RetainedObject.count",
            "before": before,
            "after": after,
            "delta_pct": _delta_pct(before, after),
        })
    return diffs


def compare_runs(conn, baseline_run_id: str, candidate_run_id: str) -> List[dict]:
    diffs = []
    diffs.extend(_diff_calls_edges(conn, baseline_run_id, candidate_run_id))
    diffs.extend(_diff_allocation_bytes(conn, baseline_run_id, candidate_run_id))
    diffs.extend(_diff_retained_count(conn, baseline_run_id, candidate_run_id))

    def _sort_key(d):
        if d["delta_pct"] is not None:
            return abs(d["delta_pct"])
        return abs(d["after"] - d["before"])

    diffs.sort(key=_sort_key, reverse=True)
    return diffs


def list_run_ids(conn) -> List[str]:
    run_ids = set()
    for query in (
        "MATCH ()-[r:CALLS]->() RETURN DISTINCT r.runId",
        "MATCH (a:Allocation) RETURN DISTINCT a.runId",
        "MATCH (r:RetainedObject) RETURN DISTINCT r.runId",
        "MATCH (b:MonitorBlock) RETURN DISTINCT b.runId",
    ):
        res = conn.execute(query)
        while res.has_next():
            rid = res.get_next()[0]
            if rid:
                run_ids.add(rid)
    return sorted(run_ids)


def main():
    import argparse
    import json

    import kuzu

    parser = argparse.ArgumentParser(description="Differential analysis between two profiling runs in one KuzuDB")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--baseline-run-id", required=True)
    parser.add_argument("--candidate-run-id", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    db = kuzu.Database(args.db_path)
    conn = kuzu.Connection(db)
    diffs = compare_runs(conn, args.baseline_run_id, args.candidate_run_id)

    if args.json:
        print(json.dumps(diffs, indent=2))
    else:
        for d in diffs:
            sign = f"{d['delta_pct']:+.1f}%" if d["delta_pct"] is not None else "(new)"
            print(f"[{d['metric']}] {d['method']}: {d['before']} -> {d['after']} ({sign})")


if __name__ == "__main__":
    main()
