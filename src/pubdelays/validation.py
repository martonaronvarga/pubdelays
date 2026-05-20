"""Differential validation helpers for comparing two processed outputs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from pubdelays.external.common import write_frame

KEY_COLUMNS = ("doi", "pmid", "title")
HASH_COLUMNS = (
    "doi",
    "title",
    "journal",
    "issn_linking",
    "received",
    "accepted",
    "article_date",
    "acceptance_delay",
    "publication_delay",
)


@dataclass(frozen=True)
class DifferentialValidationResult:
    """Summary of a baseline-vs-candidate dataset comparison report."""

    report_path: Path
    rows: int
    categories: dict[str, int]


def _read_table(path: Path) -> pl.DataFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        return pl.read_parquet(path)
    if path.suffix == ".tsv":
        return pl.read_csv(path, separator="\t", infer_schema=False)
    return pl.read_csv(path, infer_schema=False)


def _ensure_text(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        [pl.col(col).cast(pl.Utf8, strict=False).fill_null("").alias(col) for col in df.columns]
    )


def _row_hash(row: dict[str, object]) -> str:
    payload = "\x1f".join(str(row.get(col, "") or "") for col in HASH_COLUMNS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _key(row: dict[str, object]) -> str:
    for col in KEY_COLUMNS:
        value = str(row.get(col, "") or "").strip().lower()
        if value:
            return f"{col}:{value}"
    return "title:"


def _pubdate_correction(row: dict[str, object]) -> bool:
    return (
        str(row.get("publication_date_source", "")) == "pubdate"
        and str(row.get("publication_delay", "")) not in {"", "None"}
    )


def _ceased_correction(row: dict[str, object]) -> bool:
    return str(row.get("ceased_before_publication", "")).lower() in {"1", "true", "yes"}


def compare_outputs(baseline_path: Path, candidate_path: Path, output_path: Path) -> DifferentialValidationResult:
    """Write a row-level comparison report between two processed outputs."""
    baseline = _ensure_text(_read_table(baseline_path))
    candidate = _ensure_text(_read_table(candidate_path))
    baseline_rows = {_key(row): row for row in baseline.to_dicts()}
    candidate_rows = {_key(row): row for row in candidate.to_dicts()}
    records: list[dict[str, str]] = []

    categories = {
        "expected_correction": 0,
        "format_or_type_difference": 0,
        "potential_migration_bug": 0,
    }

    if baseline.columns != candidate.columns:
        records.append(
            {
                "category": "format_or_type_difference",
                "key": "columns",
                "detail": f"baseline={baseline.columns}; candidate={candidate.columns}",
            }
        )
        categories["format_or_type_difference"] += 1

    for key in sorted(set(baseline_rows) | set(candidate_rows)):
        old = baseline_rows.get(key)
        new_row = candidate_rows.get(key)
        if old is None and new_row is not None:
            category = "expected_correction" if _pubdate_correction(new_row) else "potential_migration_bug"
            detail = "candidate-only row"
        elif new_row is None and old is not None:
            category = "expected_correction" if _ceased_correction(old) else "potential_migration_bug"
            detail = "baseline-only row"
        elif old is not None and new_row is not None and _row_hash(old) != _row_hash(new_row):
            category = "format_or_type_difference"
            detail = "matched row hash differs"
        else:
            continue
        categories[category] += 1
        records.append({"category": category, "key": key, "detail": detail})

    report = pl.DataFrame(records or [{"category": "ok", "key": "", "detail": "no differences"}])
    write_frame(output_path, report)
    return DifferentialValidationResult(Path(output_path), len(records), categories)
