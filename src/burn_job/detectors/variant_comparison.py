"""Variant generation, scoring, and winner selection per finding."""

import os
import re
from typing import Dict, List, Any, Optional

from burn_job.detectors._shared import REPO_ROOT, read_file
from burn_job.detectors.complexity import analyze_complexity
from burn_job.refinement.iterative_loop import score_candidate, verify_compilation


_STRATEGY_NAMES = {
    "T1": ["Batch Lookup & Map Indexing", "Hibernate Batch Insert (saveAll)", "Caffeine Cache & Shared Helpers"],
    "T2": ["HashMap Indexing O(N+M)", "HashSet O(1) Filtering", "SQL Level ORDER BY Sorting"],
    "T3": ["Interface Projection & COUNT Query", "Spring Data Slice & DTO Projection", "Pagination & WHERE Pushdown"],
    "T4": ["Primitive Unboxing & Specialized Collections", "StringBuilder with Capacity Hint", "Array Pool & ThreadLocal Buffer"],
    "T5": ["Guard Clause Consolidation", "Optional API Migration", "Dead Branch Pruning"],
    "T6": ["Spring Data @EntityGraph / JOIN FETCH", "Interface & Record Projections", "Native Batch Statement Insert"],
    "T7": ["Caffeine LRU Cache with maxSize", "WeakHashMap & SoftReference", "ThreadLocal try-finally Cleanup"],
    "T8": ["WHERE Clause Pushdown", "Pagination & Keyset Pagination", "Streaming Response & Projection"],
    "T9": ["Static Pre-compiled Pattern", "Lock-Free Concurrency (LongAdder)", "Hot Path Inlining & Math Optimization"],
}

_DEFAULT_NAMES = ["Declarative Spring Data Projection", "Upfront Bulk Query & Map Lookup", "Low-Overhead Primitive Structures"]


def _pick_strategy_names(tax_codes: List[str]) -> List[str]:
    for tc in tax_codes:
        if tc in _STRATEGY_NAMES:
            return _STRATEGY_NAMES[tc]
    return _DEFAULT_NAMES


def _score_from_complexity(code: str) -> float:
    return score_candidate(code, analyze_complexity(code))


def generate_and_evaluate_variants(
    finding: Dict[str, Any],
    original_code: str,
    target_file: str,
    agent: Optional[Any] = None,
    verify_compile: bool = False,
    variant_llm: str = "local",
) -> List[Dict[str, Any]]:
    tax_codes = finding.get("pdf_taxonomy", ["T1"])
    names = _pick_strategy_names(tax_codes)
    variants = []

    candidate_codes: Dict[str, str] = {}
    if agent and agent.is_api_configured():
        try:
            from burn_job.refinement.agent import SYSTEM_MULTI_VARIANT_PROMPT
            rel_file = os.path.relpath(target_file, REPO_ROOT)
            prompt = f"""Target File: {rel_file}
Taxonomy Codes: {tax_codes}
Mechanism: {finding.get('mechanism', '')}

Existing Code:
```java
{original_code}
```
Generate 3 distinct refactoring candidates per multi-variant instructions."""
            if variant_llm == "deepseek" and agent.api_key:
                deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
                resp = agent.call_llm_api(prompt, system_prompt=SYSTEM_MULTI_VARIANT_PROMPT, model=deepseek_model)
            else:
                resp = agent.call_llm(prompt, system_prompt=SYSTEM_MULTI_VARIANT_PROMPT)
            candidate_codes = agent.extract_multi_code_blocks(resp)
        except Exception as e:
            pass

    for i, name in enumerate(names):
        code = candidate_codes.get(f"v{i+1}", original_code)
        entry = {
            "strategy": name,
            "score_ast": None,
            "score": None,
            "compiles": None,
            "is_winner": False,
            "errors": [],
            "generated_code": code if code != original_code else None,
        }
        try:
            entry["score_ast"] = round(_score_from_complexity(code), 2)
        except Exception as e:
            entry["errors"].append(f"complexity_score_failed: {e}")

        if verify_compile and code != original_code:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(code)
            try:
                entry["compiles"] = verify_compilation(target_file)
            except Exception:
                entry["compiles"] = False
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(original_code)

        entry["score"] = entry["score_ast"] if entry["score_ast"] is not None else 0
        variants.append(entry)

    if variants:
        best = max(variants, key=lambda v: (v["score"] if v["score"] is not None else -1,
                                            1 if v["compiles"] is not False else 0))
        best["is_winner"] = True

    return variants


def attach_variant_comparisons(
    findings: List[Dict[str, Any]],
    agent: Optional[Any] = None,
    verify_compile: bool = False,
    variant_llm: str = "local",
) -> List[Dict[str, Any]]:
    enriched = []
    for f in findings:
        target_file = None
        rel_file = f.get("file", "")
        if rel_file:
            candidate = os.path.join(REPO_ROOT, rel_file)
            if os.path.exists(candidate):
                target_file = candidate

        original_code = None
        if target_file:
            try:
                original_code = read_file(target_file)
            except Exception:
                pass

        if original_code and target_file:
            variants = generate_and_evaluate_variants(
                f, original_code, target_file, agent=agent, verify_compile=verify_compile, variant_llm=variant_llm,
            )
        else:
            names = _pick_strategy_names(f.get("pdf_taxonomy", ["T1"]))
            variants = [{"strategy": n, "score": None, "score_ast": None, "compiles": None, "is_winner": i == 0, "errors": []}
                        for i, n in enumerate(names)]

        winner = next((v for v in variants if v.get("is_winner")), (variants[0] if variants else None))

        llm_model = getattr(agent, "model", None) if agent else None

        enriched.append({
            **f,
            "variants": variants,
            "winner": winner,
            "benchmark": None,
            "llm_model": llm_model if any(v.get("generated_code") for v in variants) else None,
        })

    return enriched
