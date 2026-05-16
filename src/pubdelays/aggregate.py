"""Aggregate transformed article shards with Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from pubdelays.external.common import write_frame
from pubdelays.schema import CANONICAL_ARTICLE_COLUMNS
from pubdelays.shards import iter_article_paths


def _scan_article(path: Path) -> pl.LazyFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        return pl.scan_parquet(path)
    if path.suffix == ".tsv":
        return pl.scan_csv(path, separator="\t", infer_schema_length=10000)
    return pl.scan_csv(path, infer_schema_length=10000)


def collect_articles(input_path: Path) -> pl.DataFrame:
    """Collect article shards and apply the final title-level deduplication."""

    paths = iter_article_paths(Path(input_path))
    if not paths:
        return pl.DataFrame({col: [] for col in CANONICAL_ARTICLE_COLUMNS})

    lf = pl.concat([_scan_article(path) for path in paths], how="diagonal_relaxed")
    df = lf.collect()
    for col in CANONICAL_ARTICLE_COLUMNS:
        if col not in df.columns:
            df = df.with_columns(pl.lit("").alias(col))
    return df.select(
        [
            pl.col(col).cast(pl.Utf8, strict=False).fill_null("").alias(col)
            for col in CANONICAL_ARTICLE_COLUMNS
        ]
    ).unique(subset=["title"], keep="first", maintain_order=True)


def aggregate_articles(input_path: Path, output_path: Path) -> int:
    """Aggregate article shards and write one output.

    This preserves the legacy ``distinct(title, .keep_all = TRUE)`` behavior,
    but uses Polars scans and writes Parquet/CSV/TSV based on the suffix.
    """

    df = collect_articles(Path(input_path))
    return write_frame(Path(output_path), df)


def aggregate_outputs(input_path: Path, output_paths: list[Path]) -> int:
    """Aggregate once and write several output formats without rereading shards."""

    df = collect_articles(Path(input_path))
    for output_path in output_paths:
        write_frame(Path(output_path), df)
    return df.height


# Backwards-compatible name for older CLI/tests.
def aggregate_tsvs(input_path: Path, output_csv: Path) -> int:
    return aggregate_articles(input_path, output_csv)
