# Implementation Plan: Автоматизированный контур профилирования, анализа и авто-исправления производительности Java бэкенда

**Branch**: `001-automated-performance-optimization-pipeline` | **Date**: 2026-07-28 | **Spec**: [spec.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-automated-performance-optimization-pipeline/spec.md)

**Input**: Feature specification from `specs/001-automated-performance-optimization-pipeline/spec.md`

---

## Technical Context

- **Language/Version**: Java 21, Python 3.10+
- **Primary Dependencies**: Spring Boot 3.3.2, Hibernate ORM 6.x, Spring Data JPA, H2 / PostgreSQL, async-profiler (ap-loader)
- **Storage**: KùzuDB (`profiler_graph.db` / `variant_evaluation_graph.db`)
- **Testing**: JUnit 5, Spring Boot Test (`mvn test`), Python `unittest` / `api_loadtest_suite.py`
- **Target Platform**: macOS / Linux (Docker / Podman Compose)
- **Performance Goals**: Сокращение Latency p95 > 40%, Прирост RPS > 50%, время фазы анализа < 500 мс.

---

## Project Structure

```text
specs/001-automated-performance-optimization-pipeline/
├── spec.md              # Feature specification
└── plan.md              # Implementation plan (this file)

loadtest/
├── api_loadtest_suite.py   # API load test runner
└── run_loadtest.sh         # Shell script runner

skill/scripts/
├── generate_api_loadtests.py      # OpenAPI / @RestController generator
├── jfr_to_graph.py                 # Profiler & JFR to KùzuDB graph converter
├── static_pattern_detectors.py     # Taxonomy detectors (T1-T9)
├── llm_agent.py                    # LLM Refactoring Agent
├── benchmark_variants.py           # Multi-variant in-memory benchmarker
├── evaluate_variants_via_kuzu.py   # Winner scoring evaluator
└── run_full_autonomous_cycle.py    # End-to-end autonomous orchestrator

src/main/java/com/example/badhibernate/
├── controller/                     # REST controllers
├── repository/                     # Spring Data JPA repositories
└── service/                        # Suboptimal & Optimal services (N+1, InMemoryFilter, etc.)
```

---

## Implementation Steps & Milestones

1. **Phase 1: Dynamic Load Test Generation & Async-Profiler Integration**
   - AST parser for `@RestController` endpoints.
   - Triggering `ap-loader` (`POST /api/profiler/profile`) during load test execution.

2. **Phase 2: JFR to KùzuDB Graph Ingest & Taxonomy Analysis**
   - Conversion of `.collapsed` profiles into `Method` and `CALLS` graph structures.
   - Executing Cypher queries to highlight bottleneck methods.

3. **Phase 3: LLM Code Refactoring Engine**
   - Constructing LLM prompts with graph context & Java 21 source snippets.
   - Outputting optimized code structures.

4. **Phase 4: In-Memory Multi-Variant Benchmarking & Winner Evaluation**
   - Fast HTTP parameter variant switching (`?variant=v1`).
   - Scoring calculation: $0.6 \Delta\text{Latency}_{p95} + 0.3 \Delta\text{RPS} + 0.1 \Delta\text{GC}$.

5. **Phase 5: Final Code Application & Maven Test Gate**
   - Writing winner implementation into source files.
   - Automated `mvn test` execution for zero regression verification.
