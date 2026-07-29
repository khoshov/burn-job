"""Variant comparison — strategy names only, no fabricated scores or benchmarks."""

from typing import List, Dict, Any


_STRATEGIES = {
    "T1": [
        "Batch Lookup & Map Indexing",
        "Hibernate Batch Insert (saveAll)",
        "Caffeine Cache & Shared Helpers",
    ],
    "T2": [
        "HashMap Indexing O(N+M)",
        "HashSet O(1) Filtering",
        "SQL Level ORDER BY Sorting",
    ],
    "T3": [
        "Interface Projection & COUNT Query",
        "Spring Data Slice & DTO Projection",
        "Pagination & WHERE Pushdown",
    ],
    "T4": [
        "Primitive Unboxing & Specialized Collections",
        "StringBuilder with Capacity Hint",
        "Array Pool & ThreadLocal Buffer",
    ],
    "T5": [
        "Guard Clause Consolidation",
        "Optional API Migration",
        "Dead Branch Pruning",
    ],
    "T6": [
        "Spring Data @EntityGraph / JOIN FETCH",
        "Interface & Record Projections",
        "Native Batch Statement Insert",
    ],
    "T7": [
        "Caffeine LRU Cache with maxSize",
        "WeakHashMap & SoftReference",
        "ThreadLocal try-finally Cleanup",
    ],
    "T8": [
        "WHERE Clause Pushdown",
        "Pagination & Keyset Pagination",
        "Streaming Response & Projection",
    ],
    "T9": [
        "Static Pre-compiled Pattern",
        "Lock-Free Concurrency (LongAdder)",
        "Hot Path Inlining & Math Optimization",
    ],
}

_DEFAULT_STRATEGIES = [
    "Declarative Spring Data Projection",
    "Upfront Bulk Query & Map Lookup",
    "Primitive Structures & Constant Pre-compilation",
]


def attach_variant_comparisons(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched = []
    for f in findings:
        tax_codes = f.get("pdf_taxonomy", ["T1"])
        names = None
        for tc in tax_codes:
            if tc in _STRATEGIES:
                names = _STRATEGIES[tc]
                break
        if names is None:
            names = _DEFAULT_STRATEGIES

        variants = []
        for i, name in enumerate(names):
            variants.append({
                "strategy": name,
                "score": None,
                "is_winner": i == 0,
                "benchmark": None,
            })

        enriched.append({
            **f,
            "variants": variants,
            "winner": variants[0] if variants else None,
            "benchmark": None,
        })

    return enriched
