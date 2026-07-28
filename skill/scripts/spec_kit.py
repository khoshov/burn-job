#!/usr/bin/env python3
"""
GitHub Spec Kit & Spec-Driven Development (SDD) Management Tool.

Provides CLI commands for managing, validating, and generating SDD specifications in plan/*.md,
tracking acceptance criteria progress, and creating GitHub PR descriptions from specs.
"""

import argparse
import datetime
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
PLAN_DIR = os.path.join(REPO_ROOT, "plan")

REQUIRED_SECTIONS = [
    "Problem",
    "Goal",
    "Non-goals",
    "Approach",
    "Files touched",
    "Acceptance criteria",
    "Dependencies",
]


def list_specs(plan_dir: str = PLAN_DIR) -> list:
    """Scans plan/*.md and summarizes all spec files and their acceptance criteria progress."""
    specs = []
    if not os.path.exists(plan_dir):
        return specs

    for file in sorted(os.listdir(plan_dir)):
        if not file.endswith(".md") or file == "README.md":
            continue

        filepath = os.path.join(plan_dir, file)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file

        criteria = re.findall(r"-\s*\[([ xX])\]\s*(.+)", content)
        total_ac = len(criteria)
        completed_ac = sum(1 for c in criteria if c[0].lower() == "x")
        progress_pct = (completed_ac / total_ac * 100) if total_ac > 0 else 0.0

        specs.append({
            "filename": file,
            "title": title,
            "total_ac": total_ac,
            "completed_ac": completed_ac,
            "progress_pct": round(progress_pct, 1),
            "status": "DONE" if total_ac > 0 and completed_ac == total_ac else ("IN_PROGRESS" if completed_ac > 0 else "PENDING"),
        })

    return specs


