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


def _safe(val: Any, fallback: str = "—", suffix: str = "") -> str:
    if val is None:
        return fallback
    if suffix:
        return f"{val}{suffix}"
    return str(val)


def _compile_badge(v: Dict[str, Any]) -> str:
    c = v.get("compiles")
    if c is True:
        return "✓"
    if c is False:
        return "✗"
    return "—"


def _explain_winner_selection(variants: List[Dict[str, Any]], winner: Dict[str, Any]) -> str:
    if not variants or not winner:
        return "Победитель выбран как первый вариант по умолчанию (нет данных для сравнения)."
    scored = [v for v in variants if v.get("score") is not None]
    if not scored:
        return "Победитель выбран как первый вариант (варианты не были оценены — нет LLM или AST-данных)."
    best_score = max(v.get("score") or 0 for v in scored)
    reasons = []
    for v in scored:
        reasons.append(f"«{v['strategy']}»: AST-score = {v['score']}")
    reasons.append(f"Победитель: «{winner['strategy']}» (максимальный AST-score = {best_score})")
    if any(v.get("compiles") is False for v in variants):
        reasons.append("Варианты с ошибкой компиляции дисквалифицированы.")
    return ". ".join(reasons) + "."


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
        winner = f.get("winner", {})

        w_score = _safe(winner.get("score")) if winner else "—"
        w_strategy = winner.get("strategy", "—") if winner else "—"

        sections = [
            f"[bold yellow]📍 Location:[/bold yellow] [green]{file_path}:{line_from}[/green]",
            f"[bold yellow]🏷️ Category:[/bold yellow] [cyan][{tax_codes_str}] {tax_title}[/cyan]",
            f"[bold yellow]⚠️ Impact:[/bold yellow] {impact}",
            "",
            f"[bold red]🔍 Analysis:[/bold red]\n{mechanism}",
        ]

        llm_model = f.get("llm_model")
        if llm_model:
            sections.insert(0, f"[bold magenta]🤖 LLM:[/bold magenta] [cyan]{llm_model}[/cyan]")

        evidence = f.get("evidence", {})
        if evidence:
            ev_before = evidence.get("before", 0)
            ev_after = evidence.get("after", 0)
            ev_channel = evidence.get("channel", "—")
            sections.append(f"[bold blue]📊 Profiling:[/bold blue] channel=[cyan]{ev_channel}[/cyan] before=[red]{ev_before}[/red] after=[green]{ev_after}[/green]")
            sections.append(f"  [dim]{evidence.get('how', '')}[/dim]")

        if variants:
            sections.append("")
            sections.append("[bold green]📋 Variants Tested:[/bold green]")
            for v in variants:
                s = _safe(v.get("score"))
                c = _compile_badge(v)
                marker = "🏆" if v.get("is_winner") else " "
                bm = v.get("benchmark", {})
                if bm.get("avg_s") is not None:
                    bm_str = f" ⏱ {bm['avg_s']}s / max {bm['max_s']}s"
                elif bm.get("error"):
                    bm_str = " ⏱ error"
                else:
                    bm_str = ""
                sections.append(f"  {marker} [{c}] [bold]{v['strategy']}[/bold] — AST Score: [cyan]{s}[/cyan]{bm_str}")
                gen_code = v.get("generated_code")
                if gen_code:
                    label = "wins" if v.get("is_winner") else "alt"
                    first_line = gen_code.split("\n")[0] if gen_code else ""
                    sections.append(f"    [dim]└ Generated ({label}): {first_line[:80]}{'…' if len(first_line) > 80 else ''}[/dim]")

        if winner:
            sections.append("")
            sections.append(f"[bold green]🏆 Winner:[/bold green] {w_strategy} (Score: [cyan]{w_score}[/cyan])")
            sections.append(f"[dim]{_explain_winner_selection(variants, winner)}[/dim]")

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
        "# 📊 Подробный отчёт: Анализ нарушений и сравнение вариантов исправлений\n",
        f"> **Всего обнаружено нарушений:** `{len(findings)}`  \n",
        "> **Режим выполнения:** `REPORT ONLY` (исходный код не изменён)\n",
        "---\n",
    ]

    if not findings:
        lines.append("### ✅ Нарушений производительности не обнаружено.\n")
    else:
        lines.append("## 📋 Оглавление\n")
        lines.append("| № | Категория | Файл | Строка | Победивший вариант | AST Score | Бенчмарк (avg) |")
        lines.append("|---|---|---|---|---|---|---|")
        for idx, f in enumerate(findings, 1):
            tax_codes_str = ", ".join(f.get("pdf_taxonomy", ["T1"]))
            file_name = os.path.basename(f.get("file", ""))
            winner = f.get("winner", {})
            w_title = winner.get("strategy", "—") if winner else "—"
            w_score = _safe(winner.get("score")) if winner else "—"
            w_bm = winner.get("benchmark", {})
            w_bm_str = f"⏱ {w_bm.get('avg_s')}s" if w_bm.get("avg_s") is not None else "—"
            lines.append(f"| {idx} | `{tax_codes_str}` | [`{file_name}`](file://{os.path.abspath(f.get('file', ''))}#L{f.get('line_from', 1)}) | L{f.get('line_from', 1)} | **{w_title}** | `{w_score}` | `{w_bm_str}` |")
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

            llm_model = f.get("llm_model")
            if llm_model:
                lines.append(f"> **🤖 Анализ выполнен LLM:** `{llm_model}`\n")

            lines.append(f"- **Категория:** `{tax_codes_str}` — {tax_title}")
            lines.append(f"- **Файл:** [`{file_path}`](file://{os.path.abspath(file_path)}#L{line_from})")
            lines.append(f"- **Влияние:** {impact}\n")

            evidence = f.get("evidence", {})
            if evidence:
                ev_before = evidence.get("before", 0)
                ev_after = evidence.get("after", 0)
                ev_channel = evidence.get("channel", "—")
                lines.append(f"- **📊 Профилирование:** канал `{ev_channel}`, сэмплов до: `{ev_before}`, после: `{ev_after}`")
                lines.append(f"  > {evidence.get('how', '')}\n")

            lines.append("#### 🔍 Анализ")
            lines.append(f"```text\n{mechanism}\n```\n")

            if variants:
                lines.append("#### 🛠️ Сравнение вариантов исправлений\n")
                lines.append("| Вариант | AST Score | Бенчмарк (avg) | Компиляция | Результат |")
                lines.append("|---|---|---|---|---|")
                for v in variants:
                    s = _safe(v.get("score"))
                    c = {True: "✅", False: "❌", None: "—"}.get(v.get("compiles"), "—")
                    marker = "🏆 **Победитель**" if v.get("is_winner") else "⚪ Альтернатива"
                    bm = v.get("benchmark", {})
                    if bm.get("avg_s") is not None:
                        bm_str = f"⏱ {bm['avg_s']}s / max {bm['max_s']}s ({bm.get('count')} reqs)"
                    elif bm.get("error"):
                        bm_str = "❌ " + bm["error"]
                    else:
                        bm_str = "—"
                    lines.append(f"| **{v['strategy']}** | `{s}` | `{bm_str}` | {c} | {marker} |")
                lines.append("")

                for v in variants:
                    gen_code = v.get("generated_code")
                    if gen_code:
                        label = "🏆 Генерированный код (победитель)" if v.get("is_winner") else f"📄 Код: {v['strategy']}"
                        lines.append(f"**{label}**")
                        lines.append(f"```java\n{gen_code}\n```\n")

            if winner and variants:
                lines.append("#### 🏆 Обоснование выбора победителя")
                lines.append(f"> {_explain_winner_selection(variants, winner)}\n")

            lines.append("---\n")

    with open(output_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))

    return output_path
