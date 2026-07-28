#!/usr/bin/env python3
"""
Profiler Call Graph Ingestor for KùzuDB (The Embedded "SQLite of Graph DBs").
Parses async-profiler collapsed stack traces or JFR exports and loads call trees into KùzuDB.
"""

import sys
import os
import json
import subprocess
import argparse
import datetime
from collections import defaultdict
from typing import Dict, Tuple, List

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False


JFR_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "..", "tools")
JFR_DUMP_SRC = os.path.join(JFR_TOOLS_DIR, "JfrDump.java")

# Event types whose stack traces feed the CPU call graph (Method/CALLS).
CPU_EVENT_TYPES = ("jdk.ExecutionSample", "jdk.NativeMethodSample")


def _ensure_jfr_dump_compiled() -> str:
    """Lazily compiles JfrDump.java, returns the classpath dir to run it from."""
    class_file = os.path.join(JFR_TOOLS_DIR, "JfrDump.class")
    needs_compile = (
        not os.path.exists(class_file)
        or os.path.getmtime(JFR_DUMP_SRC) > os.path.getmtime(class_file)
    )
    if needs_compile:
        res = subprocess.run(["javac", "-d", JFR_TOOLS_DIR, JFR_DUMP_SRC], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to compile JfrDump.java: {res.stderr}")
    return JFR_TOOLS_DIR


def parse_jfr_events(file_path: str) -> Dict[str, list]:
    """Runs JfrDump against a .jfr file, returns events grouped by eventType."""
    classpath = _ensure_jfr_dump_compiled()
    res = subprocess.run(["java", "-cp", classpath, "JfrDump", file_path], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"JfrDump failed on '{file_path}': {res.stderr}")

    events_by_type: Dict[str, list] = defaultdict(list)
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        events_by_type[event["eventType"]].append(event)
    return events_by_type


def build_graph_data_from_jfr_events(events_by_type: Dict[str, list]) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], int]:
    """
    Builds edge_counts/method_counts/total_samples from CPU-sample-type JFR events
    (jdk.ExecutionSample / jdk.NativeMethodSample), in the same shape as parse_collapsed_stack.
    """
    edge_counts = defaultdict(int)
    method_counts = defaultdict(int)
    total_samples = 0

    cpu_events = []
    for event_type in CPU_EVENT_TYPES:
        cpu_events.extend(events_by_type.get(event_type, []))

    for event in cpu_events:
        frames = event.get("stack") or []
        if not frames:
            continue

        total_samples += 1
        method_counts[frames[-1]] += 1

        for f in frames:
            if f not in method_counts:
                method_counts[f] = 0

        for i in range(len(frames) - 1):
            edge_counts[(frames[i], frames[i + 1])] += 1

    return edge_counts, method_counts, total_samples


def parse_profile(file_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], int, Dict[str, list]]:
    """
    Single entry point for both input formats.
    Returns edge_counts, method_counts, total_samples, other_jfr_events
    (other_jfr_events is empty for .collapsed input; for .jfr input it holds every
    extracted event group besides the CPU-sample ones already folded into the call graph).
    """
    if file_path.lower().endswith(".jfr"):
        events_by_type = parse_jfr_events(file_path)
        edge_counts, method_counts, total_samples = build_graph_data_from_jfr_events(events_by_type)
        other_events = {k: v for k, v in events_by_type.items() if k not in CPU_EVENT_TYPES}
        return edge_counts, method_counts, total_samples, other_events

    edge_counts, method_counts, total_samples = parse_collapsed_stack(file_path)
    return edge_counts, method_counts, total_samples, {}


def parse_collapsed_stack(file_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], int]:
    """
    Parses async-profiler collapsed format: frame1;frame2;frame3 sample_count
    Returns:
      - edge_counts: (caller, callee) -> count
      - method_counts: method -> self/total samples
      - total_samples: total samples in profile
    """
    edge_counts = defaultdict(int)
    method_counts = defaultdict(int)
    total_samples = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue

            stack_str, count_str = parts[0], parts[1]
            try:
                count = int(count_str)
            except ValueError:
                continue

            frames = [f.strip() for f in stack_str.split(";") if f.strip()]
            if not frames:
                continue

            total_samples += count

            # Count leaf (self) sample
            method_counts[frames[-1]] += count

            # Ensure all frames are registered as Method nodes
            for f in frames:
                if f not in method_counts:
                    method_counts[f] = 0

            # Build edges
            for i in range(len(frames) - 1):
                caller = frames[i]
                callee = frames[i + 1]
                edge_counts[(caller, callee)] += count

    return edge_counts, method_counts, total_samples


def extract_class_and_method(full_name: str) -> Tuple[str, str, str]:
    """Extracts package, class name, and method name from full qualified method string."""
    if "." in full_name:
        parts = full_name.rsplit(".", 1)
        method_name = parts[1]
        full_class = parts[0]
        if "." in full_class:
            pkg, class_name = full_class.rsplit(".", 1)
        else:
            pkg = ""
            class_name = full_class
    else:
        pkg = ""
        class_name = "Global"
        method_name = full_name

    return pkg, class_name, method_name


