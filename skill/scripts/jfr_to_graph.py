#!/usr/bin/env python3
"""
Profiler Call Graph Ingestor for KùzuDB (The Embedded "SQLite of Graph DBs").
Parses async-profiler collapsed stack traces or JFR exports and loads call trees into KùzuDB.
"""

import sys
import os
import argparse
import datetime
from collections import defaultdict
from typing import Dict, Tuple, List

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False


def convert_jfr_if_needed(file_path: str) -> str:
    """If file is .jfr, automatically converts it to temporary .collapsed stack file."""
    if not file_path.lower().endswith(".jfr"):
        return file_path

    print(f"Detected binary JFR file: '{file_path}'. Converting to collapsed format via Python...")
    import subprocess
    import tempfile

    temp_collapsed = tempfile.NamedTemporaryFile(suffix=".collapsed", delete=False)
    temp_collapsed.close()

    # Try conversion via ap-loader Converter JAR if available in target/
    jar_path = os.path.join(os.path.dirname(__file__), "..", "target", "bad-hibernate-demo-0.0.1-SNAPSHOT.jar")
    if os.path.exists(jar_path):
        cmd = ["java", "-cp", jar_path, "one.profiler.Converter", "jfr2flame", file_path, temp_collapsed.name]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"Successfully converted JFR to {temp_collapsed.name}")
                return temp_collapsed.name
        except Exception:
            pass

    # Fallback to JDK's built-in jfr tool
    jfr_bin = "jfr"
    for candidate in ["jfr", "/opt/homebrew/opt/openjdk/bin/jfr"]:
        try:
            res = subprocess.run([candidate, "version"], capture_output=True)
            if res.returncode == 0:
                jfr_bin = candidate
                break
        except Exception:
            continue

    print(f"Using JDK '{jfr_bin}' CLI tool to extract execution samples...")
    cmd = [jfr_bin, "print", "--events", "jdk.ExecutionSample,ExecutionSample", file_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            # Parse jfr print output lines
            frames = []
            with open(temp_collapsed.name, "w", encoding="utf-8") as out:
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if "method = " in line or "frame = " in line:
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            m = parts[1].strip().strip('"')
                            if m:
                                frames.append(m)
                    elif line.startswith("}") and frames:
                        out.write(";".join(reversed(frames)) + " 1\n")
                        frames = []
            return temp_collapsed.name
    except Exception as e:
        print(f"Warning: JFR conversion error: {e}")

    return file_path


def parse_collapsed_stack(file_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], int]:
    """
    Parses async-profiler collapsed format: frame1;frame2;frame3 sample_count
    Returns:
      - edge_counts: (caller, callee) -> count
      - method_counts: method -> self/total samples
      - total_samples: total samples in profile
    """
    actual_path = convert_jfr_if_needed(file_path)

    edge_counts = defaultdict(int)
    method_counts = defaultdict(int)
    total_samples = 0

    with open(actual_path, "r", encoding="utf-8") as f:
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

            # Build edges
            for i in range(len(frames) - 1):
                caller = frames[i]
                callee = frames[i + 1]
                edge_counts[(caller, callee)] += count

    if actual_path != file_path and os.path.exists(actual_path):
        try:
            os.remove(actual_path)
        except Exception:
            pass

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
        "CREATE REL TABLE IF NOT EXISTS CALLS(FROM Method TO Method, count INT64, percent DOUBLE, runId STRING)"
    ]
    for stmt in schemas:
        try:
            conn.execute(stmt)
        except Exception:
            pass


def ingest_to_kuzu(db_path: str, run_id: str, test_name: str, edge_counts: dict, method_counts: dict, total_samples: int):
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

    print(f"Parsing collapsed stack file: {args.input}...")
    edge_counts, method_counts, total_samples = parse_collapsed_stack(args.input)
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
        return

    ingest_to_kuzu(args.db_path, args.run_id, args.test_name, edge_counts, method_counts, total_samples)


if __name__ == "__main__":
    main()
