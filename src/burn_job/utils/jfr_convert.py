"""JFR to collapsed stack format converter."""
import os
import re
import sys
import json
import subprocess
import tempfile
from collections import defaultdict
from typing import Dict, Tuple, Optional


def _find_jfr2collapsed_tool() -> Optional[str]:
    for name in ("jfr2collapsed", "asprof"):
        for path in os.environ.get("PATH", "").split(os.pathsep):
            full = os.path.join(path, name)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return full
    return None


def _find_java() -> Optional[str]:
    for name in ("java", "java.exe"):
        for path in os.environ.get("PATH", "").split(os.pathsep):
            full = os.path.join(path, name)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return full
    return None


def convert_via_asprof(jfr_path: str, collapsed_path: str) -> bool:
    tool = _find_jfr2collapsed_tool()
    if not tool:
        return False
    try:
        cmd = [tool, "jfr2collapsed", jfr_path] if tool.endswith("asprof") else [tool, jfr_path]
        with open(collapsed_path, "w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True, timeout=120)
        return os.path.getsize(collapsed_path) > 0
    except Exception:
        return False


def convert_via_jfr_print(jfr_path: str, collapsed_path: str) -> bool:
    java = _find_java()
    if not java:
        return False
    try:
        result = subprocess.run(
            [java, "jfr", "print", "--json", "--events", "ExecutionSample", jfr_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["jfr", "print", "--json", "--events", "ExecutionSample", jfr_path],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                return False
        data = json.loads(result.stdout)
        return _fold_json_events(data, collapsed_path)
    except Exception:
        return False


def _fold_json_events(data: dict, collapsed_path: str) -> bool:
    stacks: Dict[str, int] = defaultdict(int)
    raw_events = data.get("recording", {}).get("events", data)
    if isinstance(raw_events, list):
        for event in raw_events:
            stack = _extract_stack_from_event(event)
            if stack:
                stacks[stack] += 1
    if not stacks:
        return False
    with open(collapsed_path, "w") as f:
        for stack, count in sorted(stacks.items(), key=lambda x: -x[1]):
            f.write(f"{stack} {count}\n")
    return True


def _extract_stack_from_event(event: dict) -> Optional[str]:
    stack_trace = event.get("stackTrace", event.get("stacktrace"))
    if not stack_trace:
        return None
    frames = stack_trace.get("frames", [])
    if not frames:
        return None
    reversed_frames = []
    for frame in frames:
        method = frame.get("method", {})
        cls = method.get("class", {}).get("name", "")
        method_name = method.get("name", "")
        line = frame.get("lineNumber", "")
        if cls or method_name:
            name = f"{cls}.{method_name}" if cls else method_name
            if line:
                name = f"{name}:{line}"
            reversed_frames.append(name)
    if not reversed_frames:
        return None
    return ";".join(reversed(reversed_frames))


def convert_via_jcmd(jfr_path: str, collapsed_path: str) -> bool:
    java_home = os.environ.get("JAVA_HOME", "")
    jcmd = os.path.join(java_home, "bin", "jcmd") if java_home else "jcmd"
    try:
        subprocess.run(
            [jcmd, str(os.getpid()), "JFR.flush", f"name=convert"],
            capture_output=True, timeout=10
        )
    except Exception:
        pass
    tmpdir = tempfile.mkdtemp()
    try:
        text_path = os.path.join(tmpdir, "output.txt")
        result = subprocess.run(
            _jfr_tool_cmd() + ["print", "--events", "ExecutionSample", jfr_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            return False
        with open(text_path, "w") as f:
            f.write(result.stdout)
        return _fold_text_output(text_path, collapsed_path)
    finally:
        for f in os.listdir(tmpdir):
            try:
                os.remove(os.path.join(tmpdir, f))
            except Exception:
                pass
        try:
            os.rmdir(tmpdir)
        except Exception:
            pass


def _jfr_tool_cmd() -> list:
    java_home = os.environ.get("JAVA_HOME", "")
    if java_home:
        jfr = os.path.join(java_home, "bin", "jfr")
        if os.path.isfile(jfr):
            return [jfr]
    if sys.platform == "darwin" and java_home:
        alt = os.path.join(java_home, "..", "Home", "bin", "jfr")
        if os.path.isfile(alt):
            return [alt]
    return ["jfr"]


def _fold_text_output(text_path: str, collapsed_path: str) -> bool:
    stacks: Dict[str, int] = defaultdict(int)
    current_stack = []
    sampling = False
    with open(text_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("Event:") and "ExecutionSample" in stripped:
                if current_stack:
                    stacks[";".join(current_stack)] += 1
                    current_stack = []
                sampling = True
            elif stripped.startswith("Event:") or stripped.startswith("{"):
                if current_stack:
                    stacks[";".join(current_stack)] += 1
                    current_stack = []
                sampling = False
            elif sampling and stripped and not stripped.startswith(("---", "//", "/*")):
                current_stack.append(stripped)
    if current_stack:
        stacks[";".join(current_stack)] += 1
    if not stacks:
        return False
    with open(collapsed_path, "w") as f:
        for stack, count in sorted(stacks.items(), key=lambda x: -x[1]):
            f.write(f"{stack} {count}\n")
    return True


def jfr_to_collapsed(jfr_path: str, output_path: str = None) -> Optional[str]:
    if not os.path.isfile(jfr_path):
        raise FileNotFoundError(f"JFR file not found: {jfr_path}")
    if output_path is None:
        output_path = jfr_path.rsplit(".", 1)[0] + ".collapsed"
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    if convert_via_asprof(jfr_path, output_path):
        return output_path

    if convert_via_jfr_print(jfr_path, output_path):
        return output_path

    if convert_via_jcmd(jfr_path, output_path):
        return output_path

    raise RuntimeError(
        "Could not convert JFR to collapsed. Install async-profiler (https://github.com/async-profiler/async-profiler) "
        "which provides 'jfr2collapsed', or ensure Java 17+ with 'jfr' CLI tool is on PATH."
    )
