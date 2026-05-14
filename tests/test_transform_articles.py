from __future__ import annotations

import csv
import json
from pathlib import Path

from pubdelays.transform import ExternalInputs, transform_files


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_transform_files_counts_filters_and_enriches(tmp_path: Path) -> None:
    records = [
        {
            "title": "Fast COVID replication study",
            "journal": "Example Journal",
            "pubdate": "2020-03-01",
            "article_date": "2020-02-01",
            "history": {
                "received": "2019-12-15",
                "accepted": "2020-01-15",
                "pubmed": "2020-02-03",
            },
            "publication_types": "D016428:Journal Article",
            "issn_linking": "1234-567X",
            "keywords": "covid;replication",
            "doi": "https://doi.org/10.1000/example",
            "pmid": "1",
            "delete": False,
        },
        {
            "title": "Impossible timing",
            "journal": "Example Journal",
            "pubdate": "2020-03-01",
            "article_date": "2020-02-01",
            "history": {"received": "2020-01-20", "accepted": "2020-01-10"},
            "publication_types": "D016428:Journal Article",
            "issn_linking": "1234-567X",
            "keywords": "",
            "doi": "10.1000/bad",
            "pmid": "2",
            "delete": False,
        },
    ]
    parsed = tmp_path / "parsed.jsonl"
    parsed.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )

    scimago = tmp_path / "scimago.csv"
    write_csv(
        scimago,
        [
            {
                "issn_linking": "1234567X",
                "asjc": "3203",
                "quartile_2020": "Q1",
                "rank_2020": "10",
                "h_index_2020": "50",
                "is_conference": "0",
                "ceased": "",
                "discipline": "Psychology",
                "is_series": "0",
                "established": "1999",
                "country": "United Kingdom",
                "apc": "Yes",
                "apc_amount": "1000",
            }
        ],
    )
    doaj = tmp_path / "doaj.csv"
    write_csv(
        doaj,
        [
            {
                "issn_linking": "1234567X",
                "Does the journal comply to DOAJ's definition of open access?": "Yes",
            }
        ],
    )
    retractions = tmp_path / "retraction_watch.csv"
    write_csv(
        retractions,
        [
            {
                "doi": "10.1000/example",
                "retraction_doi": "",
                "reason": "Error",
                "retraction_nature": "Retraction",
                "retraction_date": "2021-01-01",
                "original_date": "2020-02-02",
            }
        ],
    )

    output = tmp_path / "articles.tsv"
    filters = tmp_path / "filters.csv"
    result = transform_files(
        parsed,
        output,
        filters_path=filters,
        external=ExternalInputs(
            scimago=scimago, doaj=doaj, retraction_watch=retractions
        ),
    )

    assert result.counts["raw_records"] == 2
    assert result.counts["coherent_dates"] == 1
    assert result.counts["final_rows"] == 1

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 1
    row = rows[0]
    assert row["acceptance_delay"] == "31"
    assert row["publication_delay"] == "17"
    assert row["is_covid"] == "True"
    assert row["is_replication"] == "True"
    assert row["is_retracted"] == "True"
    assert row["article_date"] == "2020-02-02"
    assert row["is_psych"] == "True"
    assert row["quartile_year"] == "Q1"
    assert row["open_access"] == "True"

    with filters.open("r", encoding="utf-8", newline="") as handle:
        filter_rows = list(csv.DictReader(handle))
    assert {row["stage"] for row in filter_rows} >= {"raw_records", "final_rows"}
