"""
Detailed Findings Report Generator & Console Renderer.
Formats findings with location, description, impact, and actionable fix recommendations.
"""

import os
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

console = Console()

TAXONOMY_NAMES = {
    "T1": "Redundant Operations & Code Duplication",
    "T2": "Inefficient Algorithms & Data Structures",
    "T3": "Heavy Entity Materialization & Projections",
    "T4": "Data Layout & Object Overhead",
    "T5": "Dead Code & Redundant Checks",
    "T6": "Database Bottlenecks & N+1 Queries",
    "T7": "Memory Leaks & Unbounded Accumulation",
    "T8": "Heap Memory Overhead & Off-Query Filtering",
    "T9": "CPU Hotspots & Lock Contention",
}

def print_findings_summary(findings: List[Dict[str, Any]], checked_not_issue: List[Dict[str, Any]] = None):
    """Renders a rich, detailed console report for all detected findings."""
    if not findings:
        console.print(Panel("[bold green]✓ No performance defects or violations detected![/bold green]", title="Audit Summary"))
        return

    console.print(f"\n[bold red]=== DETECTED PERFORMANCE VIOLATIONS & DEFECTS ({len(findings)}) ===[/bold red]\n")

    for idx, f in enumerate(findings, 1):
        tax_codes = ", ".join(f.get("pdf_taxonomy", ["T1"]))
        tax_title = ", ".join([TAXONOMY_NAMES.get(code, code) for code in f.get("pdf_taxonomy", ["T1"])])
        file_path = f.get("file", "unknown")
        line_from = f.get("line_from", 1)
        mechanism = f.get("mechanism", "")
        impact = f.get("impact", "")
        fix = f.get("fix", "")

        panel_content = (
            f"[bold yellow]📍 Location:[/bold yellow] [green]{file_path}:{line_from}[/green]\n"
            f"[bold yellow]🏷️ Taxonomy:[/bold yellow] [cyan][{tax_codes}] {tax_title}[/cyan]\n"
            f"[bold yellow]⚠️ Impact:[/bold yellow] {impact}\n\n"
            f"[bold red]🔍 Description / Mechanism:[/bold red]\n{mechanism}\n\n"
            f"[bold green]💡 Recommended Fix (Как исправить):[/bold green]\n{fix}"
        )

        console.print(Panel(
            panel_content,
            title=f"[bold white]Finding #{idx} — [{tax_codes}] {file_path.split('/')[-1]}:{line_from}[/bold white]",
            border_style="red",
            expand=True
        ))

    if checked_not_issue:
        console.print(f"\n[dim]Checked & Verified Non-Defects ({len(checked_not_issue)}):[/dim]")
        for item in checked_not_issue:
            console.print(f" - [dim]{item.get('file')}: {item.get('why_not')}[/dim]")


def generate_markdown_report(findings: List[Dict[str, Any]], checked_not_issue: List[Dict[str, Any]], output_path: str):
    """Generates a detailed Markdown report file with all findings and fix instructions."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    lines = []
    lines.append("# 📊 Отчёт об аномалиях производительности и нарушениях\n")
    lines.append(f"> **Всего обнаружено нарушений:** `{len(findings)}`\n")
    lines.append("---\n")

    if not findings:
        lines.append("### ✅ Нарушений производительности не обнаружено.\n")
    else:
        lines.append("## 📋 Оглавление обнаруженных нарушений\n")
        lines.append("| № | Категория | Файл | Строка | Влияние |")
        lines.append("|---|---|---|---|---|")
        for idx, f in enumerate(findings, 1):
            tax_codes = ", ".join(f.get("pdf_taxonomy", ["T1"]))
            file_name = f.get("file", "").split("/")[-1]
            lines.append(f"| {idx} | `{tax_codes}` | [`{file_name}`](file://{os.path.abspath(f.get('file', ''))}#L{f.get('line_from', 1)}) | L{f.get('line_from', 1)} | {f.get('impact', '')} |")
        lines.append("\n---\n")

        lines.append("## 🔍 Подробное описание нарушений и рекомендации по исправлению\n")

        for idx, f in enumerate(findings, 1):
            tax_codes = ", ".join(f.get("pdf_taxonomy", ["T1"]))
            tax_title = ", ".join([TAXONOMY_NAMES.get(code, code) for code in f.get("pdf_taxonomy", ["T1"])])
            file_path = f.get("file", "")
            line_from = f.get("line_from", 1)
            mechanism = f.get("mechanism", "")
            impact = f.get("impact", "")
            fix = f.get("fix", "")

            lines.append(f"### Finding #{idx}: [{tax_codes}] {os.path.basename(file_path)} (Line {line_from})\n")
            lines.append(f"- **Категория:** `{tax_codes}` — {tax_title}")
            lines.append(f"- **Локация:** [`{file_path}`](file://{os.path.abspath(file_path)}#L{line_from})")
            lines.append(f"- **Серьёзность / Влияние:** {impact}\n")
            lines.append("#### 📝 Описание проблемы (Суть нарушения)")
            lines.append(f"```text\n{mechanism}\n```\n")
            lines.append("#### 🛠️ Как исправить (Рекомендация по оптимизации)")
            lines.append(f"> {fix}\n")
            lines.append("---\n")

    with open(output_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))

    return output_path
