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
    DEFAULT_N_CTX,
    DEFAULT_N_GPU_LAYERS,
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


@app.command("ingest", help="Ingest profiler stack traces (collapsed or JFR) into KuzuDB graph database.")
def ingest(
    profile: str = typer.Option(DEFAULT_PROFILE_PATH, "--profile", help="Path to collapsed or .jfr profile file"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to KuzuDB directory"),
):
    from burn_job.utils.jfr_convert import jfr_to_collapsed
    profile_path = profile
    if profile_path.endswith(".jfr"):
        console.print(f"[bold yellow][!][/bold yellow] Detected JFR file, converting to collapsed first...")
        try:
            profile_path = jfr_to_collapsed(profile_path)
            console.print(f"[bold green][✓][/bold green] Converted JFR to [yellow]{profile_path}[/yellow]")
        except Exception as e:
            console.print(f"[bold red][✗] JFR conversion failed:[/bold red] {e}")
            raise typer.Exit(code=1)
    console.print(f"[bold blue][*][/bold blue] Ingesting profile [green]{profile_path}[/green] into KuzuDB at [yellow]{db}[/yellow]...")
    store = KuzuGraphStore(db)
    success = store.ingest_profile(profile_path)
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
    apply: bool = typer.Option(False, "--apply", help="Apply code fixes automatically to target project"),
    online: bool = typer.Option(False, "--online", help="Enable online LLM API calls"),
    model_path: Optional[str] = typer.Option(None, "--model-path", help="Path to local model file/directory (llama.cpp or vLLM)"),
    backend: BackendEnum = typer.Option(BackendEnum.auto, "--backend", help="LLM execution backend (auto, llama.cpp, vllm, openai)"),
    server_port: Optional[int] = typer.Option(None, "--server-port", help="Connect to running llama.cpp server on port (overrides auto-detect)"),
    variant_llm: str = typer.Option("deepseek", "--variant-llm", help="LLM backend for variant code generation: local (llama.cpp) or deepseek"),
    max_workers: int = typer.Option(8, "--llm-workers", "--max-workers", help="Max parallel worker threads for external LLM API calls"),
    skip_benchmark: bool = typer.Option(False, "--skip-benchmark", "--no-benchmark", help="Skip live Spring Boot restart benchmarking and evaluate variants instantly via AST score"),
):
    mode_str = "[green]APPLY FIXES MODE[/green]" if apply else "[yellow]REPORT ONLY MODE (No code modified)[/yellow]"
    variant_str = f" | Variant LLM: [magenta]{variant_llm}[/magenta] | Workers: [cyan]{max_workers}[/cyan]"
    if skip_benchmark:
        variant_str += " | [yellow]Skip Benchmark Active[/yellow]"
    console.print(Panel.fit(
        "[bold cyan]Burn Job — Autonomous Optimization Cycle[/bold cyan]\n"
        f"Target Src: [green]{src}[/green] | Mode: {mode_str} | Backend: [yellow]{backend.value}[/yellow]{variant_str}",
        title="[bold green]Starting Cycle[/bold green]"
    ))
    orchestrator = AutonomousOrchestrator(
        src_dir=src,
        db_path=db,
        profile_path=profile,
        host=host,
        offline=not online,
        apply_fixes=apply,
        model_path=model_path,
        backend=backend.value,
        server_port=server_port,
        variant_llm=variant_llm,
        max_workers=max_workers,
        skip_benchmark=skip_benchmark,
    )
    res = orchestrator.run()
    findings_json = res.get("findings_json", os.path.join(REPO_ROOT, "reports", "sandbox", "findings.json"))
    detailed_md = res.get("detailed_md", os.path.join(REPO_ROOT, "reports", "sandbox", "detailed_report.md"))

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
            f"Findings Detected:  [bold yellow]{res.get('findings_count', 0)}[/bold yellow]\n"
            f"Files Modified:     [magenta]{res.get('modified_files', 0)}[/magenta]\n"
            f"JSON Report:        [bold green]{findings_json}[/bold green]\n"
            f"Markdown Report:    [bold cyan]{detailed_md}[/bold cyan]",
            title="[bold green]Report Summary[/bold green]"
        ))
    else:
        console.print(Panel.fit(
            f"[bold yellow]! Cycle Finished with Warnings[/bold yellow]\n"
            f"JSON Report:     [bold green]{findings_json}[/bold green]\n"
            f"Markdown Report: [bold cyan]{detailed_md}[/bold cyan]",
            title="[bold yellow]Report Summary[/bold yellow]"
        ))


