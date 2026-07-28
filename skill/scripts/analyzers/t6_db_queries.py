#!/usr/bin/env python3
"""
T6. Ошибки в запросах к базе данных (Database Query Errors)
Detects N+1 query problems, lack of JDBC batching (saves in loops), and connection pool starvation (HikariPool).
"""

import sys
import os
import argparse
import json

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False


def analyze_t6(conn) -> list:
    anomalies = []

    # 1. N+1 Queries Problem
    query_n_plus_one = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.methodName CONTAINS 'findBy' OR b.methodName CONTAINS 'getEmployees' OR b.className CONTAINS 'PersistentBag'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_n_plus_one)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 50:
            anomalies.append({
                "taxonomy_id": "T6",
                "category": "DATABASE_QUERIES",
                "type": "N_PLUS_ONE_QUERIES",
                "severity": "HIGH",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Method '{caller}' triggers lazy collection initialization or N+1 queries on '{callee}' ({count} samples). Requires JOIN FETCH."
            })

    # 2. Save In Loop / Lack of JDBC Batching
    query_unbatched_saves = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.methodName CONTAINS 'performSave' OR b.methodName CONTAINS 'save' OR b.className CONTAINS 'AbstractSaveEventListener'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_unbatched_saves)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 50:
            anomalies.append({
                "taxonomy_id": "T6",
                "category": "DATABASE_QUERIES",
                "type": "SAVE_IN_LOOP_UNBATCHED",
                "severity": "CRITICAL",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"Method '{caller}' invokes individual entity save operations in loops ({count} samples). Missing JDBC batching."
            })

    # 3. Connection Pool Starvation
    query_pool_starvation = """
        MATCH (a:Method)-[r:CALLS]->(b:Method)
        WHERE b.className CONTAINS 'HikariPool' OR b.methodName CONTAINS 'getConnection'
        RETURN a.className + '.' + a.methodName AS caller, b.className + '.' + b.methodName AS callee, r.count, r.percent
        ORDER BY r.count DESC
    """
    res = conn.execute(query_pool_starvation)
    while res.has_next():
        caller, callee, count, pct = res.get_next()
        if count > 30:
            anomalies.append({
                "taxonomy_id": "T6",
                "category": "DATABASE_QUERIES",
                "type": "CONNECTION_POOL_STARVATION",
                "severity": "HIGH",
                "caller": caller,
                "callee": callee,
                "sample_count": count,
                "percentage": pct,
                "description": f"High wait time acquiring JDBC connection in '{caller}' ({count} samples). HikariPool exhaustion risk."
            })

    return anomalies


def main():
    parser = argparse.ArgumentParser(description="T6 Analyzer: Database query errors")
    parser.add_argument("--db-path", default="./profiler_graph.db", help="Path to KùzuDB database folder")
    parser.add_argument("--json", action="store_true", help="Output findings as JSON")
    args = parser.parse_args()

    if not HAS_KUZU:
        print("Error: 'kuzu' Python package is required. Install via: pip install kuzu")
        sys.exit(1)

    if not os.path.exists(args.db_path):
        print(f"Error: KùzuDB database path '{args.db_path}' does not exist.")
        sys.exit(1)

    db = kuzu.Database(args.db_path)
    conn = kuzu.Connection(db)
    results = analyze_t6(conn)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== T6. DATABASE QUERY ERRORS REPORT ({len(results)} anomalies found) ===")
        for item in results:
            print(f"[{item['severity']}] {item['type']} in {item['caller']} -> {item['callee']} ({item['sample_count']} samples)")
            print(f"  Description: {item['description']}")


if __name__ == "__main__":
    main()
