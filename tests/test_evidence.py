from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest
from pubdelays_analysis.evidence import build_evidence


def test_build_evidence_writes_aggregate_summary_and_figures(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    run = tmp_path / "run"
    (run / "validation_tables").mkdir(parents=True)
    (run / "summaries").mkdir()
    (run / "quality").mkdir()
    pl.DataFrame({"stage": ["raw_records", "final_rows"], "count": [10, 5]}).write_csv(
        run / "filter_counts.csv"
    )
    pl.DataFrame(
        {"cohort": ["acceptance_delay"], "rows_in": [5], "eligible": [4], "excluded": [1]}
    ).write_csv(run / "validation_tables" / "outcome_eligibility.csv")
    pl.DataFrame(
        {"check": ["unique:pmid"], "status": ["pass"], "checked": [5], "failed": [0]}
    ).write_csv(run / "validation_tables" / "validation_checks.csv")
    pl.DataFrame(
        {
            "article_year": [2024, 2025],
            "acceptance_delay_median_days": [100, 101],
            "acceptance_delay_p25_days": [60, 61],
            "acceptance_delay_p75_days": [160, 161],
            "publication_delay_median_days": [20, 21],
            "publication_delay_p25_days": [8, 9],
            "publication_delay_p75_days": [40, 41],
        }
    ).write_csv(run / "summaries" / "delay_distribution.csv")
    pl.DataFrame(
        {
            "record_type": ["join"],
            "checkpoint": ["external_join"],
            "source": ["doaj"],
            "year": ["__all__"],
            "variable": [""],
            "metric": ["matched"],
            "numerator": [2],
            "denominator": [5],
            "percent": [40.0],
        }
    ).write_csv(run / "quality" / "stage_and_join_debrief.csv")
    pl.DataFrame(
        {
            "year": ["__all__"],
            "variable": ["doi"],
            "total": [5],
            "present": [4],
            "missing": [1],
            "missing_percent": [20.0],
        }
    ).write_csv(run / "quality" / "variable_quality_debrief.csv")

    outputs = build_evidence(run, tmp_path / "evidence")

    assert all(path.is_file() and path.stat().st_size > 0 for path in outputs.values())
    summary = json.loads(outputs["summary"].read_text(encoding="utf-8"))
    assert summary["outcome_eligibility"][0]["eligible"] == "4"
