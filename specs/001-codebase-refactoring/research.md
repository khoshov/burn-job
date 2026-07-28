# Research & Architectural Decisions: Codebase Architecture & Structure Refactoring

**Feature**: Codebase Architecture & Structure Refactoring
**Spec**: [spec.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/spec.md)

---

## 1. Domain-Driven Package Layout & Module Structure

### Decision
Partition `src/burn_job` into 6 cleanly separated, single-responsibility domain sub-packages:

1. `burn_job.core`: Shared configuration (`config.py`), logging (`logging.py`), exception hierarchy (`exceptions.py`), and base protocols (`protocols.py`).
2. `burn_job.domain`: Immutable domain models and data transfer objects (`finding.py`, `metrics.py`, `endpoint.py`, `variant.py`, `pipeline_context.py`).
3. `burn_job.detectors`: Static & dynamic performance defect detectors (taxonomy rules T1-T9, AST parser, byte-code analysis, rule engine orchestration).
4. `burn_job.graph`: Embedded KùzuDB graph database store, schema management, trace ingestors, and query wrappers (`store.py`, `ingest.py`).
5. `burn_job.pipeline`: Execution cycle orchestration, scanner, load-testing harness, refinement agent, scoring, and report builder.
6. `burn_job.cli`: Command line interface, argument parsing, command dispatching, and legacy compatibility adapters.

### Rationale
- Removes root-level file clutter (`config.py` and `logging_config.py` in root package).
- Establishes a strict acyclic dependency flow: `cli` → `pipeline` → `detectors` & `graph` → `domain` → `core`.
- Isolates graph storage details from detection logic and report generation.

### Alternatives Considered
- *Flat package structure*: Single package with all modules side-by-side. Rejected due to poor scalability and high risk of circular imports as additional detectors and storage drivers are introduced.
- *Micro-kernel plugin architecture*: Dynamic runtime plugin loader using entry points. Rejected as overly complex for current scope; hybrid protocol interfaces provide sufficient flexibility.

---

## 2. Interface Contracts & Protocol Design

### Decision
Use `typing.Protocol` (structural subtyping) for public extension boundaries (`BaseDetector`, `GraphStoreProtocol`, `ReportBuilderProtocol`) combined with `abc.ABC` where shared default implementation behavior is required.

### Rationale
- `typing.Protocol` allows static type checking (mypy/pyright) without requiring strict inheritance hierarchies.
- Enables simple mock injection during unit testing.
- Allows third-party or custom detectors to implement the required interface implicitly.

### Alternatives Considered
- *Strict ABC inheritance only*: Requires all custom detectors to inherit from a concrete `ABC` class. Rejected to reduce coupling and allow structural duck-typing.

---

## 3. Data Transfer Objects & Immutable State Boundaries

### Decision
Use standard `dataclasses.dataclass(frozen=True)` (or `pydantic` where runtime validation is required) for domain models (`Finding`, `Metric`, `Endpoint`, `Variant`) and `PipelineContext`.

### Rationale
- Enforces immutability for findings passed through detection and refinement pipelines.
- Eliminates silent side-effects caused by mutating state across pipeline stages.
- Provides built-in structural representation (`__repr__`), equality (`__eq__`), and JSON serialization helpers.

### Alternatives Considered
- *Raw Python dictionaries*: Dicts pass untyped data across functions, leading to runtime `KeyError` exceptions and weak IDE autocompletion. Rejected.

---

## 4. Naming Conventions & Code Style Standardization

### Decision
Enforce strict PEP 8 naming standards supplemented by domain-specific naming rules:
- Modules / Files: Lowercase with underscores (`snake_case`), e.g., `rule_engine.py`, `pipeline_context.py`.
- Classes: PascalCase with explicit intent suffixes (`Finding`, `RuleEngine`, `KuzuGraphStore`, `AsyncProfilerIngestor`).
- Interfaces / Protocols: Suffix with `Protocol` or prefix with `Base` (`DetectorProtocol`, `BaseDetector`, `StoreProtocol`).
- Methods / Functions: Verb-first `snake_case` (`detect_defects()`, `ingest_trace()`, `build_report()`).
- Variables / Constants: Explicit names; UPPER_CASE for constants (`DEFAULT_GRAPH_PATH`, `MAX_REFINEMENT_CYCLES`).

### Rationale
- Eliminates ambiguous or abbreviated names (e.g., `t1_redundant_ops.py` will be renamed/aliased to `t1_redundant_operations.py`).
- Readability is prioritized for maintainers and new contributors.

---

## 5. CLI Backward Compatibility & Deprecation Strategy

### Decision
Implement argument parsing using `argparse` with custom action hooks that emit `DeprecationWarning` logs when legacy flags or positional syntax are invoked, mapping them seamlessly to new command handlers.

### Rationale
- Fulfills `FR-006` requirement for preserving existing script compatibility without blocking CLI modernization.
