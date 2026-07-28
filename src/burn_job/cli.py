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

from burn_job.core.config import REPO_ROOT, DEFAULT_DB_PATH, DEFAULT_PROFILE_PATH, DEFAULT_HOST
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
        os.path.join(REPO_ROOT, "java", "src", "main", "java"),
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
    db: str = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to KuzuDB database"),
    profile: str = typer.Option(DEFAULT_PROFILE_PATH, "--profile", help="Path to profile file"),
    host: str = typer.Option(DEFAULT_HOST, "--host", help="Target API host"),
    online: bool = typer.Option(False, "--online", help="Enable online LLM API calls"),
    model_path: Optional[str] = typer.Option(None, "--model-path", help="Path to local model file/directory (llama.cpp or vLLM)"),
    backend: BackendEnum = typer.Option(BackendEnum.auto, "--backend", help="LLM execution backend (auto, llama.cpp, vllm, openai)"),
):
    console.print(Panel.fit(
        "[bold cyan]Burn Job — Autonomous Optimization Cycle[/bold cyan]\n"
        f"Backend: [yellow]{backend.value}[/yellow] | Online: [magenta]{online}[/magenta]",
        title="[bold green]Starting Cycle[/bold green]"
    ))
    orchestrator = AutonomousOrchestrator(
        db_path=db,
        profile_path=profile,
        host=host,
        offline=not online,
        model_path=model_path,
        backend=backend.value,
    )
    res = orchestrator.run()
    if res.get("success"):
        console.print("\n[bold green][✓] Autonomous cycle finished successfully.[/bold green]")
    else:
        console.print("\n[bold yellow][!] Autonomous cycle finished with warnings.[/bold yellow]")


@app.command("version", help="Print CLI version.")
def version():
    console.print("[bold cyan]burn-job CLI[/bold cyan] version [green]0.1.0[/green]")


def main():
    app()


if __name__ == "__main__":
    main()
