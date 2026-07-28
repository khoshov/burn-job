"""Pytest integration test for CLI subcommands."""

import os
import subprocess
import sys

def _run_cli(args):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run([sys.executable, "-m", "burn_job.cli"] + args, capture_output=True, text=True, env=env)

def test_cli_help():
    res = _run_cli(["--help"])
    assert res.returncode == 0
    assert "scan" in res.stdout
    assert "ingest" in res.stdout
    assert "run-cycle" in res.stdout

def test_cli_version():
    res = _run_cli(["version"])
    assert res.returncode == 0
    assert "0.1.0" in res.stdout

def test_cli_scan():
    res = _run_cli(["scan", "--help"])
    assert res.returncode == 0
    assert "--src" in res.stdout
