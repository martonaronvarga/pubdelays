from __future__ import annotations

from pathlib import Path

import polars as pl

from pubdelays.schema import CANONICAL_ARTICLE_COLUMNS
from pubdelays.summaries import derive_summary_tables


def canonical_row(**updates: str) -> dict[str, str]:
    row = {column: "" for column in CANONICAL_ARTICLE_COLUMNS}
    row.update(
        {
            "journal": "Example Journal",
            "issn_linking": "12345678",
            "discipline": "health_sciences",
            "publisher": "Example Publisher",
            "publisher_group": "Example Group",
            "article_date": "2020-02-01",
            "acceptance_delay": "31",
            "publication_delay": "17",
        }
    )
    row.update(updates)
    return row


def test_derive_summary_tables_from_processed_parquet(tmp_path: Path) -> None:
    processed = tmp_path / "processed.parquet"
    pl.DataFrame(
        [
            canonical_row(title="A", publication_delay="17"),
            canonical_row(title="B", publication_delay="19"),
            canonical_row(
                title="C",
                journal="Other Journal",
                issn_linking="87654321",
                discipline="social_sciences_and_humanities",
                publisher="",
                publisher_group="",
                article_date="2021-03-01",
                publication_delay="40",
            ),
        ]
    ).write_parquet(processed)

    outputs = derive_summary_tables(processed, tmp_path / "summaries")

    assert set(outputs) == {"journal_year", "field_year", "publisher_year", "delay_distribution"}
    journal = pl.read_csv(outputs["journal_year"], infer_schema=False)
    assert journal.filter(pl.col("journal") == "Example Journal")["articles"].item() == "2"
    publisher = pl.read_csv(outputs["publisher_year"], infer_schema=False)
    assert publisher.height == 1
    assert publisher["publisher"].to_list() == ["Example Publisher"]
    distribution = pl.read_csv(outputs["delay_distribution"], infer_schema=False)
    assert set(distribution["article_year"].to_list()) == {"2020", "2021"}
