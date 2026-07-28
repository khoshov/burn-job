"""
Taxonomy Analyzers Package (T1 - T9) for graph-based performance anomaly detection.
"""

from burn_job.detectors.taxonomy.t1_redundant_ops import analyze_t1
from burn_job.detectors.taxonomy.t2_inefficient_algos import analyze_t2
from burn_job.detectors.taxonomy.t3_improper_func_usage import analyze_t3
from burn_job.detectors.taxonomy.t4_data_layout import analyze_t4
from burn_job.detectors.taxonomy.t5_redundant_checks import analyze_t5
from burn_job.detectors.taxonomy.t6_db_queries import analyze_t6
from burn_job.detectors.taxonomy.t7_memory_leak import analyze_t7
from burn_job.detectors.taxonomy.t8_memory_bloat import analyze_t8
from burn_job.detectors.taxonomy.t9_cpu_hotspots import analyze_t9

__all__ = [
    "analyze_t1", "analyze_t2", "analyze_t3", "analyze_t4", "analyze_t5",
    "analyze_t6", "analyze_t7", "analyze_t8", "analyze_t9",
]
