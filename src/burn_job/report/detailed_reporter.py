"""Detailed Findings Report Generator & Console Renderer."""

import os
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel

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


def _safe(val: Any, fallback: str = "—") -> str:
    if val is None:
        return fallback
    if isinstance(val, float):
        return f"{val}/100"
    return str(val)


def print_findings_summary(findings: List[Dict[str, Any]], checked_not_issue: List[Dict[str, Any]] = None):
    if not findings:
        console.print(Panel("[bold green]✓ No performance defects detected[/bold green]", title="Audit Summary"))
        return

    console.print(f"\n[bold red]=== DETECTED PERFORMANCE VIOLATIONS ({len(findings)}) ===[/bold red]\n")

    for idx, f in enumerate(findings, 1):
        tax_codes = f.get("pdf_taxonomy", ["T1"])
        tax_codes_str = ", ".join(tax_codes)
        tax_title = ", ".join([TAXONOMY_NAMES.get(code, code) for code in tax_codes])
        file_path = f.get("file", "unknown")
        line_from = f.get("line_from", 1)
        mechanism = f.get("mechanism", "")
        impact = f.get("impact", "")
        variants = f.get("variants", [])

        sections = [
            f"[bold yellow]📍 Location:[/bold yellow] [green]{file_path}:{line_from}[/green]",
            f"[bold yellow]🏷️ Category:[/bold yellow] [cyan][{tax_codes_str}] {tax_title}[/cyan]",
            f"[bold yellow]⚠️ Impact:[/bold yellow] {impact}",
            "",
            f"[bold red]🔍 Analysis:[/bold red]\n{mechanism}",
        ]

        if variants:
            lines = []
            for v in variants:
                score = _safe(v.get("score"))
                marker = "🏆 WINNER" if v.get("is_winner") else "⚪"
                lines.append(f"  [{marker}] [bold]{v['strategy']}[/bold] — Score: [cyan]{score}[/cyan]")
            sections.append("")
            sections.append(f"[bold green]📋 Variants:[/bold green]")
            sections.append("\n".join(lines))

        if variants:
            w = variants[0] if any(v.get("is_winner") for v in variants) else variants[0]
            sections.append("")
            sections.append(f"[bold green]🏆 Winner:[/bold green] {w['strategy']} ([cyan]{_safe(w.get('score'))}[/cyan])")

        console.print(Panel(
            "\n".join(sections),
            title=f"[bold white]Finding #{idx} — [{tax_codes_str}] {os.path.basename(file_path)}:{line_from}[/bold white]",
            border_style="red",
            expand=True
        ))

    if checked_not_issue:
        console.print(f"\n[dim]Checked & Verified Non-Defects ({len(checked_not_issue)}):[/dim]")
        for item in checked_not_issue:
            console.print(f" - [dim]{item.get('file')}: {item.get('why_not')}[/dim]")


def generate_markdown_report(findings: List[Dict[str, Any]], checked_not_issue: List[Dict[str, Any]], output_path: str):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    lines = [
        "# 📊 Подробный отчёт: Анализ нарушений и варианты исправлений\n",
        f"> **Всего обнаружено нарушений:** `{len(findings)}`  \n",
        "> **Режим выполнения:** `REPORT ONLY` (исходный код не изменён)\n",
        "---\n",
    ]

    if not findings:
        lines.append("### ✅ Нарушений производительности не обнаружено.\n")
    else:
        lines.append("## 📋 Оглавление\n")
        lines.append("| № | Категория | Файл | Строка | Победивший вариант |")
        lines.append("|---|---|---|---|---|")
        for idx, f in enumerate(findings, 1):
            tax_codes_str = ", ".join(f.get("pdf_taxonomy", ["T1"]))
            file_name = os.path.basename(f.get("file", ""))
            winner = f.get("winner", {})
            w_title = winner.get("strategy", "—") if winner else "—"
            lines.append(f"| {idx} | `{tax_codes_str}` | [`{file_name}`](file://{os.path.abspath(f.get('file', ''))}#L{f.get('line_from', 1)}) | L{f.get('line_from', 1)} | **{w_title}** |")
        lines.append("\n---\n")

        lines.append("## 🔍 Разбор нарушений\n")

        for idx, f in enumerate(findings, 1):
            tax_codes = f.get("pdf_taxonomy", ["T1"])
            tax_codes_str = ", ".join(tax_codes)
            tax_title = ", ".join([TAXONOMY_NAMES.get(code, code) for code in tax_codes])
            file_path = f.get("file", "")
            line_from = f.get("line_from", 1)
            mechanism = f.get("mechanism", "")
            impact = f.get("impact", "")
            variants = f.get("variants", [])
            winner = f.get("winner", {})

            w_title = winner.get("strategy", "—") if winner else "—"
            w_score = _safe(winner.get("score")) if winner else "—"

            lines.append(f"### Finding #{idx}: [{tax_codes_str}] {os.path.basename(file_path)} (Line {line_from})\n")
            lines.append(f"- **Категория:** `{tax_codes_str}` — {tax_title}")
            lines.append(f"- **Файл:** [`{file_path}`](file://{os.path.abspath(file_path)}#L{line_from})")
            lines.append(f"- **Влияние:** {impact}\n")

            lines.append("#### 🔍 Анализ")
            lines.append(f"```text\n{mechanism}\n```\n")

            if variants:
                lines.append("#### 🛠️ Варианты исправлений\n")
                lines.append("| Вариант | Score | Результат |")
                lines.append("|---|---|---|")
                for v in variants:
                    score = _safe(v.get("score"))
                    marker = "🏆 **Победитель**" if v.get("is_winner") else "⚪ Альтернатива"
                    lines.append(f"| **{v['strategy']}** | {score} | {marker} |")
                lines.append("")

            if winner:
                lines.append(f"#### 🏆 Победивший вариант: {w_title}")
                lines.append(f"> **Score:** {w_score}  \n> _Результаты бенчмарка требуют профилирования._\n")

            lines.append("---\n")

    with open(output_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))

    return output_path
