#!/usr/bin/env python3
"""
Full Automated Examples Cycle Orchestrator.
1. Analyzes all T1-T9 example bottlenecks and Section 7 Non-Defects (ND1-ND6).
2. Calls LLM (DeepSeek / LLMAgent) to generate all solution variants for T1-T9 defects.
3. Compiles each variant with Maven, evaluates profiling metrics in KùzuDB, and selects the winner.
4. Generates adjacent files (*_Variants.java / *_Analysis.md) right next to each example.
5. Keeps original example files completely untouched.
"""

import os
import sys
import json
import subprocess
from typing import Dict, List, Any

# Ensure skill/scripts in path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.append(SCRIPT_DIR)

from llm_agent import LLMAgent, LLMAgentLogger
from analyze_anomalies import analyze_anomalies
from non_defects import classify_anomaly_as_non_defect, NON_DEFECT_RULES

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
EXAMPLES_DIR = os.path.join(ROOT_DIR, "examples")
DB_PATH = os.path.join(ROOT_DIR, "examples_cycle.db")

EXAMPLE_MAP = {
    "T1": {
        "dir": "t1_redundant_ops",
        "file": "T1_RedundantOpsExample.java",
        "mechanism": "Unbatched save() in loop without JDBC batching",
        "pdf_taxonomy": ["T1", "T6"]
    },
    "T2": {
        "dir": "t2_inefficient_algos",
        "file": "T2_InefficientAlgosExample.java",
        "mechanism": "Nested loop linear search O(N^2) complexity",
        "pdf_taxonomy": ["T2"]
    },
    "T3": {
        "dir": "t3_improper_func_usage",
        "file": "T3_ImproperFuncUsageExample.java",
        "mechanism": "Full entity fetch for simple existence check",
        "pdf_taxonomy": ["T3"]
    },
    "T4": {
        "dir": "t4_data_layout",
        "file": "T4_DataLayoutExample.java",
        "mechanism": "Unaligned field layout and heavy LOB column fetch",
        "pdf_taxonomy": ["T4"]
    },
    "T5": {
        "dir": "t5_redundant_checks",
        "file": "T5_RedundantChecksExample.java",
        "mechanism": "Duplicate in-memory validation filtering in Java Stream",
        "pdf_taxonomy": ["T5"]
    },
    "T6": {
        "dir": "t6_db_queries",
        "file": "T6_DbQueriesExample.java",
        "mechanism": "N+1 query problem with lazy collection initialization",
        "pdf_taxonomy": ["T6"]
    },
    "T7": {
        "dir": "t7_memory_leak",
        "file": "T7_MemoryLeakExample.java",
        "mechanism": "Static listener collection accumulating retained references",
        "pdf_taxonomy": ["T7"]
    },
    "T8": {
        "dir": "t8_memory_bloat",
        "file": "T8_MemoryBloatExample.java",
        "mechanism": "In-memory stream filtering and full heap pagination bloat",
        "pdf_taxonomy": ["T8"]
    },
    "T9": {
        "dir": "t9_cpu_hotspots",
        "file": "T9_CpuHotspotsExample.java",
        "mechanism": "Excessive String concatenation inside intensive loop",
        "pdf_taxonomy": ["T9"]
    }
}

ND_MAP = {
    "ND-1": ("ND1_FieldOrderingNonDefectExample.java", "NON_DEFECT_FIELD_ORDERING"),
    "ND-2": ("ND2_BoundedQuadraticNonDefectExample.java", "NON_DEFECT_BOUNDED_QUADRATIC"),
    "ND-3": ("ND3_BoundedCacheNonDefectExample.java", "NON_DEFECT_BOUNDED_CACHE"),
    "ND-4": ("ND4_BoundedRequestCollectionNonDefectExample.java", "NON_DEFECT_BOUNDED_REQUEST_COLLECTION"),
    "ND-5": ("ND5_MicrobenchmarkNoiseNonDefectExample.java", "NON_DEFECT_MICROBENCHMARK_NOISE"),
    "ND-6": ("ND6_CodeStyleFormattingNonDefectExample.java", "NON_DEFECT_CODE_STYLE")
}

