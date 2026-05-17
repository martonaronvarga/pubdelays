"""Publisher metadata preprocessing."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from .common import issn_expr, normalize_columns, read_csv_polars, write_frame

PUBLISHER_FIELDS = [
    "issn_linking",
    "publisher",
    "publisher_group",
    "publisher_conflict",
    "publisher_group_conflict",
]


def _first_existing(df: pl.DataFrame, candidates: tuple[str, ...], output: str) -> pl.Expr:
    for column in candidates:
        if column in df.columns:
            return pl.col(column).cast(pl.Utf8, strict=False).str.strip_chars().alias(output)
    return pl.lit(None).cast(pl.Utf8).alias(output)


def preprocess_publisher(input_csv: Path, output: Path) -> int:
    df = normalize_columns(read_csv_polars(Path(input_csv)))
    df = df.with_columns(
        _first_existing(df, ("publisher", "publisher_name", "publisher_title"), "publisher"),
        _first_existing(df, ("publisher_group", "parent_publisher", "publisher_parent"), "publisher_group"),
    )
    for col in ["issn_linking", "issn", "print_issn", "e_issn", "online_issn"]:
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))

    exploded = (
        df.with_columns(
            pl.concat_list(
                [
                    pl.col("issn_linking").cast(pl.Utf8),
                    pl.col("issn").cast(pl.Utf8),
                    pl.col("print_issn").cast(pl.Utf8),
                    pl.col("e_issn").cast(pl.Utf8),
                    pl.col("online_issn").cast(pl.Utf8),
                ]
            ).alias("issn_parts")
        )
        .explode("issn_parts")
        .with_columns(issn_expr(pl.col("issn_parts")).alias("issn_linking"))
        .filter(pl.col("issn_linking") != "")
        .with_columns(
            pl.col("publisher").fill_null("").str.strip_chars().alias("publisher"),
            pl.col("publisher_group")
            .fill_null("")
            .str.strip_chars()
            .alias("publisher_group"),
        )
    )

    out = exploded.group_by("issn_linking", maintain_order=True).agg(
        pl.col("publisher").filter(pl.col("publisher") != "").first().fill_null(""),
        pl.col("publisher_group")
        .filter(pl.col("publisher_group") != "")
        .first()
        .fill_null(""),
        (pl.col("publisher").filter(pl.col("publisher") != "").n_unique() > 1)
        .cast(pl.Utf8)
        .replace({"true": "True", "false": "False"})
        .alias("publisher_conflict"),
        (pl.col("publisher_group").filter(pl.col("publisher_group") != "").n_unique() > 1)
        .cast(pl.Utf8)
        .replace({"true": "True", "false": "False"})
        .alias("publisher_group_conflict"),
    )
    return write_frame(output, out.select(PUBLISHER_FIELDS))
