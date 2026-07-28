"""Burn-Job Core Framework Package."""

__version__ = "0.1.0"
__author__ = "Google DeepMind Advanced Agentic Coding"

from burn_job import core, domain, detectors, graph, pipeline, cli

__all__ = [
    "__version__",
    "core",
    "domain",
    "detectors",
    "graph",
    "pipeline",
    "cli",
]
