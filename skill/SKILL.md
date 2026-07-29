---
name: burn-job-performance-refactor
description: Skill for automated static & dynamic profiling analysis, taxonomy defect detection (T1-T9), graph-based dependency querying via KuzuDB, and LLM-guided performance refactoring for Java Spring Boot services.
---

# Burn Job Performance Refactoring Skill

This skill exposes autonomous performance profiling and refactoring capabilities to AI agents.

## Core Capabilities

1. **Static Analysis & Controller Discovery**: Scans Spring `@RestController` classes, extracts mapped HTTP routes, request/response models, and method signatures.
2. **Dynamic Trace Graphing**: Ingests `.collapsed` folded stack traces from `async-profiler` and JFR into an embedded KùzuDB graph database.
3. **Taxonomy Defect Detection (T1–T9)**:
   - **T1**: Redundant Operations & Repeated Computations
   - **T2**: Inefficient Algorithms (quadratic loops vs linear)
   - **T3**: Heavy Object/Entity Materialization
   - **T4**: Data Layout & Memory Overhead
   - **T5**: Dead Code & Redundant Checks
   - **T6**: Database Query Bottlenecks (N+1 queries, unbatched saves)
   - **T7**: Memory Leaks & Retained Collection Growth
   - **T8**: Excessive Heap Memory Allocation
   - **T9**: Hot Path CPU Bottlenecks
4. **LLM Self-Optimization Loop**: Generates candidate code refactorings, evaluates latency/RPS/GC scores, and ensures contracts and Maven compilation remain 100% green.
5. **Standardized Report Generation**: Exports structured `findings.json` matching the submission schema with empirical `evidence` (`X-Sql-Count`, `X-Elapsed-Ms`, JFR metrics).

## Usage via CLI

```bash
# Execute full optimization cycle
./run.sh run-cycle
```