def validate_spec(spec_path: str) -> tuple[bool, list]:
    """Validates a markdown specification file against the SDD standard schema."""
    if not os.path.exists(spec_path):
        return False, [f"File not found: {spec_path}"]

    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []

    # Title check
    if not re.search(r"^#\s+(.+)$", content, re.MULTILINE):
        errors.append("Missing main H1 title ('# Title')")

    # Section checks
    for sec in REQUIRED_SECTIONS:
        if not re.search(rf"^##\s+{re.escape(sec)}\b", content, re.MULTILINE | re.IGNORECASE):
            errors.append(f"Missing required section '## {sec}'")

    # Acceptance criteria checkbox check
    ac_section = re.search(r"##\s+Acceptance criteria\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if ac_section:
        checkboxes = re.findall(r"-\s*\[([ xX])\]", ac_section.group(1))
        if not checkboxes:
            errors.append("Section '## Acceptance criteria' contains no valid '- [ ]' or '- [x]' checkboxes")

    return len(errors) == 0, errors


def create_spec(spec_number: str, slug: str, title: str, plan_dir: str = PLAN_DIR) -> str:
    """Creates a new standardized SDD specification file."""
    filename = f"{spec_number.zfill(3)}-{slug.lower().replace(' ', '-')}.md"
    filepath = os.path.join(plan_dir, filename)

    template = f"""# {spec_number.zfill(3)} — {title}

## Problem
Describe the problem or architectural gap being addressed.

## Goal
State the specific, measurable objective.

## Non-goals
Explicitly list what is NOT in scope for this specification.

## Approach
Detail the technical solution, algorithms, and component design.

```mermaid
graph TD
    A["Input Component"] --> B["Processing Engine"]
    B --> C["Output Artifact"]
```

## Files touched
- New: `skill/scripts/example.py`
- Modified: `plan/README.md`

## Acceptance criteria
- [ ] Feature implemented according to specification
- [ ] Unit / Integration tests pass cleanly
- [ ] Documentation updated

## Dependencies
List any precursor specs (e.g. Depends on [004](004-findings-json-generator.md)).
"""

    os.makedirs(plan_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(template)

    return filepath


def generate_github_pr(spec_path: str) -> str:
    """Generates a GitHub Pull Request description body from a spec file."""
    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Pull Request"

    prob_match = re.search(r"##\s+Problem\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    goal_match = re.search(r"##\s+Goal\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    ac_match = re.search(r"##\s+Acceptance criteria\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)

    problem = prob_match.group(1).strip() if prob_match else "N/A"
    goal = goal_match.group(1).strip() if goal_match else "N/A"
    ac = ac_match.group(1).strip() if ac_match else "N/A"

    pr_body = f"""## 🚀 PR Summary: {title}

### 🔍 Problem & Motivation
{problem}

### 🎯 Goal
{goal}

### ✅ Acceptance Criteria Checklist
{ac}

---
*Generated automatically by GitHub Spec Kit CLI (`skill/scripts/spec_kit.py`)*
"""
    return pr_body


def init_project(project_name: str, integration: str = "gemini") -> str:
    """Initializes a new Spec Kit SDD project structure with AI integration (Gemini/OpenAI/Claude/Qwen)."""
    target_dir = os.path.abspath(project_name)
    plan_dir = os.path.join(target_dir, "plan")
    integration_dir = os.path.join(target_dir, f".{integration}")

    os.makedirs(plan_dir, exist_ok=True)
    os.makedirs(integration_dir, exist_ok=True)

    # 1. specify.config.json
    config_path = os.path.join(target_dir, "specify.config.json")
    config_data = {
        "project_name": os.path.basename(target_dir),
        "integration": integration,
        "spec_dir": "plan",
        "version": "1.0.0",
        "created_at": datetime.datetime.now().isoformat(),
        "sdd_rules": {
            "required_sections": REQUIRED_SECTIONS,
            "acceptance_criteria_checkboxes": True,
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    # 2. Integration AI rules file (.gemini/spec_rules.md)
    ai_rules_path = os.path.join(integration_dir, "spec_rules.md")
    ai_rules_content = f"""# GitHub Spec Kit — {integration.upper()} Integration Rules

You are an AI assistant operating within a Spec-Driven Development (SDD) repository configured for **{integration.upper()}**.

## Core SDD Guidelines:
1. All major features, bugfixes, and refactorings MUST be specified in `plan/*.md` before implementation.
2. Each spec MUST contain the required sections: `Problem`, `Goal`, `Non-goals`, `Approach`, `Files touched`, `Acceptance criteria`, `Dependencies`.
3. Track progress by checking off `- [x]` items in `Acceptance criteria`.
4. Validate specs using `specify validate` or `python3 skill/scripts/spec_kit.py validate`.
"""
    with open(ai_rules_path, "w", encoding="utf-8") as f:
        f.write(ai_rules_content)

    # 3. plan/README.md
    plan_readme_path = os.path.join(plan_dir, "README.md")
    if not os.path.exists(plan_readme_path):
        plan_readme_content = f"""# Spec-Driven Development (SDD) Index — {os.path.basename(target_dir)}

This directory contains specifications for project features and refactorings.

## Specs Registry

| # | Spec File | Summary | Status |
|---|---|---|---|
"""
        with open(plan_readme_path, "w", encoding="utf-8") as f:
            f.write(plan_readme_content)

    return target_dir


def main():
    parser = argparse.ArgumentParser(description="GitHub Spec Kit CLI for Spec-Driven Development")
    subparsers = parser.add_subparsers(dest="command", help="Spec Kit Commands")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Initialize a new Spec Kit SDD project")
    init_parser.add_argument("project_name", help="Directory name or path for the project")
    init_parser.add_argument("--integration", default="gemini", choices=["gemini", "openai", "claude", "qwen"], help="AI provider integration (default: gemini)")

    # Command: list
    list_parser = subparsers.add_parser("list", help="List all specs and their completion progress")
    list_parser.add_argument("--json", action="store_true", help="Output list as JSON")

    # Command: validate
    val_parser = subparsers.add_parser("validate", help="Validate specification file(s) against SDD schema")
    val_parser.add_argument("file", nargs="?", help="Spec file path (or all if omitted)")

    # Command: new
    new_parser = subparsers.add_parser("new", help="Create a new specification file")
    new_parser.add_argument("number", help="Spec number (e.g. 018)")
    new_parser.add_argument("slug", help="Short slug name (e.g. my-feature)")
    new_parser.add_argument("--title", help="Full spec title")

    # Command: github-pr
    pr_parser = subparsers.add_parser("github-pr", help="Generate GitHub PR description body from a spec file")
    pr_parser.add_argument("file", help="Spec file path")

    args = parser.parse_args()

    if args.command == "init":
        target = init_project(args.project_name, args.integration)
        print(f"✨ Initialized GitHub Spec Kit project at: {target}")
        print(f"   Integration: {args.integration.upper()} (Config: {os.path.join(target, 'specify.config.json')})")
        print(f"   Spec directory: {os.path.join(target, 'plan')}")
        print(f"   AI rules file: {os.path.join(target, f'.{args.integration}', 'spec_rules.md')}")

    elif args.command == "list":
        specs = list_specs()
        if args.json:
            print(json.dumps(specs, indent=2))
        else:
            print(f"📋 GitHub Spec Kit — SDD Specifications Index ({len(specs)} specs found):")
            print("-" * 75)
            for s in specs:
                status_icon = "✅" if s["status"] == "DONE" else ("🟡" if s["status"] == "IN_PROGRESS" else "⚪")
                print(f"{status_icon} [{s['status']:<11}] {s['filename']:<35} ({s['completed_ac']}/{s['total_ac']} AC - {s['progress_pct']}%)")
            print("-" * 75)

    elif args.command == "validate":
        if args.file:
            files_to_check = [args.file]
        else:
            files_to_check = [os.path.join(PLAN_DIR, f) for f in sorted(os.listdir(PLAN_DIR)) if f.endswith(".md") and f != "README.md"]

        all_ok = True
        for filepath in files_to_check:
            ok, errors = validate_spec(filepath)
            rel = os.path.basename(filepath)
            if ok:
                print(f"  ✓ {rel}: Valid SDD Spec")
            else:
                all_ok = False
                print(f"  ❌ {rel}: Validation Errors:")
                for err in errors:
                    print(f"     - {err}")

        if not all_ok:
            sys.exit(1)

    elif args.command == "new":
        title = args.title or args.slug.replace("-", " ").title()
        path = create_spec(args.number, args.slug, title)
        print(f"✨ Created new SDD Specification: {path}")

    elif args.command == "github-pr":
        pr_body = generate_github_pr(args.file)
        print(pr_body)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
