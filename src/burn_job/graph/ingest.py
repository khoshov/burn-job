"""
Profiler Call Graph Ingestor for KuzuDB Wrapper.
"""

import sys
import os
import argparse

from burn_job.graph.store import KuzuGraphStore


def parse_profile(profile_path: str):
    edge_counts, method_counts, total_samples = KuzuGraphStore._parse_collapsed(profile_path)
    return edge_counts, method_counts, total_samples, {}


def ingest_to_kuzu(db_path: str, run_id: str, test_name: str, edge_counts, method_counts, total_samples, other_jfr_events=None):
    store = KuzuGraphStore(db_path)
    for m_name in method_counts.keys():
        parts = m_name.rsplit(".", 1)
        class_name = parts[0] if len(parts) > 1 else ""
        short_name = parts[1] if len(parts) > 1 else m_name
        cypher = f"MERGE (m:Method {{name: '{m_name}'}}) ON CREATE SET m.class_name = '{class_name}', m.short_name = '{short_name}', m.is_synthetic = false;"
        store.execute(cypher)
    for (caller, callee), weight in edge_counts.items():
        cypher = f"MATCH (a:Method {{name: '{caller}'}}), (b:Method {{name: '{callee}'}}) CREATE (a)-[:CALLS {{count: {weight}}}]->(b);"
        store.execute(cypher)


def parse_collapsed_stack(file_path: str) -> dict:
    edge_counts, method_counts, total_samples = KuzuGraphStore._parse_collapsed(file_path)
    return method_counts


def convert_jfr_if_needed(file_path: str) -> dict:
    return parse_collapsed_stack(file_path)


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))


def main():
    parser = argparse.ArgumentParser(description="Ingest JFR or Collapsed Stack Traces into KuzuDB")
    parser.add_argument("--input", "-i", required=True, help="Path to profile file")
    parser.add_argument("--db-path", "--db", default=os.path.join(REPO_ROOT, "profiler_graph.db"), help="KuzuDB directory")
    args = parser.parse_args()

    store = KuzuGraphStore(args.db_path)
    store.ingest_profile(args.input)
    print(f"Successfully ingested '{args.input}' into KuzuDB graph at '{args.db_path}'.")


if __name__ == "__main__":
    main()
