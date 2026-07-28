"""
KuzuDB Embedded Graph Database Store & Ingestor Module.
"""

import os
import sys
import json
import subprocess
import datetime
from collections import defaultdict
from typing import Dict, Tuple, List, Any, Optional

from burn_job.config import DEFAULT_DB_PATH
from burn_job.logging_config import setup_logger

logger = setup_logger("GraphStore")

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False


class KuzuGraphStore:
    """Encapsulates connection management, schema initialization, and graph operations for KuzuDB."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db = None
        self.conn = None
        if HAS_KUZU:
            self._connect()

    def _connect(self):
        if not HAS_KUZU:
            logger.warning("KuzuDB python package not installed.")
            return
        os.makedirs(self.db_path, exist_ok=True)
        self.db = kuzu.Database(self.db_path)
        self.conn = kuzu.Connection(self.db)
        self.init_schema()

    def execute(self, query: str, params: dict = None) -> Any:
        if not self.conn:
            logger.warning("No active KuzuDB connection.")
            return None
        try:
            if params:
                return self.conn.execute(query, params)
            return self.conn.execute(query)
        except Exception as e:
            logger.error(f"Cypher execution failed: {e}\nQuery: {query}")
            return None

    def init_schema(self):
        schema_statements = [
            "CREATE NODE TABLE IF NOT EXISTS Method(name STRING, class_name STRING, short_name STRING, is_synthetic BOOLEAN, PRIMARY KEY (name));",
            "CREATE NODE TABLE IF NOT EXISTS SqlStatement(hash STRING, query STRING, query_type STRING, PRIMARY KEY (hash));",
            "CREATE NODE TABLE IF NOT EXISTS Issue(id STRING, taxonomy_id STRING, category STRING, type STRING, title STRING, file STRING, line INT64, PRIMARY KEY (id));",
            "CREATE REL TABLE IF NOT EXISTS CALLS(FROM Method TO Method, count INT64);",
            "CREATE REL TABLE IF NOT EXISTS EXECUTES(FROM Method TO SqlStatement, count INT64);",
            "CREATE REL TABLE IF NOT EXISTS HAS_DEFECT(FROM Method TO Issue, severity STRING);",
        ]
        for stmt in schema_statements:
            self.execute(stmt)

    def ingest_profile(self, profile_path: str, run_id: str = "run_1") -> bool:
        if not os.path.exists(profile_path):
            logger.error(f"Profile path does not exist: {profile_path}")
            return False

        edge_counts, method_counts, total_samples = self._parse_collapsed(profile_path)
        logger.info(f"Parsed profile {profile_path}: {len(method_counts)} methods, {len(edge_counts)} call edges ({total_samples} samples).")

        if not HAS_KUZU or not self.conn:
            return True

        for m_name, count in method_counts.items():
            parts = m_name.rsplit(".", 1)
            class_name = parts[0] if len(parts) > 1 else ""
            short_name = parts[1] if len(parts) > 1 else m_name
            cypher = (
                f"MERGE (m:Method {{name: '{m_name}'}}) "
                f"ON CREATE SET m.class_name = '{class_name}', m.short_name = '{short_name}', m.is_synthetic = false;"
            )
            self.execute(cypher)

        for (caller, callee), weight in edge_counts.items():
            cypher = (
                f"MATCH (a:Method {{name: '{caller}'}}), (b:Method {{name: '{callee}'}}) "
                f"CREATE (a)-[:CALLS {{count: {weight}}}]->(b);"
            )
            self.execute(cypher)

        return True

    @staticmethod
    def _parse_collapsed(file_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], int]:
        edge_counts = defaultdict(int)
        method_counts = defaultdict(int)
        total_samples = 0

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.rsplit(" ", 1)
                if len(parts) != 2:
                    continue
                frames_str, count_str = parts[0], parts[1]
                try:
                    count = int(count_str)
                except ValueError:
                    continue

                total_samples += count
                frames = [fr.strip() for fr in frames_str.split(";") if fr.strip()]
                for fr in frames:
                    method_counts[fr] += count
                for i in range(len(frames) - 1):
                    caller, callee = frames[i], frames[i + 1]
                    edge_counts[(caller, callee)] += count

        return edge_counts, method_counts, total_samples