@app.command("jfr2collapsed", help="Convert a JFR recording file to collapsed stack format.")
def jfr2collapsed_cmd(
    input: str = typer.Argument(..., help="Path to input .jfr file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output .collapsed file path (default: input name with .collapsed)"),
):
    from burn_job.utils.jfr_convert import jfr_to_collapsed
    if not os.path.isfile(input):
        console.print(f"[bold red][✗] File not found:[/bold red] {input}")
        raise typer.Exit(code=1)
    if not input.endswith(".jfr"):
        console.print(f"[bold yellow][!][/bold yellow] Input does not end with .jfr, proceeding anyway...")
    try:
        out = jfr_to_collapsed(input, output)
        size_kb = os.path.getsize(out) / 1024
        console.print(f"[bold green][✓][/bold green] Converted to [yellow]{out}[/yellow] ({size_kb:.1f} KB, {sum(1 for _ in open(out))} stacks)")
    except Exception as e:
        console.print(f"[bold red][✗] Conversion failed:[/bold red] {e}")
        raise typer.Exit(code=1)


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


@app.command("llm-server", help="Start persistent llama.cpp OpenAI-compatible server.")
def llm_server(
    port: int = typer.Option(8081, "--port", "-p", help="Server listening port"),
    host: str = typer.Option("localhost", "--host", help="Server bind address"),
    model_path: Optional[str] = typer.Option(None, "--model-path", help="Path to GGUF model file"),
    n_ctx: int = typer.Option(DEFAULT_N_CTX, "--n-ctx", help="Context window size"),
    n_gpu_layers: int = typer.Option(DEFAULT_N_GPU_LAYERS, "--n-gpu-layers", help="GPU layers to offload (-1 = all)"),
):
    from burn_job.refinement.agent import resolve_model_path

    resolved = resolve_model_path(model_path)
    if not resolved:
        console.print("[bold red][✗] No GGUF model found. Specify --model-path or set BURN_JOB_MODEL_PATH.[/bold red]")
        raise typer.Exit(code=1)

    console.print(Panel.fit(
        f"[bold green]Starting llama.cpp server[/bold green]\n"
        f"Model: [yellow]{resolved}[/yellow]\n"
        f"Host:  [cyan]{host}:{port}[/cyan]\n"
        f"n_ctx: [magenta]{n_ctx}[/magenta]  n_gpu_layers: [magenta]{n_gpu_layers}[/magenta]",
        title="[bold cyan]LLM Server[/bold cyan]"
    ))

    try:
        from llama_cpp.server.app import create_app
        from llama_cpp.server.settings import Settings
        import uvicorn

        settings = Settings(
            model=resolved,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
        )
        app_instance = create_app(settings=settings)
        console.print(f"[bold green][✓][/bold green] Server ready at [underline]http://{host}:{port}/v1[/underline]")
        console.print("  Use: [bold]burn-job run-cycle --backend openai --base-url http://localhost:{}/v1[/bold]".format(port))
        uvicorn.run(app_instance, host=host, port=port, log_level="info")
    except ImportError as e:
        console.print(f"[bold red][✗] Missing dependency: {e}[/bold red]")
        console.print("  Install: pip install llama-cpp-python[server]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red][✗] Server error: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("version", help="Print CLI version.")
def version():
    console.print("[bold cyan]burn-job CLI[/bold cyan] version [green]0.1.0[/green]")


def main():
    app()


if __name__ == "__main__":
    main()
