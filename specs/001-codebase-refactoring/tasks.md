# Tasks: Codebase Architecture & Structure Refactoring with Pytest Test Suite

**Input**: Design documents from `/specs/001-codebase-refactoring/`

**Prerequisites**: [plan.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/plan.md) (required), [spec.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/spec.md) (required for user stories), [research.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/research.md), [data-model.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/data-model.md), [contracts/](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/contracts/)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story using `pytest`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Exact file paths included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, domain sub-package directory structure, and `pytest` framework configuration.

- [X] T001 Create project domain directory structure in `src/burn_job/core`, `src/burn_job/domain`, `src/burn_job/detectors`, `src/burn_job/graph`, `src/burn_job/pipeline`, and `src/burn_job/cli`
- [X] T002 Update package discovery configuration in `pyproject.toml`
- [X] T003 [P] Create test directory hierarchy in `tests/unit/`, `tests/integration/`, and `tests/contract/`
- [X] T004 [P] Configure `pytest` and `pytest-cov` settings in `pyproject.toml` with coverage threshold flags

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and primitives that MUST be complete before user story domain models and logic are refactored.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Create `src/burn_job/core/__init__.py` exposing core package primitives
- [X] T006 [P] Create domain exception hierarchy in `src/burn_job/core/exceptions.py`
- [X] T007 [P] Create central configuration manager in `src/burn_job/core/config.py`
- [X] T008 [P] Create structured logging infrastructure in `src/burn_job/core/logging.py`
- [X] T009 [P] Implement core typing protocols (`DetectorProtocol`, `StoreProtocol`) in `src/burn_job/core/protocols.py`
- [X] T010 [P] Create pytest unit tests for `burn_job.core` in `tests/unit/test_core.py`

**Checkpoint**: Foundation ready — domain models and story implementation can now begin.

---

## Phase 3: User Story 1 - Developer Code Comprehension & Navigation (Priority: P1) 🎯 MVP

**Goal**: Establish domain-driven package layout, unified naming conventions, clean immutable domain entities (`Finding`, `Endpoint`, `Metric`, `Variant`, `PipelineContext`), and unit/integration `pytest` coverage.

**Independent Test**: Verified by running `pytest tests/unit/test_domain.py tests/unit/test_graph.py tests/integration/test_domain_context.py`.

### Implementation for User Story 1

- [X] T011 [P] [US1] Create `Finding`, `Severity`, `SourceLocation` DTOs in `src/burn_job/domain/finding.py`
- [X] T012 [P] [US1] Create `Endpoint` domain entity in `src/burn_job/domain/endpoint.py`
- [X] T013 [P] [US1] Create `Metric` and `MetricSource` DTOs in `src/burn_job/domain/metrics.py`
- [X] T014 [P] [US1] Create `Variant` optimization entity in `src/burn_job/domain/variant.py`
- [X] T015 [US1] Create immutable `PipelineContext` state container in `src/burn_job/domain/pipeline_context.py`
- [X] T016 [P] [US1] Create domain package exports in `src/burn_job/domain/__init__.py`
- [X] T017 [P] [US1] Refactor KùzuDB graph store wrapper into `src/burn_job/graph/store.py`
- [X] T018 [P] [US1] Refactor profile trace log ingestor into `src/burn_job/graph/ingest.py`
- [X] T019 [P] [US1] Create graph package exports in `src/burn_job/graph/__init__.py`
- [X] T020 [P] [US1] Create pytest unit tests for domain models in `tests/unit/test_domain.py`
- [X] T021 [P] [US1] Create pytest unit tests for graph store and ingestor in `tests/unit/test_graph.py`
- [X] T022 [US1] Refactor domain context integration test to native `pytest` in `tests/integration/test_domain_context.py`

**Checkpoint**: User Story 1 functional and independently testable with `pytest`.

---

## Phase 4: User Story 2 - Modular Component Isolation & Extensibility (Priority: P2)

**Goal**: Standardize defect detector contracts (`BaseDetector`, `RuleEngine`) to isolate static/dynamic taxonomy rules (T1-T9) behind abstract boundaries with `pytest` suite.

**Independent Test**: Verified by running `pytest tests/unit/test_detectors.py tests/contract/test_detector_protocol.py`.

### Implementation for User Story 2

- [X] T023 [P] [US2] Implement `BaseDetector` abstract base class in `src/burn_job/detectors/base.py`
- [X] T024 [P] [US2] Refactor AST and Bytecode static analyzers into `src/burn_job/detectors/static/`
- [X] T025 [P] [US2] Refactor taxonomy defect rules (T1-T9) into `src/burn_job/detectors/taxonomy/`
- [X] T026 [US2] Implement `RuleEngine` registry and orchestrator in `src/burn_job/detectors/rule_engine.py`
- [X] T027 [P] [US2] Create detector package exports in `src/burn_job/detectors/__init__.py`
- [X] T028 [P] [US2] Create pytest unit tests for RuleEngine and taxonomy detectors in `tests/unit/test_detectors.py`
- [X] T029 [US2] Refactor detector protocol contract test to native `pytest` in `tests/contract/test_detector_protocol.py`

**Checkpoint**: User Story 2 functional and independently testable with `pytest`.

---

## Phase 5: User Story 3 - Operational CLI & Pipeline Stability (Priority: P3)

**Goal**: Refactor execution pipeline orchestrator, scanner, loadtest harness, and CLI command parser with backward compatibility and `pytest` integration suite.

**Independent Test**: Verified by running `pytest tests/unit/test_pipeline.py tests/integration/test_cli_commands.py`.

### Implementation for User Story 3

- [X] T030 [P] [US3] Refactor target application scanner in `src/burn_job/pipeline/scanner.py`
- [X] T031 [P] [US3] Refactor loadtest harness in `src/burn_job/pipeline/loadtest.py`
- [X] T032 [P] [US3] Refactor scoring engine in `src/burn_job/pipeline/scorer.py`
- [X] T033 [US3] Refactor `AutonomousOrchestrator` cycle engine in `src/burn_job/pipeline/orchestrator.py`
- [X] T034 [P] [US3] Create pipeline package exports in `src/burn_job/pipeline/__init__.py`
- [X] T035 [US3] Refactor CLI parser and legacy argument deprecation handlers in `src/burn_job/cli.py`
- [X] T036 [P] [US3] Create pytest unit tests for pipeline components in `tests/unit/test_pipeline.py`
- [X] T037 [US3] Refactor CLI integration test to native `pytest` in `tests/integration/test_cli_commands.py`

**Checkpoint**: All user stories complete and functional with `pytest`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup legacy root files, update documentation, and run full `pytest --cov=burn_job` validation suite.

- [X] T038 [P] Deprecate legacy root files (`src/burn_job/config.py`, `src/burn_job/logging_config.py`) and update root exports in `src/burn_job/__init__.py`
- [X] T039 [P] Update repository `README.md` architecture section with new 6-package layout diagram
- [X] T040 Execute full `pytest --cov=burn_job` test suite and verify code coverage meets >= 90% target
- [X] T041 Expand `README.md` with detailed architecture diagram, 6 sub-package breakdown, dependency matrix, and pytest testing guide

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - Sequential priority order: US1 (P1) → US2 (P2) → US3 (P3)
- **Polish (Phase 6)**: Depends on completion of User Stories 1-3
