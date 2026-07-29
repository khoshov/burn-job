"""Variant generation, scoring, and winner selection per finding."""

import os
import re
import concurrent.futures
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

# Phase 2 Optimization: In-memory Candidate Cache
_CANDIDATE_CACHE: Dict[str, Dict[str, str]] = {}


def _pick_strategy_names(tax_codes: List[str]) -> List[str]:
    for tc in tax_codes:
        if tc in _STRATEGY_NAMES:
            return _STRATEGY_NAMES[tc]
    return _DEFAULT_NAMES


def _score_from_complexity(code: str) -> float:
    return score_candidate(code, analyze_complexity(code))


def _quick_syntax_check(code: str) -> bool:
    """Fast in-memory Java syntax pre-validation to avoid expensive disk/mvn execution."""
    if not code or len(code.strip()) < 15:
        return False
    braces = 0
    parens = 0
    for char in code:
        if char == '{':
            braces += 1
        elif char == '}':
            braces -= 1
        elif char == '(':
            parens += 1
        elif char == ')':
            parens -= 1
        if braces < 0 or parens < 0:
            return False
    if braces != 0 or parens != 0:
        return False
    if not any(k in code for k in ("class ", "interface ", "record ", "void ", "return", "import ")):
        return False
    return True


def _make_cache_key(finding: Dict[str, Any], target_file: str, original_code: str) -> str:
    tax = tuple(sorted(finding.get("pdf_taxonomy", ["T1"])))
    mech = finding.get("mechanism", "")
    return f"{target_file}:{tax}:{mech}:{hash(original_code)}"


def fetch_candidate_codes_from_llm(
    finding: Dict[str, Any],
    original_code: str,
    target_file: str,
    agent: Optional[Any] = None,
    variant_llm: str = "local",
) -> Dict[str, str]:
    if not (agent and agent.is_api_configured()):
        return {}

    cache_key = _make_cache_key(finding, target_file, original_code)
    if cache_key in _CANDIDATE_CACHE:
        return _CANDIDATE_CACHE[cache_key]

    try:
        from burn_job.refinement.agent import SYSTEM_MULTI_VARIANT_PROMPT
        tax_codes = finding.get("pdf_taxonomy", ["T1"])
        rel_file = os.path.relpath(target_file, REPO_ROOT)
        prompt = f"""Target File: {rel_file}
Taxonomy Codes: {tax_codes}
Mechanism: {finding.get('mechanism', '')}

Existing Code:
```java
{original_code}
```
Generate EXACTLY 3 distinct refactoring candidate implementations. Label each variant with [VARIANT_1], [VARIANT_2], and [VARIANT_3]."""
        if variant_llm == "deepseek" and agent.api_key:
            deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
            resp = agent.call_llm_api(prompt, system_prompt=SYSTEM_MULTI_VARIANT_PROMPT, model=deepseek_model)
        else:
            resp = agent.call_llm(prompt, system_prompt=SYSTEM_MULTI_VARIANT_PROMPT)
        blocks = agent.extract_multi_code_blocks(resp)
        _CANDIDATE_CACHE[cache_key] = blocks
        return blocks
    except Exception:
        return {}


def generate_and_evaluate_variants(
    finding: Dict[str, Any],
    original_code: str,
    target_file: str,
    agent: Optional[Any] = None,
    verify_compile: bool = False,
    variant_llm: str = "local",
    prefetched_candidates: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    tax_codes = finding.get("pdf_taxonomy", ["T1"])
    names = _pick_strategy_names(tax_codes)
    variants = []

    if prefetched_candidates is not None:
        candidate_codes = prefetched_candidates
    else:
        candidate_codes = fetch_candidate_codes_from_llm(finding, original_code, target_file, agent=agent, variant_llm=variant_llm)

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
            if not _quick_syntax_check(code):
                entry["compiles"] = False
                entry["errors"].append("fast_syntax_precheck_failed")
            else:
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
    max_workers: Optional[int] = None,
) -> List[Dict[str, Any]]:
    prepared_items = []
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

        prepared_items.append((f, target_file, original_code))

    candidates_by_index: Dict[int, Dict[str, str]] = {}
    if agent and agent.is_api_configured() and prepared_items:
        concurrency = max_workers or int(os.getenv("DEEPSEEK_CONCURRENCY", os.getenv("LLM_MAX_WORKERS", "8")))
        workers = max(1, min(concurrency, len(prepared_items)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {
                executor.submit(fetch_candidate_codes_from_llm, f, orig_code, t_file, agent, variant_llm): idx
                for idx, (f, t_file, orig_code) in enumerate(prepared_items)
                if orig_code and t_file
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    candidates_by_index[idx] = future.result()
                except Exception:
                    candidates_by_index[idx] = {}

    enriched = []
    for idx, (f, target_file, original_code) in enumerate(prepared_items):
        if original_code and target_file:
            candidates = candidates_by_index.get(idx)
            variants = generate_and_evaluate_variants(
                f, original_code, target_file, agent=agent, verify_compile=verify_compile, variant_llm=variant_llm, prefetched_candidates=candidates
            )
        else:
            names = _pick_strategy_names(f.get("pdf_taxonomy", ["T1"]))
            variants = [{"strategy": n, "score": None, "score_ast": None, "compiles": None, "is_winner": i == 0, "errors": []}
                        for i, n in enumerate(names)]

        winner = next((v for v in variants if v.get("is_winner")), (variants[0] if variants else None))

        llm_model = getattr(agent, "model", None) if agent else None
        orig_score = None
        if original_code:
            try:
                orig_score = round(_score_from_complexity(original_code), 2)
            except Exception:
                pass

        enriched.append({
            **f,
            "original_score": orig_score,
            "variants": variants,
            "winner": winner,
            "benchmark": None,
            "llm_model": llm_model if any(v.get("generated_code") for v in variants) else None,
        })

    return enriched
