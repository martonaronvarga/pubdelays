"""Directory of Open Access Journals preprocessing, implemented with Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from .common import (
    first_by_key,
    issn_expr,
    normalize_columns,
    read_csv_polars,
    write_frame,
)

DOAJ_FIELDS = [
    "journal_title",
    "review_process",
    "apc",
    "apc_amount",
    "does_the_journal_comply_to_doaj_s_definition_of_open_access",
    "issn_linking",
]


def preprocess_doaj(input_csv: Path, output: Path) -> int:
    df = normalize_columns(read_csv_polars(Path(input_csv)))
    rename = {
        "journal_issn_print_version": "journal_issn_print_version",
        "journal_eissn_online_version": "journal_eissn_online_version",
    }
    df = df.rename({k: v for k, v in rename.items() if k in df.columns})
    for col in [
        *DOAJ_FIELDS,
        "journal_issn_print_version",
        "journal_eissn_online_version",
    ]:
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))

    df = (
        df.with_columns(
            pl.concat_list(
                [
                    pl.col("journal_issn_print_version").cast(pl.Utf8),
                    pl.col("journal_eissn_online_version").cast(pl.Utf8),
                ]
            ).alias("issn_parts")
        )
        .explode("issn_parts")
        .with_columns(issn_expr(pl.col("issn_parts")).alias("issn_linking"))
        .filter(pl.col("issn_linking") != "")
        .select(DOAJ_FIELDS)
    )
    return write_frame(output, first_by_key(df, "issn_linking"))
