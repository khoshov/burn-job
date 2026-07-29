"""Detailed Findings Report Generator & Console Renderer (Markdown & Modern HTML)."""

import os
import html
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


def _calculate_improvement_metrics(finding: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate latency reduction % or AST improvement to evaluate optimization success."""
    baseline_bm = finding.get("baseline_benchmark", {})
    baseline_avg = baseline_bm.get("avg_s") if baseline_bm else None

    winner = finding.get("winner", {})
    winner_bm = winner.get("benchmark", {}) if winner else {}
    winner_avg = winner_bm.get("avg_s") if winner_bm else None

    orig_score = finding.get("original_score")
    winner_score = winner.get("score") if winner else None

    pct_gain = 0.0
    is_improved = False

    if baseline_avg is not None and winner_avg is not None and baseline_avg > 0:
        delta = baseline_avg - winner_avg
        pct_gain = (delta / baseline_avg) * 100.0
        is_improved = pct_gain > 0.5
    elif orig_score is not None and winner_score is not None:
        delta_score = winner_score - orig_score
        pct_gain = float(delta_score)
        is_improved = delta_score > 0.0
    else:
        is_improved = any(v.get("generated_code") for v in finding.get("variants", []))

    return {
        "pct_gain": round(pct_gain, 1),
        "is_improved": is_improved,
        "baseline_avg": baseline_avg,
        "winner_avg": winner_avg,
        "orig_score": orig_score,
        "winner_score": winner_score,
    }


def _sort_findings_by_improvement(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort findings so best performance gains appear first."""
    def sort_key(f):
        m = _calculate_improvement_metrics(f)
        return (1 if m["is_improved"] else 0, m["pct_gain"])

    return sorted(findings, key=sort_key, reverse=True)


def _explain_winner_selection(variants: List[Dict[str, Any]], winner: Dict[str, Any]) -> str:
    if not variants or not winner:
        return "Победитель выбран как первый вариант по умолчанию (нет данных для сравнения)."
    bench_scored = [v for v in variants if v.get("benchmark", {}).get("avg_s") is not None]
    if bench_scored:
        reasons = []
        for v in sorted(bench_scored, key=lambda x: x["benchmark"]["avg_s"]):
            tag = "🏆" if v.get("is_winner") else " "
            reasons.append(f"{tag} «{v['strategy']}»: {v['benchmark']['avg_s']}s avg")
        reasons.append(f"Победитель по benchmark: «{winner['strategy']}» ({winner['benchmark']['avg_s']}s)")
        return ". ".join(reasons) + "."
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

    sorted_findings = _sort_findings_by_improvement(findings)
    console.print(f"\n[bold red]=== DETECTED PERFORMANCE VIOLATIONS ({len(sorted_findings)}) ===[/bold red]\n")

    for idx, f in enumerate(sorted_findings, 1):
        m = _calculate_improvement_metrics(f)
        status_tag = f"[bold green]🚀 +{m['pct_gain']}%[/bold green]" if m["is_improved"] else "[dim]⚪ Без прироста[/dim]"
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
            f"[bold yellow]📍 Location:[/bold yellow] [green]{file_path}:{line_from}[/green] | Status: {status_tag}",
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

        if variants:
            sections.append("")
            sections.append("[bold green]📋 Variants Tested:[/bold green]")
            for v in variants:
                s = _safe(v.get("score"))
                marker = "🏆" if v.get("is_winner") else " "
                bm = v.get("benchmark", {})
                if bm.get("avg_s") is not None:
                    bm_str = f" ⏱ {bm['avg_s']}s / max {bm['max_s']}s"
                elif bm.get("error"):
                    bm_str = " ⏱ error"
                else:
                    bm_str = ""
                sections.append(f"  {marker} [bold]{v['strategy']}[/bold] — AST Score: [cyan]{s}[/cyan]{bm_str}")

        if winner:
            w_bm = winner.get("benchmark", {})
            w_bm_str = f" ⏱ {w_bm['avg_s']}s" if w_bm.get("avg_s") is not None else ""
            sections.append("")
            sections.append(f"[bold green]🏆 Winner:[/bold green] {w_strategy} (Score: [cyan]{w_score}[/cyan]{w_bm_str})")
            sections.append(f"[dim]{_explain_winner_selection(variants, winner)}[/dim]")

        console.print(Panel(
            "\n".join(sections),
            title=f"[bold white]Finding #{idx} — [{tax_codes_str}] {os.path.basename(file_path)}:{line_from}[/bold white]",
            border_style="green" if m["is_improved"] else "dim",
            expand=True
        ))


def generate_markdown_report(findings: List[Dict[str, Any]], checked_not_issue: List[Dict[str, Any]], output_path: str):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sorted_findings = _sort_findings_by_improvement(findings)

    lines = [
        "# 📊 Подробный отчёт: Анализ нарушений и сравнение вариантов исправлений\n",
        f"> **Всего обнаружено нарушений:** `{len(sorted_findings)}`  \n",
        "> **Отсортировано по:** Наибольшему эффекту ускорения  \n",
        "---\n",
    ]

    if not sorted_findings:
        lines.append("### ✅ Нарушений производительности не обнаружено.\n")
    else:
        lines.append("## 📋 Оглавление и сводка результатов\n")
        lines.append("| № | Категория | Файл | Строка | До улучшения | Победивший вариант | AST Score | После улучшения (avg) | Статус |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for idx, f in enumerate(sorted_findings, 1):
            m = _calculate_improvement_metrics(f)
            tax_codes_str = ", ".join(f.get("pdf_taxonomy", ["T1"]))
            file_name = os.path.basename(f.get("file", ""))
            winner = f.get("winner", {})
            w_title = winner.get("strategy", "—") if winner else "—"
            w_score = _safe(winner.get("score")) if winner else "—"
            w_bm = winner.get("benchmark", {})
            w_bm_str = f"⏱ {w_bm.get('avg_s')}s" if w_bm.get("avg_s") is not None else "—"

            bm_base = f.get("baseline_benchmark", {})
            orig_score = f.get("original_score")
            evidence = f.get("evidence", {})
            ev_before = evidence.get("before")

            if bm_base and bm_base.get("avg_s") is not None:
                before_str = f"⏱ {bm_base['avg_s']}s"
            elif ev_before is not None and isinstance(ev_before, (int, float)) and ev_before > 0:
                before_str = f"⏱ {ev_before}s" if isinstance(ev_before, float) else f"{ev_before} samples"
            elif orig_score is not None:
                before_str = f"AST: {orig_score}"
            else:
                before_str = "—"

            if orig_score is not None and winner.get("score") is not None and orig_score != winner.get("score"):
                ast_display = f"{orig_score} → {winner.get('score')}"
            else:
                ast_display = w_score

            status_badge = f"🚀 +{m['pct_gain']}%" if m["is_improved"] else "⚪ Без прироста"

            lines.append(f"| {idx} | `{tax_codes_str}` | [`{file_name}`](file://{os.path.abspath(f.get('file', ''))}#L{f.get('line_from', 1)}) | L{f.get('line_from', 1)} | `{before_str}` | **{w_title}** | `{ast_display}` | `{w_bm_str}` | {status_badge} |")
        lines.append("\n---\n")

        lines.append("## 🔍 Разбор нарушений\n")

        for idx, f in enumerate(sorted_findings, 1):
            m = _calculate_improvement_metrics(f)
            tax_codes = f.get("pdf_taxonomy", ["T1"])
            tax_codes_str = ", ".join(tax_codes)
            tax_title = ", ".join([TAXONOMY_NAMES.get(code, code) for code in tax_codes])
            file_path = f.get("file", "")
            line_from = f.get("line_from", 1)
            mechanism = f.get("mechanism", "")
            impact = f.get("impact", "")
            variants = f.get("variants", [])
            winner = f.get("winner", {})

            lines.append(f"### Finding #{idx}: [{tax_codes_str}] {os.path.basename(file_path)} (Line {line_from})\n")
            lines.append(f"- **Категория:** `{tax_codes_str}` — {tax_title}")
            lines.append(f"- **Файл:** [`{file_path}`](file://{os.path.abspath(file_path)}#L{line_from})")
            lines.append(f"- **Статус оптимизации:** {'🚀 **Улучшено (+' + str(m['pct_gain']) + '%)**' if m['is_improved'] else '⚪ **Без прироста (нейтрально)**'}")
            lines.append(f"- **Влияние:** {impact}\n")

            lines.append("#### 🔍 Анализ")
            lines.append(f"```text\n{mechanism}\n```\n")

            if variants:
                lines.append("#### 🛠️ Сравнение вариантов исправлений\n")
                lines.append("| Вариант | AST Score | Бенчмарк (avg) | Результат |")
                lines.append("|---|---|---|---|")
                for v in variants:
                    s = _safe(v.get("score"))
                    marker = "🏆 **Победитель**" if v.get("is_winner") else "⚪ Альтернатива"
                    bm = v.get("benchmark", {})
                    if bm.get("avg_s") is not None:
                        bm_str = f"⏱ {bm['avg_s']}s / max {bm['max_s']}s"
                    elif bm.get("error"):
                        bm_str = "❌ " + bm["error"]
                    else:
                        bm_str = "—"
                    lines.append(f"| **{v['strategy']}** | `{s}` | `{bm_str}` | {marker} |")
                lines.append("")

                for v in variants:
                    gen_code = v.get("generated_code")
                    if gen_code:
                        label = "🏆 Генерированный код (победитель)" if v.get("is_winner") else f"📄 Код: {v['strategy']}"
                        lines.append(f"**{label}**")
                        lines.append(f"```java\n{gen_code}\n```\n")

            lines.append("---\n")

    with open(output_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))

    return output_path


def generate_html_report(findings: List[Dict[str, Any]], checked_not_issue: List[Dict[str, Any]], output_path: str) -> str:
    """Generate modern, interactive HTML performance optimization report with dark theme & filtering."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sorted_findings = _sort_findings_by_improvement(findings)

    total_findings = len(sorted_findings)
    improved_count = sum(1 for f in sorted_findings if _calculate_improvement_metrics(f)["is_improved"])
    neutral_count = total_findings - improved_count

    top_speedup = max((_calculate_improvement_metrics(f)["pct_gain"] for f in sorted_findings), default=0.0)

    # Render summary table rows
    table_rows = []
    for idx, f in enumerate(sorted_findings, 1):
        m = _calculate_improvement_metrics(f)
        tax_codes_str = ", ".join(f.get("pdf_taxonomy", ["T1"]))
        file_name = html.escape(os.path.basename(f.get("file", "")))
        abs_path = html.escape(os.path.abspath(f.get("file", "")))
        winner = f.get("winner", {})
        w_title = html.escape(winner.get("strategy", "—")) if winner else "—"
        w_score = _safe(winner.get("score")) if winner else "—"
        w_bm = winner.get("benchmark", {})
        w_bm_str = f"⏱ {w_bm.get('avg_s')}s" if w_bm.get("avg_s") is not None else "—"

        bm_base = f.get("baseline_benchmark", {})
        orig_score = f.get("original_score")
        ev_before = f.get("evidence", {}).get("before")

        if bm_base and bm_base.get("avg_s") is not None:
            before_str = f"⏱ {bm_base['avg_s']}s"
        elif ev_before is not None and isinstance(ev_before, (int, float)) and ev_before > 0:
            before_str = f"⏱ {ev_before}s" if isinstance(ev_before, float) else f"{ev_before} samples"
        elif orig_score is not None:
            before_str = f"AST: {orig_score}"
        else:
            before_str = "—"

        if orig_score is not None and winner.get("score") is not None and orig_score != winner.get("score"):
            ast_display = f"{orig_score} &rarr; {winner.get('score')}"
        else:
            ast_display = w_score

        if m["is_improved"]:
            status_badge = f'<span class="badge badge-success">🚀 +{m["pct_gain"]}% Ускорение</span>'
            row_class = "row-improved"
        else:
            status_badge = '<span class="badge badge-neutral">⚪ Без прироста</span>'
            row_class = "row-neutral"

        table_rows.append(f"""
        <tr class="{row_class}">
            <td><strong>#{idx}</strong></td>
            <td><span class="tax-tag">{tax_codes_str}</span></td>
            <td><a href="file://{abs_path}#L{f.get('line_from', 1)}" class="file-link">{file_name}:L{f.get('line_from', 1)}</a></td>
            <td><code class="val-code">{before_str}</code></td>
            <td><strong>{w_title}</strong></td>
            <td><code class="val-code">{ast_display}</code></td>
            <td><code class="val-code highlight">{w_bm_str}</code></td>
            <td>{status_badge}</td>
        </tr>""")

    # Render Detail Cards
    detail_cards = []
    for idx, f in enumerate(sorted_findings, 1):
        m = _calculate_improvement_metrics(f)
        tax_codes = f.get("pdf_taxonomy", ["T1"])
        tax_codes_str = ", ".join(tax_codes)
        tax_title = ", ".join([TAXONOMY_NAMES.get(code, code) for code in tax_codes])
        file_path = html.escape(f.get("file", ""))
        abs_path = html.escape(os.path.abspath(f.get("file", "")))
        line_from = f.get("line_from", 1)
        mechanism = html.escape(f.get("mechanism", ""))
        impact = html.escape(f.get("impact", ""))
        variants = f.get("variants", [])
        winner = f.get("winner", {})

        is_imp = m["is_improved"]
        card_class = "card-improved" if is_imp else "card-neutral"
        status_html = f'<span class="badge badge-success">🚀 +{m["pct_gain"]}% Ускорение</span>' if is_imp else '<span class="badge badge-neutral">⚪ Без прироста (нейтрально)</span>'

        # Render Variant rows
        variant_rows = []
        code_tabs = []
        for v_idx, v in enumerate(variants, 1):
            s = _safe(v.get("score"))
            is_w = v.get("is_winner")
            marker = '<span class="badge badge-winner">🏆 Победитель</span>' if is_w else '<span class="badge badge-alt">⚪ Альтернатива</span>'
            bm = v.get("benchmark", {})
            if bm.get("avg_s") is not None:
                max_str = f" (max {bm['max_s']}s)" if bm.get("max_s") is not None else ""
                bm_str = f"⏱ {bm['avg_s']}s{max_str}"
            elif bm.get("error"):
                bm_str = f"❌ {html.escape(bm['error'])}"
            else:
                bm_str = "—"

            variant_rows.append(f"""
            <tr class="{'winner-row' if is_w else ''}">
                <td><strong>{html.escape(v.get('strategy', '—'))}</strong></td>
                <td><code>{s}</code></td>
                <td><code>{bm_str}</code></td>
                <td>{marker}</td>
            </tr>""")

            gen_code = v.get("generated_code")
            if gen_code:
                tab_id = f"code_f{idx}_v{v_idx}"
                code_esc = html.escape(gen_code)
                code_tabs.append(f"""
                <div class="code-block-container">
                    <div class="code-header">
                        <span>{'🏆 Победивший вариант' if is_w else f'📄 Вариант #{v_idx}: ' + html.escape(v.get('strategy', ''))}</span>
                    </div>
                    <pre><code class="language-java">{code_esc}</code></pre>
                </div>""")

        variant_table_html = f"""
        <table class="variant-table">
            <thead>
                <tr>
                    <th>Стратегия оптимизации</th>
                    <th>AST Score</th>
                    <th>Latency (avg)</th>
                    <th>Результат</th>
                </tr>
            </thead>
            <tbody>
                {''.join(variant_rows)}
            </tbody>
        </table>""" if variants else ""

        detail_cards.append(f"""
        <div class="finding-card {card_class}" data-status="{'improved' if is_imp else 'neutral'}">
            <div class="card-header">
                <div>
                    <span class="finding-number">Finding #{idx}</span>
                    <span class="tax-badge">[{tax_codes_str}]</span>
                    <span class="tax-title">{html.escape(tax_title)}</span>
                </div>
                <div>{status_html}</div>
            </div>
            <div class="card-meta">
                <div>📍 <strong>Файл:</strong> <a href="file://{abs_path}#L{line_from}" class="file-link">{file_path}:L{line_from}</a></div>
                <div>⚠️ <strong>Влияние:</strong> {impact}</div>
            </div>
            <div class="section-title">🔍 Анализ узкого места</div>
            <div class="mechanism-box">{mechanism}</div>
            
            <div class="section-title">🛠️ Сравнение вариантов исправлений</div>
            {variant_table_html}

            <div class="code-tabs-wrapper">
                {''.join(code_tabs)}
            </div>
        </div>""")

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Burn Job — Отчёт по оптимизации производительности</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {{
            --bg-color: #0b0f17;
            --card-bg: #151d2a;
            --card-border: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-green: #10b981;
            --accent-green-bright: #34d399;
            --accent-blue: #38bdf8;
            --accent-dim: #64748b;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem 1.5rem;
        }}

        .container {{
            max-width: 1280px;
            margin: 0 auto;
        }}

        /* Header Dashboard */
        .dashboard-header {{
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.5rem;
        }}

        .dashboard-title {{
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #38bdf8, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .dashboard-subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.25rem;
            margin: 2rem 0;
        }}

        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
        }}

        .stat-val {{
            font-size: 2rem;
            font-weight: 800;
            margin-top: 0.25rem;
        }}

        .stat-val.green {{ color: var(--accent-green-bright); }}
        .stat-val.blue {{ color: var(--accent-blue); }}
        .stat-val.grey {{ color: var(--accent-dim); }}

        /* Filter Controls */
        .controls-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}

        .filter-btn-group {{
            display: flex;
            gap: 0.5rem;
            background: #111827;
            padding: 4px;
            border-radius: 10px;
            border: 1px solid var(--card-border);
        }}

        .filter-btn {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .filter-btn.active {{
            background: var(--card-bg);
            color: var(--text-primary);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
        }}

        /* Table */
        .table-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            overflow: hidden;
            margin-bottom: 3rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.92rem;
        }}

        th {{
            background: #0f172a;
            color: var(--text-secondary);
            font-weight: 600;
            padding: 12px 16px;
            border-bottom: 1px solid var(--card-border);
        }}

        td {{
            padding: 14px 16px;
            border-bottom: 1px solid rgba(30, 41, 59, 0.6);
        }}

        .row-improved {{
            background: rgba(16, 185, 129, 0.03);
        }}

        .row-neutral {{
            opacity: 0.7;
            background: rgba(15, 23, 42, 0.4);
        }}

        .tax-tag {{
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-blue);
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.82rem;
        }}

        .file-link {{
            color: var(--accent-blue);
            text-decoration: none;
            font-weight: 500;
        }}

        .file-link:hover {{ text-decoration: underline; }}

        .val-code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.88rem;
        }}

        .val-code.highlight {{
            color: var(--accent-green-bright);
            font-weight: 600;
        }}

        /* Badges */
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .badge-success {{
            background: rgba(16, 185, 129, 0.18);
            color: var(--accent-green-bright);
            border: 1px solid rgba(52, 211, 153, 0.4);
        }}

        .badge-neutral {{
            background: rgba(148, 163, 184, 0.1);
            color: #94a3b8;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }}

        .badge-winner {{
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
        }}

        .badge-alt {{
            background: rgba(255, 255, 255, 0.05);
            color: #94a3b8;
        }}

        /* Cards */
        .finding-card {{
            background: var(--card-bg);
            border-radius: 14px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            transition: transform 0.2s ease, opacity 0.2s ease;
        }}

        .card-improved {{
            border: 1px solid rgba(52, 211, 153, 0.35);
            box-shadow: 0 4px 20px rgba(16, 185, 129, 0.05);
        }}

        .card-neutral {{
            border: 1px solid rgba(148, 163, 184, 0.15);
            opacity: 0.72;
            background: #121926;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}

        .finding-number {{
            font-size: 1.25rem;
            font-weight: 800;
            margin-right: 0.75rem;
        }}

        .tax-badge {{
            color: var(--accent-blue);
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            margin-right: 0.5rem;
        }}

        .tax-title {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}

        .card-meta {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 1.25rem;
            display: flex;
            gap: 2rem;
        }}

        .section-title {{
            font-size: 0.95rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin: 1.25rem 0 0.5rem 0;
        }}

        .mechanism-box {{
            background: #0d131f;
            border: 1px solid var(--card-border);
            padding: 1rem;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: #cbd5e1;
            white-space: pre-wrap;
        }}

        .variant-table {{
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
        }}

        .winner-row {{
            background: rgba(16, 185, 129, 0.08);
        }}

        /* Code Blocks */
        .code-block-container {{
            background: #090d14;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            margin-top: 1rem;
            overflow: hidden;
        }}

        .code-header {{
            background: #111724;
            padding: 8px 14px;
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--card-border);
        }}

        pre {{
            padding: 1rem;
            overflow-x: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: #e2e8f0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="dashboard-header">
            <h1 class="dashboard-title">Burn Job — Performance Optimization Report</h1>
            <p class="dashboard-subtitle">Результаты автоматического анализа нарушений и оценки вариантов сгенерированного кода</p>
        </header>

        <section class="stats-grid">
            <div class="stat-card">
                <span class="stat-label">Всего нарушений</span>
                <span class="stat-val blue">{total_findings}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Успешно улучшено</span>
                <span class="stat-val green">{improved_count}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Нейтральные / Без прироста</span>
                <span class="stat-val grey">{neutral_count}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Макс. прирост latency</span>
                <span class="stat-val green">+{top_speedup}%</span>
            </div>
        </section>

        <div class="controls-bar">
            <h2>📋 Оглавление и сводка (отсортировано по эффекту)</h2>
            <div class="filter-btn-group">
                <button onclick="filterFindings('all')" class="filter-btn active" id="btn-all">Все ({total_findings})</button>
                <button onclick="filterFindings('improved')" class="filter-btn" id="btn-improved">🚀 Улучшенные ({improved_count})</button>
                <button onclick="filterFindings('neutral')" class="filter-btn" id="btn-neutral">⚪ Без прироста ({neutral_count})</button>
            </div>
        </div>

        <section class="table-card">
            <table>
                <thead>
                    <tr>
                        <th>№</th>
                        <th>Тег</th>
                        <th>Файл и строка</th>
                        <th>До улучшения</th>
                        <th>Победивший вариант</th>
                        <th>AST Score</th>
                        <th>После (avg)</th>
                        <th>Статус</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
            </table>
        </section>

        <section id="findings-cards-section">
            <h2 style="margin-bottom: 1.5rem;">🔍 Подробный разбор каждого узкого места</h2>
            {''.join(detail_cards)}
        </section>
    </div>

    <script>
        function filterFindings(status) {{
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('btn-' + status).classList.add('active');

            const cards = document.querySelectorAll('.finding-card');
            cards.forEach(card => {{
                if (status === 'all') {{
                    card.style.display = 'block';
                }} else if (status === 'improved') {{
                    card.style.display = card.getAttribute('data-status') === 'improved' ? 'block' : 'none';
                }} else if (status === 'neutral') {{
                    card.style.display = card.getAttribute('data-status') === 'neutral' ? 'block' : 'none';
                }}
            }});
        }}
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
