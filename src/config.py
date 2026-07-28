"""
Global Configuration & Environment Settings for Performance Optimization Pipeline.
"""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# Storage paths
SPEC_DIR = os.path.join(REPO_ROOT, "specs")
DEFAULT_DB_PATH = os.path.join(REPO_ROOT, "profiler_graph.db")
DEFAULT_PROFILE_PATH = os.path.join(REPO_ROOT, "app_profiling_full.collapsed")
RUN_LOG_PATH = os.path.join(REPO_ROOT, "runlog", "agent_run.log")
REPORTS_SANDBOX_DIR = os.path.join(REPO_ROOT, "reports", "sandbox")
FINDINGS_JSON_PATH = os.path.join(REPORTS_SANDBOX_DIR, "findings.json")

# Server / Load test settings
DEFAULT_HOST = "http://localhost:8080"
DEFAULT_CONCURRENCY = 50
DEFAULT_DURATION_SEC = 5

# Scoring Function weights
WEIGHT_LATENCY_P95 = 0.6
WEIGHT_RPS = 0.3
WEIGHT_GC_ALLOC = 0.1

# LLM Agent settings
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_MODEL = "deepseek-coder"
