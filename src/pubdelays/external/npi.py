"""Norwegian Publication Indicator preprocessing, implemented with Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from .common import first_by_key, issn_expr, normalize_columns, read_csv_polars, write_frame

NPI_FIELDS = [
    "npi_title",
    "npi_open_access",
    "npi_discipline",
    "npi_field",
    "npi_level_25",
    "npi_level_24",
    "npi_level_23",
    "npi_level_22",
    "npi_level_21",
    "npi_level_20",
    "npi_level_19",
    "npi_level_18",
    "npi_level_17",
    "npi_level_16",
    "npi_level_15",
    "country_of_publication",
    "language",
    "is_conference",
    "is_series",
    "established",
    "ceased",
    "issn_linking",
]


def preprocess_npi(input_csv: Path, output: Path) -> int:
    df = normalize_columns(read_csv_polars(Path(input_csv), separator=";"))
    rename = {
        "original_title": "npi_title",
        "open_access": "npi_open_access",
        "npi_academic_discipline": "npi_discipline",
        "npi_scientific_field": "npi_field",
        "level_2025": "npi_level_25",
        "level_2024": "npi_level_24",
        "level_2023": "npi_level_23",
        "level_2022": "npi_level_22",
        "level_2021": "npi_level_21",
        "level_2020": "npi_level_20",
        "level_2019": "npi_level_19",
        "level_2018": "npi_level_18",
        "level_2017": "npi_level_17",
        "level_2016": "npi_level_16",
        "level_2015": "npi_level_15",
        "conference_proceedings": "is_conference",
        "series": "is_series",
    }
    df = df.rename({k: v for k, v in rename.items() if k in df.columns})
    for col in [*NPI_FIELDS, "print_issn", "online_issn"]:
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))

    df = (
        df.with_columns(
            pl.concat_list([pl.col("print_issn").cast(pl.Utf8), pl.col("online_issn").cast(pl.Utf8)]).alias(
                "issn_parts"
            )
        )
        .explode("issn_parts")
        .with_columns(issn_expr(pl.col("issn_parts")).alias("issn_linking"))
        .filter(pl.col("issn_linking") != "")
        .select(NPI_FIELDS)
    )
    return write_frame(output, first_by_key(df, "issn_linking"))