def init_kuzu_schema(conn: "kuzu.Connection"):
    """Creates node and relationship tables in KùzuDB if not already present."""
    schemas = [
        "CREATE NODE TABLE IF NOT EXISTS Run(id STRING, timestamp STRING, PRIMARY KEY (id))",
        "CREATE NODE TABLE IF NOT EXISTS Test(id STRING, name STRING, PRIMARY KEY (id))",
        "CREATE NODE TABLE IF NOT EXISTS Method(id STRING, pkg STRING, className STRING, methodName STRING, sampleCount INT64, PRIMARY KEY (id))",
        "CREATE REL TABLE IF NOT EXISTS EXECUTED_TEST(FROM Run TO Test)",
        "CREATE REL TABLE IF NOT EXISTS CALLS(FROM Method TO Method, count INT64, percent DOUBLE, runId STRING)",
        # Non-CPU JFR event types (spec plan/002) — allocations, retained objects, monitor/park blocking.
        "CREATE NODE TABLE IF NOT EXISTS Allocation(id STRING, className STRING, bytes INT64, count INT64, runId STRING, PRIMARY KEY (id))",
        "CREATE NODE TABLE IF NOT EXISTS RetainedObject(id STRING, className STRING, ageMs INT64, allocationStack STRING, runId STRING, PRIMARY KEY (id))",
        "CREATE NODE TABLE IF NOT EXISTS MonitorBlock(id STRING, className STRING, durationMs INT64, runId STRING, PRIMARY KEY (id))",
        "CREATE REL TABLE IF NOT EXISTS ALLOCATED_BY(FROM Allocation TO Method)",
        "CREATE REL TABLE IF NOT EXISTS RETAINED_BY(FROM RetainedObject TO Method)",
        "CREATE REL TABLE IF NOT EXISTS BLOCKED_IN(FROM MonitorBlock TO Method)",
    ]
    for stmt in schemas:
        try:
            conn.execute(stmt)
        except Exception:
            pass


def _merge_method_nodes_for_stack(conn: "kuzu.Connection", frames: List[str]):
    """Ensures a Method node exists for every frame in a stack, without touching sampleCount if it already exists."""
    for f in frames:
        pkg, class_name, m_name = extract_class_and_method(f)
        conn.execute("""
            MERGE (m:Method {id: $id})
            ON CREATE SET m.pkg = $pkg, m.className = $cls, m.methodName = $mname, m.sampleCount = 0
        """, {"id": f, "pkg": pkg, "cls": class_name, "mname": m_name})


def ingest_jfr_events_to_kuzu(conn: "kuzu.Connection", run_id: str, other_jfr_events: Dict[str, list]):
    """
    Ingests non-CPU JFR event types (allocations, retained objects, monitor/park blocking) as
    new node types, each linked via a dedicated relationship to the Method node representing the
    leaf (deepest) stack frame — the method where the event actually occurred. Method nodes are
    merged for every frame in the stack, same as the CPU call-graph path.
    """
    allocation_events = other_jfr_events.get("jdk.ObjectAllocationSample", [])
    for i, event in enumerate(allocation_events):
        stack = event.get("stack") or []
        if not stack:
            continue
        _merge_method_nodes_for_stack(conn, stack)
        alloc_id = f"{run_id}_alloc_{i}"
        conn.execute("""
            MERGE (a:Allocation {id: $id})
            ON CREATE SET a.className = $cls, a.bytes = $bytes, a.count = 1, a.runId = $rid
        """, {"id": alloc_id, "cls": event.get("objectClass", "Unknown"), "bytes": event.get("weight", 0), "rid": run_id})
        conn.execute("""
            MATCH (a:Allocation {id: $aid}), (m:Method {id: $mid})
            MERGE (a)-[:ALLOCATED_BY]->(m)
        """, {"aid": alloc_id, "mid": stack[-1]})

    retained_events = other_jfr_events.get("jdk.OldObjectSample", [])
    for i, event in enumerate(retained_events):
        stack = event.get("stack") or []
        if not stack:
            continue
        _merge_method_nodes_for_stack(conn, stack)
        retained_id = f"{run_id}_retained_{i}"
        conn.execute("""
            MERGE (r:RetainedObject {id: $id})
            ON CREATE SET r.className = $cls, r.ageMs = $age, r.allocationStack = $stack, r.runId = $rid
        """, {
            "id": retained_id,
            "cls": event.get("objectClass", "Unknown"),
            "age": event.get("ageMs", 0),
            "stack": ";".join(stack),
            "rid": run_id,
        })
        conn.execute("""
            MATCH (r:RetainedObject {id: $rid_}), (m:Method {id: $mid})
            MERGE (r)-[:RETAINED_BY]->(m)
        """, {"rid_": retained_id, "mid": stack[-1]})

    monitor_events = other_jfr_events.get("jdk.JavaMonitorEnter", []) + other_jfr_events.get("jdk.ThreadPark", [])
    for i, event in enumerate(monitor_events):
        stack = event.get("stack") or []
        if not stack:
            continue
        _merge_method_nodes_for_stack(conn, stack)
        class_name = event.get("monitorClass") or event.get("parkedClass") or "Unknown"
        monitor_id = f"{run_id}_monitor_{i}"
        conn.execute("""
            MERGE (b:MonitorBlock {id: $id})
            ON CREATE SET b.className = $cls, b.durationMs = $dur, b.runId = $rid
        """, {"id": monitor_id, "cls": class_name, "dur": event.get("durationMs", 0), "rid": run_id})
        conn.execute("""
            MATCH (b:MonitorBlock {id: $bid}), (m:Method {id: $mid})
            MERGE (b)-[:BLOCKED_IN]->(m)
        """, {"bid": monitor_id, "mid": stack[-1]})

    print(
        f"Ingested {len(allocation_events)} allocations, {len(retained_events)} retained-object "
        f"samples, {len(monitor_events)} monitor blocks into KùzuDB."
    )


