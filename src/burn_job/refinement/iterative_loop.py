"""
Iterative Self-Optimization Loop Orchestrator.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from typing import Any, Optional, Tuple

from burn_job.detectors.complexity import analyze_complexity

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
PROMPTS_DIR = os.path.join(_THIS_DIR, "..", "resources", "prompts")

try:
    from jinja2 import Environment, FileSystemLoader
    _JINJA_ENV = Environment(loader=FileSystemLoader(PROMPTS_DIR))
except ImportError:
    _JINJA_ENV = None


def render_prompt(template_name: str, data: dict) -> str:
    if _JINJA_ENV:
        try:
            template = _JINJA_ENV.get_template(template_name)
            return template.render(data)
        except Exception:
            return json.dumps(data, indent=2)
    return json.dumps(data, indent=2)


def verify_compilation(file_path: str, repo_root: str = REPO_ROOT) -> bool:
    java_dir = os.path.join(repo_root, "java") if os.path.exists(os.path.join(repo_root, "java", "pom.xml")) else repo_root
    try:
        res = subprocess.run(
            ["mvn", "test-compile"],
            cwd=java_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
        return res.returncode == 0
    except Exception:
        return False


def score_candidate(code: str, complexity_res: dict) -> float:
    score = 100.0
    nesting = complexity_res.get("max_nesting_depth", 0)
    if nesting > 1:
        score -= 10.0 * (nesting - 1)
    issues = complexity_res.get("issues", [])
    for issue in issues:
        sev = issue.get("severity", "low")
        if sev == "high":
            score -= 15.0
        elif sev == "medium":
            score -= 5.0
    num_loops = complexity_res.get("num_loops", 0)
    if num_loops >= 3:
        score -= 5.0
    suggestions = complexity_res.get("suggestions", [])
    if suggestions:
        score -= 3.0 * len(suggestions)
    return max(score, 0.0)


def _extract_section_bounds(target_file: str, findings: list) -> Tuple[int, int]:
    """Determine the line range to send to the LLM based on findings."""
    with open(target_file, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    total = len(lines)
    lf = 1
    lt = total
    if findings:
        lf = max(1, (findings[0].get("line_from") or 1) - 3)
        lt = min(total, (findings[0].get("line_to") or total) + 3)

    from burn_job.detectors._shared import iter_method_bodies
    with open(target_file, "r", encoding="utf-8") as f:
        methods = iter_method_bodies(f.read())
    for name, body, body_start in methods:
        body_end = body_start + body.count("\n")
        if body_start <= lf <= body_end or body_start <= lt <= body_end:
            sig_start = max(body_start - 4, 1)
            lf = sig_start
            lt = min(total, body_end)
            break
    return lf, lt


def run_iterative_loop(target_file: str, max_steps: int = 3, findings: list = None,
                       run_log_path: str = None, verify_mvn: bool = True,
                       agent: Any = None) -> dict:
    logger = _SimpleLogger(run_log_path) if run_log_path else None

    if not os.path.exists(target_file):
        return {"success": False, "error": "target file not found"}

    with open(target_file, "r", encoding="utf-8") as f:
        original_code = f.read()
    original_lines = original_code.splitlines(keepends=False)

    sec_start, sec_end = _extract_section_bounds(target_file, findings or [])
    if logger:
        logger.log("INFO", f"Section bounds: lines {sec_start}-{sec_end} of {len(original_lines)}")

    consecutive_errors = 0
    step_log = []

    for step in range(max_steps):
        step_entry = {"step": step + 1, "action": "", "result": ""}

        current_section = "\n".join(original_lines[sec_start - 1:sec_end])
        complexity_result = analyze_complexity(current_section)

        prompt = render_prompt("generator_prompt.jinja2", {
            "code": current_section,
            "findings": findings or [],
            "complexity_analysis": complexity_result,
            "evaluator_feedback": step_log[-1].get("evaluator_feedback", "") if step_log else "",
        })

        new_section = None
        if agent and hasattr(agent, "call_llm") and agent.is_api_configured():
            try:
                llm_res = agent.call_llm(prompt)
                new_section = agent.extract_code_block(llm_res)
            except Exception as e:
                if logger:
                    logger.log("WARNING", f"LLM call in iterative loop failed: {e}")

        if not new_section or len(new_section.strip()) < 10:
            step_entry["result"] = "generated_code_too_short"
            step_log.append(step_entry)
            break

        patched_lines = original_lines[:sec_start - 1] + new_section.splitlines(keepends=False) + original_lines[sec_end:]
        patched_code = "\n".join(patched_lines)

        if verify_mvn:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(patched_code)
            verified = verify_compilation(target_file)
            if not verified:
                consecutive_errors += 1
                step_entry["result"] = f"compilation_failed ({consecutive_errors}/3)"
                if consecutive_errors >= 3:
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(original_code)
                    step_entry["result"] = "rolled_back_to_original"
                    step_log.append(step_entry)
                    break
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(original_code)
                continue
            consecutive_errors = 0
        else:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(patched_code)

        original_lines = patched_lines
        sec_end = sec_start + len(new_section.splitlines(keepends=False)) - 1
        evaluator_feedback = f"Step {step + 1}: code section updated successfully."
        if logger:
            logger.log("INFO", f"Step {step + 1}: {evaluator_feedback}")
        step_entry["evaluator_feedback"] = evaluator_feedback
        step_entry["result"] = "success"
        step_log.append(step_entry)

    if logger:
        logger.log("INFO", f"Iterative loop completed after {len(step_log)} steps.")

    final_code = "\n".join(original_lines)
    return {
        "success": len([s for s in step_log if s["result"] == "success"]) > 0,
        "final_code": final_code,
        "steps": step_log,
        "score": score_candidate(final_code, analyze_complexity(final_code)),
    }


class _SimpleLogger:
    def __init__(self, log_path: str):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log(self, level: str, message: str):
        timestamp = datetime.datetime.now().isoformat()
        formatted = f"[{timestamp}] [{level.upper()}] {message}\n"
        print(formatted, end="", flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(formatted)


def main():
    parser = argparse.ArgumentParser(description="Iterative Self-Optimization Loop")
    parser.add_argument("--file", required=True, help="Target Java source file")
    parser.add_argument("--max-steps", type=int, default=3)
    parser.add_argument("--findings", help="Path to findings JSON")
    parser.add_argument("--no-verify", action="store_true", dest="no_verify")
    parser.add_argument("--run-log", help="Path to run log file")
    args = parser.parse_args()

    findings_list = []
    if args.findings:
        with open(args.findings) as f:
            findings_list = json.load(f)

    result = run_iterative_loop(
        target_file=args.file,
        max_steps=args.max_steps,
        findings=findings_list,
        run_log_path=args.run_log,
        verify_mvn=not args.no_verify,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
