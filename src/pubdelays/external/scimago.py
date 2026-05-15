"""Scimago Journal Rank preprocessing, implemented with Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from .common import first_by_key, issn_expr, normalize_columns, read_csv_polars, write_frame

SCIMAGO_FIELDS = [
    "issn_linking",
    "quartile_2024",
    "h_index_2024",
    "journal_title",
    "rank_2024",
    "sjr_2024",
    "quartile_2015",
    "h_index_2015",
    "rank_2015",
    "sjr_2015",
    "quartile_2016",
    "h_index_2016",
    "rank_2016",
    "sjr_2016",
    "quartile_2017",
    "h_index_2017",
    "rank_2017",
    "sjr_2017",
    "quartile_2018",
    "h_index_2018",
    "rank_2018",
    "sjr_2018",
    "quartile_2019",
    "h_index_2019",
    "rank_2019",
    "sjr_2019",
    "quartile_2020",
    "h_index_2020",
    "rank_2020",
    "sjr_2020",
    "quartile_2021",
    "h_index_2021",
    "rank_2021",
    "sjr_2021",
    "quartile_2022",
    "h_index_2022",
    "rank_2022",
    "sjr_2022",
    "quartile_2023",
    "h_index_2023",
    "rank_2023",
    "sjr_2023",
]


def _read_scimago_file(path: Path, year: int) -> pl.DataFrame:
    df = normalize_columns(read_csv_polars(path, separator=";"))
    required = ["title", "issn", "sjr_best_quartile", "h_index", "rank", "sjr"]
    for col in required:
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))

    df = (
        df.select(required)
        .with_columns(pl.col("issn").cast(pl.Utf8).str.split(",").alias("issn_parts"))
        .explode("issn_parts")
        .with_columns(issn_expr(pl.col("issn_parts")).alias("issn_linking"))
        .filter(pl.col("issn_linking") != "")
    )

    if year == 2024:
        return df.select(
            "issn_linking",
            pl.col("sjr_best_quartile").alias("quartile_2024"),
            pl.col("h_index").alias("h_index_2024"),
            pl.col("title").alias("journal_title"),
            pl.col("rank").alias("rank_2024"),
            pl.col("sjr").alias("sjr_2024"),
        )
    return df.select(
        "issn_linking",
        pl.col("sjr_best_quartile").alias(f"quartile_{year}"),
        pl.col("h_index").alias(f"h_index_{year}"),
        pl.col("rank").alias(f"rank_{year}"),
        pl.col("sjr").alias(f"sjr_{year}"),
    )


def preprocess_scimago(input_dir: Path, output: Path, *, start_year: int = 2015, end_year: int = 2024) -> int:
    input_dir = Path(input_dir)
    scimago = _read_scimago_file(input_dir / f"scimagojr {end_year}.csv", end_year)
    scimago = first_by_key(
        scimago.filter(pl.col("quartile_2024").is_not_null() & (pl.col("quartile_2024") != "")),
        "issn_linking",
    )

    for year in range(start_year, end_year):
        year_df = first_by_key(_read_scimago_file(input_dir / f"scimagojr {year}.csv", year), "issn_linking")
        scimago = scimago.join(year_df, on="issn_linking", how="left")

    for col in SCIMAGO_FIELDS:
        if col not in scimago.columns:
            scimago = scimago.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))
    scimago = scimago.select(SCIMAGO_FIELDS).with_columns(
        [
            pl.col(col).cast(pl.Utf8, strict=False).fill_null("").replace({"-": "", "NA": "", "_": ""})
            for col in SCIMAGO_FIELDS
        ]
    )
    return write_frame(output, scimago)
