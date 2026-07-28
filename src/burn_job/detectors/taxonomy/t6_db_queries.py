#!/usr/bin/env python3
"""
T6. Database Queries (N+1, Save in Loop, etc.)
"""

import sys
import os

_SCRIPTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPTS_ROOT)

from burn_job.detectors import rule_engine

try:
    import kuzu
    HAS_KUZU = True
except ImportError:
    HAS_KUZU = False


def analyze_t6(conn) -> list:
    if not HAS_KUZU:
        return []
    return rule_engine.run(conn, "T6")
