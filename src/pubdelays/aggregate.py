"""Aggregate transformed article shards with Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from pubdelays.external.common import write_frame
from pubdelays.schema import CANONICAL_ARTICLE_COLUMNS


def iter_article_paths(input_path: Path) -> list[Path]:
    input_path = Path(input_path)
    if input_path.is_dir():
        return sorted(
            list(input_path.rglob("*.parquet"))
            + list(input_path.rglob("*.tsv"))
            + list(input_path.rglob("*.csv"))
        )
    return [input_path]


def _scan_article(path: Path) -> pl.LazyFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        return pl.scan_parquet(path)
    if path.suffix == ".tsv":
        return pl.scan_csv(path, separator="\t", infer_schema_length=10000)
    return pl.scan_csv(path, infer_schema_length=10000)


def aggregate_articles(input_path: Path, output_path: Path) -> int:
    """Concatenate article shards and keep the first row per title.

    This preserves the legacy `distinct(title, .keep_all = TRUE)` behavior, but
    uses Polars scans and writes Parquet/CSV/TSV based on the output suffix.
    """

    paths = iter_article_paths(Path(input_path))
    if not paths:
        out = pl.DataFrame({col: [] for col in CANONICAL_ARTICLE_COLUMNS})
        return write_frame(Path(output_path), out)

    lf = pl.concat([_scan_article(path) for path in paths], how="diagonal_relaxed")
    df = lf.collect()
    for col in CANONICAL_ARTICLE_COLUMNS:
        if col not in df.columns:
            df = df.with_columns(pl.lit("").alias(col))
    df = df.select(
        [
            pl.col(col).cast(pl.Utf8, strict=False).fill_null("").alias(col)
            for col in CANONICAL_ARTICLE_COLUMNS
        ]
    ).unique(subset=["title"], keep="first", maintain_order=True)
    return write_frame(Path(output_path), df)


# Backwards-compatible name for older CLI/tests.
def aggregate_tsvs(input_path: Path, output_csv: Path) -> int:
    return aggregate_articles(input_path, output_csv)
