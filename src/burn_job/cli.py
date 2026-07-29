"""Unified Typer (Click-powered) CLI Entrypoint for Performance Optimization Pipeline."""

import os
import sys
import warnings
from enum import Enum
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from burn_job.core.config import (
    REPO_ROOT,
    DEFAULT_SRC_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_PROFILE_PATH,
    DEFAULT_HOST,
)
from burn_job.core.logging import setup_logger
from burn_job.pipeline.scanner import ControllerScanner
from burn_job.graph.store import KuzuGraphStore
from burn_job.pipeline.orchestrator import AutonomousOrchestrator

logger = setup_logger("CLI")
console = Console()

app = typer.Typer(
    name="burn-job",
    help="Performance Optimization Pipeline & Codebase Refactoring Engine CLI",
    add_completion=False,
    rich_markup_mode="rich",
)

class BackendEnum(str, Enum):
    auto = "auto"
    llama_cpp = "llama.cpp"
    vllm = "vllm"
    openai = "openai"


@app.command("scan", help="Scan Java Spring REST controllers for endpoints.")
def scan(
    src: str = typer.Option(
        DEFAULT_SRC_DIR,
        "--src",
        help="Path to Java source directory",
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        help="[Deprecated] Alias for --src",
    ),
):
    if target:
        warnings.warn("The '--target' flag is deprecated for 'scan'; use '--src' instead.", DeprecationWarning)
        src = target

    endpoints = ControllerScanner.scan_directory(src)
    table = Table(title=f"Scanned REST Endpoints ({len(endpoints)})", show_header=True, header_style="bold magenta")
    table.add_column("HTTP Method", style="cyan", width=12)
    table.add_column("Path", style="green")
    table.add_column("Controller & Method", style="yellow")

    for ep in endpoints:
        table.add_row(ep.http_method, ep.path, f"{ep.controller_class}#{ep.method_name}")

    console.print(table)


