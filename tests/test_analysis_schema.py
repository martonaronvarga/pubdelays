from __future__ import annotations

from pathlib import Path

import polars as pl

from pubdelays.cli import main
from pubdelays.schema import (
    ANALYSIS_DATASET_VERSION,
    CANONICAL_ARTICLE_COLUMNS,
    validate_analysis_dataset_schema,
)


def test_analysis_schema_validator_accepts_exact_columns(tmp_path: Path) -> None:
    path = tmp_path / "processed.parquet"
    pl.DataFrame({column: [] for column in CANONICAL_ARTICLE_COLUMNS}).write_parquet(path)

    valid, errors = validate_analysis_dataset_schema(path)

    assert valid
    assert errors == []


def test_analysis_schema_validator_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "processed.csv"
    pl.DataFrame({"title": ["missing most columns"]}).write_csv(path)

    valid, errors = validate_analysis_dataset_schema(path)

    assert not valid
    assert any("missing columns" in error for error in errors)


def test_schema_cli_prints_version_and_validates_input(tmp_path: Path, capsys: object) -> None:
    path = tmp_path / "processed.parquet"
    pl.DataFrame({column: [] for column in CANONICAL_ARTICLE_COLUMNS}).write_parquet(path)

    assert main(["schema"]) == 0
    output = capsys.readouterr().out
    assert ANALYSIS_DATASET_VERSION in output
    assert "issn_linking" in output

    assert main(["schema", "--input", str(path)]) == 0
    output = capsys.readouterr().out
    assert f"matches {ANALYSIS_DATASET_VERSION}" in output
