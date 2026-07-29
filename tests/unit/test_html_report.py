"""Unit tests for HTML report generation, improvement sorting, and status deemphasis."""

import os
import pytest
from burn_job.report.detailed_reporter import (
    _calculate_improvement_metrics,
    _sort_findings_by_improvement,
    generate_html_report,
)


def test_calculate_improvement_metrics_improved_vs_unimproved():
    """Verify speedup % calculation and improvement flag logic."""
    improved_finding = {
        "baseline_benchmark": {"avg_s": 0.200},
        "winner": {"benchmark": {"avg_s": 0.050}, "score": 100.0},
        "original_score": 80.0,
    }

    neutral_finding = {
        "baseline_benchmark": {"avg_s": 0.100},
        "winner": {"benchmark": {"avg_s": 0.105}, "score": 80.0},
        "original_score": 80.0,
    }

    m_imp = _calculate_improvement_metrics(improved_finding)
    assert m_imp["is_improved"] is True
    assert m_imp["pct_gain"] == 75.0  # (0.200 - 0.050) / 0.200 * 100% = 75%

    m_neu = _calculate_improvement_metrics(neutral_finding)
    assert m_neu["is_improved"] is False
    assert m_neu["pct_gain"] <= 0


def test_sort_findings_by_improvement():
    """Verify findings are sorted in descending order of performance gain."""
    f_neutral = {
        "baseline_benchmark": {"avg_s": 0.100},
        "winner": {"benchmark": {"avg_s": 0.100}},
        "file": "Neutral.java",
    }
    f_high_gain = {
        "baseline_benchmark": {"avg_s": 1.000},
        "winner": {"benchmark": {"avg_s": 0.200}},
        "file": "HighGain.java",
    }
    f_mid_gain = {
        "baseline_benchmark": {"avg_s": 0.500},
        "winner": {"benchmark": {"avg_s": 0.250}},
        "file": "MidGain.java",
    }

    sorted_list = _sort_findings_by_improvement([f_neutral, f_high_gain, f_mid_gain])
    assert sorted_list[0]["file"] == "HighGain.java"
    assert sorted_list[1]["file"] == "MidGain.java"
    assert sorted_list[2]["file"] == "Neutral.java"


def test_generate_html_report_file_output(tmp_path):
    """Verify generate_html_report writes valid HTML content with proper styling classes."""
    out_file = str(tmp_path / "test_report.html")

    findings = [
        {
            "file": "test_project/src/main/java/com/example/TestController.java",
            "line_from": 15,
            "pdf_taxonomy": ["T1"],
            "mechanism": "Redundant loop lookup",
            "impact": "HIGH",
            "baseline_benchmark": {"avg_s": 0.300},
            "original_score": 80.0,
            "variants": [
                {
                    "strategy": "Batch Lookup & Map Indexing",
                    "score": 100.0,
                    "benchmark": {"avg_s": 0.060, "max_s": 0.100, "count": 500},
                    "is_winner": True,
                    "generated_code": "public class Optimized {}",
                }
            ],
            "winner": {
                "strategy": "Batch Lookup & Map Indexing",
                "score": 100.0,
                "benchmark": {"avg_s": 0.060},
            },
        },
        {
            "file": "test_project/src/main/java/com/example/NeutralController.java",
            "line_from": 40,
            "pdf_taxonomy": ["T5"],
            "mechanism": "Dead code check",
            "impact": "LOW",
            "baseline_benchmark": {"avg_s": 0.050},
            "original_score": 90.0,
            "variants": [
                {
                    "strategy": "Guard Clause Consolidation",
                    "score": 90.0,
                    "benchmark": {"avg_s": 0.051},
                    "is_winner": True,
                }
            ],
            "winner": {"strategy": "Guard Clause Consolidation", "score": 90.0, "benchmark": {"avg_s": 0.051}},
        },
    ]

    res_path = generate_html_report(findings, [], out_file)
    assert os.path.exists(res_path)

    with open(res_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    assert "Burn Job — Отчёт по оптимизации производительности" in html_content
    assert "row-improved" in html_content
    assert "row-neutral" in html_content
    assert "card-improved" in html_content
    assert "card-neutral" in html_content
    assert "🚀 +80.0% Ускорение" in html_content
    assert "⚪ Без прироста" in html_content