@app.command("ingest", help="Ingest profiler stack traces into KuzuDB graph database.")
def ingest(
    profile: str = typer.Option(DEFAULT_PROFILE_PATH, "--profile", help="Path to collapsed profile file"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to KuzuDB directory"),
):
    console.print(f"[bold blue][*][/bold blue] Ingesting profile [green]{profile}[/green] into KuzuDB at [yellow]{db}[/yellow]...")
    store = KuzuGraphStore(db)
    success = store.ingest_profile(profile)
    if success:
        console.print("[bold green][✓] Profile ingested successfully into KuzuDB.[/bold green]")
    else:
        console.print("[bold red][✗] Profile ingestion failed.[/bold red]")
        raise typer.Exit(code=1)


@app.command("run-cycle", help="Run full 8-step autonomous performance optimization cycle.")
def run_cycle(
    src: str = typer.Option(DEFAULT_SRC_DIR, "--src", help="Path to Java source code directory"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to KuzuDB database"),
    profile: str = typer.Option(DEFAULT_PROFILE_PATH, "--profile", help="Path to profile file"),
    host: str = typer.Option(DEFAULT_HOST, "--host", help="Target API host"),
    online: bool = typer.Option(False, "--online", help="Enable online LLM API calls"),
    model_path: Optional[str] = typer.Option(None, "--model-path", help="Path to local model file/directory (llama.cpp or vLLM)"),
    backend: BackendEnum = typer.Option(BackendEnum.auto, "--backend", help="LLM execution backend (auto, llama.cpp, vllm, openai)"),
):
    console.print(Panel.fit(
        "[bold cyan]Burn Job — Autonomous Optimization Cycle[/bold cyan]\n"
        f"Target Src: [green]{src}[/green] | Backend: [yellow]{backend.value}[/yellow] | Online: [magenta]{online}[/magenta]",
        title="[bold green]Starting Cycle[/bold green]"
    ))
    orchestrator = AutonomousOrchestrator(
        src_dir=src,
        db_path=db,
        profile_path=profile,
        host=host,
        offline=not online,
        model_path=model_path,
        backend=backend.value,
    )
    res = orchestrator.run()
    findings_json = os.path.join(REPO_ROOT, "reports", "sandbox", "findings.json")

    endpoints_list = res.get("endpoints", [])
    if endpoints_list:
        table = Table(title=f"Executed Test Endpoints ({len(endpoints_list)})", show_header=True, header_style="bold magenta")
        table.add_column("HTTP Method", style="cyan", width=12)
        table.add_column("Path", style="green")
        table.add_column("Controller & Method Handler", style="yellow")

        for ep in endpoints_list:
            table.add_row(ep.get("method", "GET"), ep.get("path", "/"), ep.get("handler", ""))
        console.print("\n", table)

    if res.get("success"):
        console.print(Panel.fit(
            f"[bold green]✓ Cycle Completed Successfully![/bold green]\n"
            f"Endpoints Profiled: [cyan]{res.get('endpoints_count', 0)}[/cyan]\n"
            f"Findings Detected:  [yellow]{res.get('findings_count', 0)}[/yellow]\n"
            f"Report Generated:   [bold green]{findings_json}[/bold green]",
            title="[bold green]Report Summary[/bold green]"
        ))
    else:
        console.print(Panel.fit(
            f"[bold yellow]! Cycle Finished with Warnings[/bold yellow]\n"
            f"Report Generated: [bold green]{findings_json}[/bold green]",
            title="[bold yellow]Report Summary[/bold yellow]"
        ))


@app.command("profile", help="Generate a JFR profile from a running Java application.")
def profile(
    pid: Optional[str] = typer.Option(None, "--pid", "-p", help="Java process ID (auto-detected if omitted)"),
    duration: int = typer.Option(15, "--duration", "-d", help="Recording duration in seconds"),
    output: str = typer.Option("./app_profiling.jfr", "--output", "-o", help="Output path for .jfr file"),
):
    import subprocess
    import time

    target_pid = pid
    if not target_pid:
        try:
            res = subprocess.run(["jcmd", "-l"], capture_output=True, text=True, timeout=5)
            for line in res.stdout.splitlines():
                if "burn_job" in line or "jcmd" in line:
                    continue
                parts = line.split()
                if len(parts) > 0 and parts[0].isdigit():
                    target_pid = parts[0]
                    break
        except Exception:
            pass

    if not target_pid:
        console.print("[bold red][✗] No running Java process detected.[/bold red] Please specify --pid explicitly.")
        raise typer.Exit(code=1)

    recording_name = f"burn_job_jfr_{int(time.time())}"
    console.print(Panel.fit(
        f"Target PID:  [cyan]{target_pid}[/cyan]\n"
        f"Duration:    [magenta]{duration}s[/magenta]\n"
        f"Output File: [yellow]{output}[/yellow]",
        title="[bold green]Starting JFR Profiling[/bold green]"
    ))

    try:
        start_res = subprocess.run(
            ["jcmd", target_pid, "JFR.start", f"name={recording_name}", "settings=profile"],
            capture_output=True, text=True, timeout=10
        )
        if start_res.returncode != 0:
            console.print(f"[bold red][✗] JFR.start failed:[/bold red] {start_res.stderr.strip()}")
            raise typer.Exit(code=1)

        with console.status(f"[bold green]Recording JFR profile for {duration} seconds...[/bold green]"):
            time.sleep(duration)

        os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
        stop_res = subprocess.run(
            ["jcmd", target_pid, "JFR.stop", f"name={recording_name}", f"filename={os.path.abspath(output)}"],
            capture_output=True, text=True, timeout=10
        )

        if os.path.exists(output) and os.path.getsize(output) > 0:
            size_mb = os.path.getsize(output) / (1024 * 1024)
            console.print(f"[bold green][✓] JFR profile saved successfully:[/bold green] [yellow]{output}[/yellow] ({size_mb:.2f} MB)")
        else:
            console.print(f"[bold red][✗] JFR.stop did not generate file at {output}.[/bold red]")
            raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red][✗] JFR profiling error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("version", help="Print CLI version.")
def version():
    console.print("[bold cyan]burn-job CLI[/bold cyan] version [green]0.1.0[/green]")


def main():
    app()


if __name__ == "__main__":
    main()