def ingest_to_kuzu(db_path: str, run_id: str, test_name: str, edge_counts: dict, method_counts: dict, total_samples: int, other_jfr_events: Dict[str, list] = None):
    """Ingests aggregated call edges and node metadata into KùzuDB."""
    if not HAS_KUZU:
        print("Error: 'kuzu' Python package is required. Install via: pip install kuzu")
        sys.exit(1)

    print(f"Opening KùzuDB database at '{db_path}'...")
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    init_kuzu_schema(conn)

    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    test_id = f"{run_id}_{test_name}"

    # 1. Insert Run & Test
    conn.execute("MERGE (r:Run {id: $id, timestamp: $ts})", {"id": run_id, "ts": timestamp_str})
    conn.execute("MERGE (t:Test {id: $id, name: $name})", {"id": test_id, "name": test_name})
    conn.execute("MATCH (r:Run {id: $rid}), (t:Test {id: $tid}) MERGE (r)-[:EXECUTED_TEST]->(t)", {"rid": run_id, "tid": test_id})

    # 2. Insert Methods
    for m_id, sample_cnt in method_counts.items():
        pkg, class_name, m_name = extract_class_and_method(m_id)
        conn.execute("""
            MERGE (m:Method {id: $id})
            ON CREATE SET m.pkg = $pkg, m.className = $cls, m.methodName = $mname, m.sampleCount = $cnt
        """, {"id": m_id, "pkg": pkg, "cls": class_name, "mname": m_name, "cnt": sample_cnt})

    # 3. Insert Call Edges
    inserted_edges = 0
    for (caller, callee), count in edge_counts.items():
        pct = round((count / max(1, total_samples)) * 100, 2)
        conn.execute("""
            MATCH (a:Method {id: $caller}), (b:Method {id: $callee})
            MERGE (a)-[r:CALLS {count: $cnt, percent: $pct, runId: $rid}]->(b)
        """, {"caller": caller, "callee": callee, "cnt": count, "pct": pct, "rid": run_id})
        inserted_edges += 1

    print(f"Successfully ingested {len(method_counts)} methods and {inserted_edges} call edges into KùzuDB!")

    # 4. Insert non-CPU JFR events (allocations/retained-objects/monitor-blocks), if any (spec plan/002).
    if other_jfr_events:
        ingest_jfr_events_to_kuzu(conn, run_id, other_jfr_events)


def main():
    parser = argparse.ArgumentParser(description="Ingest async-profiler collapsed stacks into KùzuDB (Embedded Graph DB)")
    parser.add_argument("--input", "-i", required=True, help="Path to collapsed stack file (.collapsed or .txt)")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KùzuDB database folder (default: ./profiler_graph.db)")
    parser.add_argument("--run-id", default="run_1", help="Unique ID for this profiling run (e.g. commit hash or build ID)")
    parser.add_argument("--test-name", default="api_benchmark", help="Name of the profiled API test")
    parser.add_argument("--dry-run", action="store_true", help="Parse and display summary without writing to KùzuDB")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)

    print(f"Parsing profile file: {args.input}...")
    edge_counts, method_counts, total_samples, other_jfr_events = parse_profile(args.input)
    print(f"Parsed {total_samples} total samples, {len(method_counts)} distinct methods, {len(edge_counts)} unique edges.")

    if args.dry_run:
        print("\n=== DRY RUN SUMMARY ===")
        print(f"Top Methods by Samples:")
        sorted_methods = sorted(method_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for m, count in sorted_methods:
            print(f"  [{count} samples] {m}")

        print(f"\nTop Call Edges:")
        sorted_edges = sorted(edge_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for (caller, callee), count in sorted_edges:
            print(f"  [{count} calls] {caller} -> {callee}")

        if other_jfr_events:
            print(f"\nOther JFR Event Types Extracted (Allocation/RetainedObject/MonitorBlock nodes on ingest):")
            for event_type, events in sorted(other_jfr_events.items()):
                print(f"  {event_type}: {len(events)} events")
        return

    ingest_to_kuzu(args.db_path, args.run_id, args.test_name, edge_counts, method_counts, total_samples, other_jfr_events)


if __name__ == "__main__":
    main()
