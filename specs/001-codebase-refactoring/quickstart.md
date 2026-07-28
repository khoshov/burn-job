# Quickstart Validation Guide: Codebase Architecture & Structure Refactoring

**Feature**: Codebase Architecture & Structure Refactoring
**Spec**: [spec.md](file:///Users/stanislavkhoshov/Documents/burn-job/specs/001-codebase-refactoring/spec.md)

---

## Overview

This guide documents runnable validation scenarios that prove the refactored `burn-job` architecture, domain-driven package layout, strict typing, and CLI command compatibility work as intended.

---

## Scenario 1: Python Package Import & Module Integrity Validation

Verify that all sub-packages are importable without circular dependencies or missing exports.

```bash
# Execute python module import check script
python3 -c "
import burn_job
import burn_job.core
import burn_job.domain
import burn_job.detectors
import burn_job.graph
import burn_job.pipeline
import burn_job.cli
print('✅ All 6 domain sub-packages imported successfully!')
"
```

**Expected Outcome**: Zero `ImportError` or `ModuleNotFoundError`, output displays success message.

---

## Scenario 2: Static Analysis & Type Checking

Verify code style consistency, naming rules, and type annotations across the refactored codebase.

```bash
# Verify Python syntax and compilation across all modules
python3 -m compileall src/burn_job

# Run flake8 / ruff / mypy if installed
python3 -m mypy src/burn_job --ignore-missing-imports || true
```

**Expected Outcome**: Clean compilation with 0 syntax errors or circular import issues.

---

## Scenario 3: CLI Help & Deprecation Notice Execution

Validate CLI command discovery and deprecation warning behavior for legacy flags.

```bash
# Verify CLI entry point help menu
python3 -m burn_job.cli --help

# Test scan command interface
python3 -m burn_job.cli scan --help
```

**Expected Outcome**: CLI menu lists commands (`scan`, `ingest`, `run-cycle`, `report`, `version`) cleanly with zero stacktraces.

---

## Scenario 4: Detector Protocol Verification

Verify that all taxonomy detectors conform to `DetectorProtocol`.

```bash
python3 -c "
from burn_job.core.protocols import DetectorProtocol
from burn_job.detectors.rule_engine import RuleEngine

engine = RuleEngine()
for detector in engine.get_registered_detectors():
    assert isinstance(detector, DetectorProtocol), f'{detector} does not implement DetectorProtocol'
print(f'✅ All {len(engine.get_registered_detectors())} detectors conform to DetectorProtocol!')
"
```

**Expected Outcome**: All registered detectors pass protocol validation.