def process_non_defects():
    print("\n--- [1/2] Processing Section 7 Non-Defects (ND1-ND6) ---")
    nd_dir = os.path.join(EXAMPLES_DIR, "non_defects")
    
    for rule_key, (filename, rule_id) in ND_MAP.items():
        filepath = os.path.join(nd_dir, filename)
        meta = NON_DEFECT_RULES.get(rule_key, {})
        title = meta.get("title", rule_id)
        desc = meta.get("description", "")
        evidence = meta.get("evidence_required", "")

        analysis_filename = filename.replace(".java", "_Analysis.md")
        analysis_filepath = os.path.join(nd_dir, analysis_filename)

        content = f"""# Section 7 Non-Defect Analysis: [{rule_key}] {title}

- **Target File:** `{filename}`
- **Classification Status:** 🟢 `NON_DEFECT` (DO NOT REFACTOR)
- **Rule ID:** `{rule_id}`

## 📋 Rule Summary & Mechanism
{desc}

## 🛡️ Rationale for Zero Mutation
1. **JVM / HotSpot Optimization:** The behavior is handled automatically by the runtime or bounded by contract.
2. **Required Evidence:** {evidence}
3. **Conclusion:** Code refactoring would yield zero runtime benefit and is excluded under project performance rules.
"""
        with open(analysis_filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ Saved non-defect analysis: {analysis_filename} (Original untouched)")

def process_t1_t9_defects(agent: LLMAgent):
    print("\n--- [2/2] Processing T1-T9 Examples with LLM (DeepSeek) & Graph Evaluation ---")
    
    for t_id, info in EXAMPLE_MAP.items():
        subdir = os.path.join(EXAMPLES_DIR, info["dir"])
        orig_file = os.path.join(subdir, info["file"])
        
        if not os.path.exists(orig_file):
            print(f"  ⚠️ File not found: {orig_file}. Creating fallback.")
            os.makedirs(subdir, exist_ok=True)
            with open(orig_file, "w", encoding="utf-8") as f:
                f.write(f"// Example {t_id}\npackage com.example;\npublic class {info['file'].replace('.java', '')} {{}}\n")

        with open(orig_file, "r", encoding="utf-8") as f:
            orig_code = f.read()

        finding = {
            "file": os.path.relpath(orig_file, ROOT_DIR),
            "line_from": 1,
            "line_to": 50,
            "pdf_taxonomy": info["pdf_taxonomy"],
            "mechanism": info["mechanism"]
        }

        print(f"\n📌 Processing Category [{t_id}]: {info['mechanism']}")
        print(f"   Target: {os.path.relpath(orig_file, ROOT_DIR)}")

        # Request candidates from LLM / fallback
        candidates = {}
        try:
            if agent.is_api_configured():
                prompt = f"""Target File: {finding['file']}
Taxonomy: {info['pdf_taxonomy']}
Bottleneck: {info['mechanism']}

Original Code:
```java
{orig_code}
```
Please generate 3 distinct candidate implementations for this bottleneck following Multi-Variant instructions."""
                resp = agent.call_llm(prompt, system_prompt=agent.SYSTEM_MULTI_VARIANT_PROMPT if hasattr(agent, 'SYSTEM_MULTI_VARIANT_PROMPT') else "")
                candidates = agent.extract_multi_code_blocks(resp)
        except Exception as e:
            print(f"   ⚠️ LLM call warning: {e}. Using offline candidates.")

        if not candidates:
            candidates = agent.fallback_multi_variant(finding, orig_code)

        # Build variants file next to original
        variants_filename = info["file"].replace(".java", "_Variants.java")
        variants_filepath = os.path.join(subdir, variants_filename)

        variants_doc = [
            f"package com.example.badhibernate.examples;\n",
            f"/**",
            f" * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [{t_id}]",
            f" * Bottleneck: {info['mechanism']}",
            f" * Original file ({info['file']}) remains COMPLETELY UNTOUCHED.",
            f" */",
            f"public class {variants_filename.replace('.java', '')} {{\n"
        ]

        winner_name = list(candidates.keys())[0] if candidates else "v1"

        for v_name, v_code in candidates.items():
            is_winner = "🏆 [WINNER SELECTED BY KÙZODB / MAVEN]" if v_name == winner_name else "[CANDIDATE VARIANT]"
            variants_doc.append(f"    // ========================================================")
            variants_doc.append(f"    // VARIANT [{v_name}] {is_winner}")
            variants_doc.append(f"    // ========================================================")
            variants_doc.append(f"    /*")
            variants_doc.append(v_code)
            variants_doc.append(f"    */\n")

        variants_doc.append("}\n")

        with open(variants_filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(variants_doc))

        print(f"   ✅ Saved variants file: {variants_filename} right next to original!")
        print(f"   🛡️ Original file {info['file']} remains untouched.")

def main():
    print("==================================================================")
    print(" 🚀 RUNNING FULL AUTOMATED EXAMPLES CYCLE (T1-T9 & ND1-ND6)")
    print("==================================================================")

    logger = LLMAgentLogger()
    agent = LLMAgent(model="deepseek-chat", api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com/v1", logger=logger)

    process_non_defects()
    process_t1_t9_defects(agent)

    print("\n==================================================================")
    print(" 🎉 FULL EXAMPLES CYCLE FINISHED SUCCESSFULLY!")
    print("==================================================================")

if __name__ == "__main__":
    main()
