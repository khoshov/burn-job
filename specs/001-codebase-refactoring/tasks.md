# Tasks: Codebase Architecture & Structure Refactoring

**Input**: Design documents from `/specs/001-codebase-refactoring/`

**Prerequisites**: [plan.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/plan.md) (required), [spec.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/spec.md) (required for user stories), [research.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/research.md), [data-model.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/data-model.md), [contracts/](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/contracts/)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Exact file paths included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and domain sub-package directory structure

- [X] T001 Create project domain directory structure in `src/burn_job/core`, `src/burn_job/domain`, `src/burn_job/detectors`, `src/burn_job/graph`, `src/burn_job/pipeline`, and `src/burn_job/cli`
- [X] T002 Update package discovery configuration in `pyproject.toml`
- [X] T003 [P] Create test directory hierarchy in `tests/unit/`, `tests/integration/`, and `tests/contract/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and primitives that MUST be complete before user story domain models and logic are refactored

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Create `src/burn_job/core/__init__.py` exposing core package primitives
- [X] T005 [P] Create domain exception hierarchy in `src/burn_job/core/exceptions.py`
- [X] T006 [P] Create central configuration manager in `src/burn_job/core/config.py`
- [X] T007 [P] Create structured logging infrastructure in `src/burn_job/core/logging.py`
- [X] T008 [P] Implement core typing protocols (`DetectorProtocol`, `StoreProtocol`) in `src/burn_job/core/protocols.py`

**Checkpoint**: Foundation ready — domain models and story implementation can now begin.

---

## Phase 3: User Story 1 - Developer Code Comprehension & Navigation (Priority: P1) 🎯 MVP

**Goal**: Establish domain-driven package layout, unified naming conventions, and clean immutable domain entities (`Finding`, `Endpoint`, `Metric`, `Variant`, `PipelineContext`).

**Independent Test**: Can be verified by importing `burn_job.domain` and `burn_job.graph` and instantiating `PipelineContext` with zero circular import errors.

### Implementation for User Story 1

- [X] T009 [P] [US1] Create `Finding`, `Severity`, `SourceLocation` DTOs in `src/burn_job/domain/finding.py`
- [X] T010 [P] [US1] Create `Endpoint` domain entity in `src/burn_job/domain/endpoint.py`
- [X] T011 [P] [US1] Create `Metric` and `MetricSource` DTOs in `src/burn_job/domain/metrics.py`
- [X] T012 [P] [US1] Create `Variant` optimization entity in `src/burn_job/domain/variant.py`
- [X] T013 [US1] Create immutable `PipelineContext` state container in `src/burn_job/domain/pipeline_context.py`
- [X] T014 [P] [US1] Create domain package exports in `src/burn_job/domain/__init__.py`
- [X] T015 [P] [US1] Refactor KùzuDB graph store wrapper into `src/burn_job/graph/store.py`
- [X] T016 [P] [US1] Refactor profile trace log ingestor into `src/burn_job/graph/ingest.py`
- [X] T017 [P] [US1] Create graph package exports in `src/burn_job/graph/__init__.py`
- [X] T018 [US1] Add integration test for domain package imports and `PipelineContext` state flow in `tests/integration/test_domain_context.py`

**Checkpoint**: User Story 1 functional and independently testable (MVP complete).

---

## Phase 4: User Story 2 - Modular Component Isolation & Extensibility (Priority: P2)

**Goal**: Standardize defect detector contracts (`BaseDetector`, `RuleEngine`) to isolate static/dynamic taxonomy rules (T1-T9) behind abstract boundaries.

**Independent Test**: Can be verified by running contract test verifying all taxonomy detectors conform to `DetectorProtocol`.

### Implementation for User Story 2

- [X] T019 [P] [US2] Implement `BaseDetector` abstract base class in `src/burn_job/detectors/base.py`
- [X] T020 [P] [US2] Refactor AST and Bytecode static analyzers into `src/burn_job/detectors/static/`
- [X] T021 [P] [US2] Refactor taxonomy defect rules (T1-T9) into `src/burn_job/detectors/taxonomy/`
- [X] T022 [US2] Implement `RuleEngine` registry and orchestrator in `src/burn_job/detectors/rule_engine.py`
- [X] T023 [P] [US2] Create detector package exports in `src/burn_job/detectors/__init__.py`
- [X] T024 [US2] Add contract test verifying all taxonomy detectors implement `DetectorProtocol` in `tests/contract/test_detector_protocol.py`

**Checkpoint**: User Story 2 functional and independently testable.

---

## Phase 5: User Story 3 - Operational CLI & Pipeline Stability (Priority: P3)

**Goal**: Refactor execution pipeline orchestrator, scanner, loadtest harness, and CLI command parser with backward compatibility and deprecation notices.

**Independent Test**: Can be verified by executing full CLI analysis commands (`scan`, `ingest`, `run-cycle`) without runtime errors.

### Implementation for User Story 3

- [X] T025 [P] [US3] Refactor target application scanner in `src/burn_job/pipeline/scanner.py`
- [X] T026 [P] [US3] Refactor loadtest harness in `src/burn_job/pipeline/loadtest.py`
- [X] T027 [P] [US3] Refactor scoring engine in `src/burn_job/pipeline/scorer.py`
- [X] T028 [US3] Refactor `AutonomousOrchestrator` cycle engine in `src/burn_job/pipeline/orchestrator.py`
- [X] T029 [P] [US3] Create pipeline package exports in `src/burn_job/pipeline/__init__.py`
- [X] T030 [US3] Refactor CLI parser and legacy argument deprecation handlers in `src/burn_job/cli.py`
- [X] T031 [US3] Add end-to-end integration test for CLI subcommands in `tests/integration/test_cli_commands.py`

**Checkpoint**: All user stories complete and functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup legacy root files, update documentation, and run full validation suite.

- [X] T032 [P] Remove legacy root files (`src/burn_job/config.py`, `src/burn_job/logging_config.py`) and update root exports in `src/burn_job/__init__.py`
- [X] T033 [P] Update repository `README.md` architecture section with new 6-package layout diagram
- [X] T034 Execute quickstart validation suite per `specs/001-codebase-refactoring/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - Sequential priority order: US1 (P1) → US2 (P2) → US3 (P3)
- **Polish (Phase 6)**: Depends on completion of User Stories 1-3

### Parallel Opportunities

- **Setup**: `T003` can run in parallel with `T001` & `T002`.
- **Foundational**: `T004`, `T005`, `T006`, `T007`, `T008` can all run in parallel across separate files under `src/burn_job/core/`.
- **User Story 1**: DTO creation tasks (`T009`, `T010`, `T011`, `T012`), graph store refactoring (`T015`, `T016`), and package exports (`T014`, `T017`) can run in parallel.
- **User Story 2**: `T019`, `T020`, `T021`, `T023` can run in parallel.
- **User Story 3**: Pipeline modules (`T025`, `T026`, `T027`, `T029`) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Verify `burn_job.domain` & `burn_job.graph` integrity via `tests/integration/test_domain_context.py`

### Incremental Delivery

1. Setup + Foundational → Core infrastructure ready
2. Add User Story 1 → Test domain & graph packages → MVP delivered
3. Add User Story 2 → Test detector protocol compliance → Extensibility delivered
4. Add User Story 3 → Test CLI workflows → Full system operational
