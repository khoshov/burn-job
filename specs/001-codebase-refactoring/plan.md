# Implementation Plan: Codebase Architecture & Structure Refactoring

**Branch**: `001-codebase-refactoring` | **Date**: 2026-07-29 | **Spec**: [spec.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/spec.md)

**Input**: Feature specification from `/specs/001-codebase-refactoring/spec.md`

## Summary

Complete structural refactoring of `burn-job` codebase into 6 domain-driven sub-packages (`core`, `domain`, `detectors`, `graph`, `pipeline`, `cli`). Enforces strict PEP 8 naming, immutable dataclasses for findings/context state, `typing.Protocol` for detector interfaces, and backward-compatible CLI command dispatching.

## Technical Context

**Language/Version**: Python >= 3.10

**Primary Dependencies**: `kuzu` (v0.3+ embedded graph DB), `jinja2` (v3.0+ LLM prompt templates)

**Storage**: KùzuDB embedded graph database (`store.py`, `ingest.py`)

**Testing**: `pytest` framework with `pytest-cov` (target >= 90% code coverage)

**Target Platform**: Linux / macOS cross-platform CLI & Orchestration Engine

**Project Type**: CLI & Python Library / Orchestrator Engine

**Performance Goals**: Zero runtime overhead added by domain abstractions; instant (<100ms) CLI command parsing and context initialization.

**Constraints**: Strict acyclic dependency flow (`cli` → `pipeline` → `detectors` & `graph` → `domain` → `core`); 100% backward compatibility for existing CLI invocations with deprecation warnings.

**Scale/Scope**: ~30 Python modules across 6 domain sub-packages.

## Constitution Check

*GATE: Passed before Phase 0 research. Re-checked post Phase 1 design.*

- **Principle I: Library-First**: PASS - Core domain, graph store, and detectors are decoupled as self-contained library packages (`burn_job.domain`, `burn_job.detectors`, `burn_job.graph`).
- **Principle II: CLI Interface**: PASS - CLI exposed via `burn_job.cli`, supporting stdin/stdout/stderr conventions and JSON/human outputs.
- **Principle III: Test-First**: PASS - Refactoring done incrementally with tests kept green at each step.
- **Principle IV: Integration Testing**: PASS - Quickstart scenarios validate inter-module contracts and CLI execution end-to-end.
- **Principle V: Observability & Simplicity**: PASS - Structured logging (`burn_job.core.logging`) preserved across all pipeline stages.

## Project Structure

### Documentation (this feature)

```text
specs/001-codebase-refactoring/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 architectural decisions
├── data-model.md        # Phase 1 domain entities & state flow
├── quickstart.md        # Phase 1 quickstart validation guide
├── contracts/           # Phase 1 interface contracts
│   ├── detector-protocol.md
│   └── cli-contract.json
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Target Source Code Layout

```text
src/burn_job/
├── __init__.py
├── core/                # System primitives, logging, protocols, exceptions
│   ├── __init__.py
│   ├── config.py        # Central configuration settings
│   ├── logging.py       # Structured logging setup
│   ├── exceptions.py    # Domain exception hierarchy
│   └── protocols.py     # Base typing.Protocol interfaces
├── domain/              # Immutable domain entities & DTOs
│   ├── __init__.py
│   ├── finding.py       # Finding, Severity, SourceLocation DTOs
│   ├── endpoint.py      # Endpoint & HTTP route models
│   ├── metrics.py       # Metric & MetricSource DTOs
│   ├── variant.py       # Optimization code Variant DTO
│   └── pipeline_context.py # Immutable pipeline state context
├── detectors/           # Static & dynamic defect detection engine
│   ├── __init__.py
│   ├── base.py          # BaseDetector abstract class
│   ├── rule_engine.py   # RuleEngine orchestrator & registry
│   ├── static/          # AST, byte-code, complexity analyzers
│   └── taxonomy/        # Rules T1-T9 defect detectors
├── graph/               # Embedded KuzuDB graph store & ingestors
│   ├── __init__.py
│   ├── store.py         # KuzuGraphStore wrapper
│   └── ingest.py        # JFR / async-profiler trace ingestor
├── pipeline/            # 8-step cycle execution pipeline
│   ├── __init__.py
│   ├── orchestrator.py  # AutonomousOrchestrator
│   ├── scanner.py       # Target repository controller scanner
│   ├── loadtest.py      # Load-testing harness
│   └── scorer.py       # Scoring & evaluation module
├── refinement/          # LLM refinement & code generation loop
│   ├── __init__.py
│   ├── agent.py         # LLM prompt agent
│   └── iterative_loop.py# Benchmark & verification loop
├── report/              # Performance report generator
│   ├── __init__.py
│   └── builder.py       # ReportBuilder engine
└── cli.py               # Main CLI entry point & compatibility parser

tests/
├── unit/                # Unit tests per domain sub-package
├── integration/         # Inter-module integration tests
└── contract/            # Interface & protocol verification tests
```

**Structure Decision**: Selected single-package Python layout (`src/burn_job`) partitioned into 6 domain-driven sub-packages with `tests/` directory at repository root.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *None* | All constitution principles satisfied without violations | N/A |
