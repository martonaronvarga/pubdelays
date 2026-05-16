from __future__ import annotations

from pathlib import Path

import polars as pl

from pubdelays.cli import main
from pubdelays.validation import compare_legacy_outputs


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    pl.DataFrame(rows).write_csv(path)


def test_compare_legacy_classifies_expected_corrections_and_bugs(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.csv"
    new = tmp_path / "new.csv"
    output = tmp_path / "report.csv"
    base = {
        "doi": "10.same",
        "pmid": "1",
        "title": "Same",
        "journal": "J",
        "issn_linking": "12345678",
        "received": "2020-01-01",
        "accepted": "2020-02-01",
        "article_date": "2020-03-01",
        "publication_date_source": "article_date",
        "acceptance_delay": "31",
        "publication_delay": "29",
        "ceased_before_publication": "",
    }
    write_csv(
        legacy,
        [
            base,
            {**base, "doi": "10.ceased", "title": "Ceased", "ceased_before_publication": "true"},
            {**base, "doi": "10.bug", "title": "Legacy only"},
        ],
    )
    write_csv(
        new,
        [
            base,
            {
                **base,
                "doi": "10.fallback",
                "title": "Fallback",
                "article_date": "2020-03-01",
                "publication_date_source": "pubdate",
            },
        ],
    )

    result = compare_legacy_outputs(legacy, new, output)
    report = pl.read_csv(output, infer_schema=False)

    assert result.categories["expected_correction"] == 2
    assert result.categories["potential_migration_bug"] == 1
    assert set(report["category"]) >= {"expected_correction", "potential_migration_bug"}


def test_compare_legacy_cli_writes_report(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.csv"
    new = tmp_path / "new.csv"
    output = tmp_path / "validation/report.csv"
    write_csv(legacy, [{"doi": "10.same", "title": "Same"}])
    write_csv(new, [{"doi": "10.same", "title": "Same"}])

    code = main(["compare-legacy", "--legacy", str(legacy), "--new", str(new), "--output", str(output)])

    assert code == 0
    assert output.exists()
    assert pl.read_csv(output, infer_schema=False)["category"].to_list() == ["ok"]
