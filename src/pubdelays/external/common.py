"""Polars-backed helpers for external metadata preprocessing.

All tabular IO goes through Polars; helper
functions are limited to string normalization, deterministic deduplication, and
atomic writes.

"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import polars as pl

from pubdelays.fs import atomic_output_path


def normalize_header(name: str) -> str:
    normalized = name.strip().lower()
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def normalize_issn_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.upper() == "NA":
        return ""
    return re.sub(r"[^0-9Xx]", "", text).upper()


def normalize_doi_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.strip()


def issn_expr(expr: pl.Expr) -> pl.Expr:
    return (
        expr.cast(pl.Utf8, strict=False)
        .str.strip_chars()
        .str.replace_all(r"[^0-9Xx]", "")
        .str.to_uppercase()
        .replace("NA", "")
    )


def doi_expr(expr: pl.Expr) -> pl.Expr:
    return (
        expr.cast(pl.Utf8, strict=False)
        .str.strip_chars()
        .str.to_lowercase()
        .str.replace(r"^https?://(dx\.)?doi\.org/", "")
        .str.replace(r"^doi:\s*", "")
        .str.strip_chars()
    )


def read_csv_polars(path: Path, *, separator: str = ",") -> pl.DataFrame:
    """Read raw CSV/TSV-like inputs without inferring identifier columns."""

    return pl.read_csv(
        Path(path),
        separator=separator,
        infer_schema=False,
        ignore_errors=False,
        try_parse_dates=False,
        encoding="utf8-lossy",
    )


def normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
    return df.rename({name: normalize_header(name) for name in df.columns})


def ensure_columns(df: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    exprs = []
    existing = set(df.columns)
    for col in columns:
        if col not in existing:
            exprs.append(pl.lit(None).cast(pl.Utf8).alias(col))
    return df.with_columns(exprs) if exprs else df


def first_by_key(df: pl.DataFrame, key: str) -> pl.DataFrame:
    if key not in df.columns:
        return df
    return df.filter(
        pl.col(key).is_not_null() & (pl.col(key).cast(pl.Utf8) != "")
    ).unique(subset=[key], keep="first", maintain_order=True)


def write_frame(
    path: Path, df: pl.DataFrame, *, format: str | None = None, separator: str = ","
) -> int:
    """Atomically write a Polars DataFrame.

    Format is inferred from suffix unless explicitly supplied.  CSV/TSV remains
    available for interoperability; Parquet is preferred for internal pipeline
    handoff.
    """

    path = Path(path)
    fmt = (format or path.suffix.lstrip(".") or "csv").lower()
    with atomic_output_path(path) as tmp_path:
        if fmt in {"parquet", "pq"}:
            df.write_parquet(tmp_path, compression="zstd")
        elif fmt == "tsv":
            df.write_csv(tmp_path, separator="\t")
        else:
            df.write_csv(tmp_path, separator=separator)
    return df.height


def scan_tabular(path: Path, *, separator: str = ",") -> pl.LazyFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        return pl.scan_parquet(path)
    if path.suffix == ".tsv":
        return pl.scan_csv(path, separator="\t", infer_schema=False)
    return pl.scan_csv(path, separator=separator, infer_schema=False)
