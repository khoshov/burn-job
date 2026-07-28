"""Global Configuration & Environment Settings for Performance Optimization Pipeline."""

import os
from dataclasses import dataclass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

# Storage paths
DEFAULT_DB_PATH = os.environ.get("BURN_JOB_DB_PATH", os.path.join(REPO_ROOT, "profiler_graph.db"))
DEFAULT_PROFILE_PATH = os.environ.get("BURN_JOB_PROFILE_PATH", os.path.join(REPO_ROOT, "app_profiling_full.collapsed"))
RUN_LOG_PATH = os.environ.get("BURN_JOB_LOG_PATH", os.path.join(REPO_ROOT, "runlog", "agent_run.log"))
REPORTS_SANDBOX_DIR = os.path.join(REPO_ROOT, "reports", "sandbox")
FINDINGS_JSON_PATH = os.path.join(REPORTS_SANDBOX_DIR, "findings.json")

# Server / Load test settings
DEFAULT_HOST = os.environ.get("BURN_JOB_HOST", "http://localhost:8080")
DEFAULT_CONCURRENCY = int(os.environ.get("BURN_JOB_CONCURRENCY", "50"))
DEFAULT_DURATION_SEC = int(os.environ.get("BURN_JOB_DURATION_SEC", "5"))

# Scoring Function weights
WEIGHT_LATENCY_P95 = 0.6
WEIGHT_RPS = 0.3
WEIGHT_GC_ALLOC = 0.1

# LLM Agent settings
DEFAULT_MAX_ITERATIONS = int(os.environ.get("BURN_JOB_MAX_ITERATIONS", "3"))
DEFAULT_MODEL = os.environ.get("BURN_JOB_MODEL", "deepseek-coder")

@dataclass
class Config:
    """Central configuration container for pipeline operations."""
    repo_root: str = REPO_ROOT
    db_path: str = DEFAULT_DB_PATH
    profile_path: str = DEFAULT_PROFILE_PATH
    log_path: str = RUN_LOG_PATH
    host: str = DEFAULT_HOST
    concurrency: int = DEFAULT_CONCURRENCY
    duration_sec: int = DEFAULT_DURATION_SEC
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    model: str = DEFAULT_MODEL
