from __future__ import annotations

from pathlib import Path

import polars as pl

from pubdelays.external import (
    preprocess_doaj,
    preprocess_npi,
    preprocess_retraction_watch,
    preprocess_wos,
)
from pubdelays.external.wos import discipline_for_asjc


def rows(path: Path) -> list[dict[str, object]]:
    return pl.read_csv(path).to_dicts()


def test_wos_preprocessor_splits_asjc_and_issn_then_keeps_first_issn(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "wos.csv"
    raw.write_text(
        "Source Title,Print-ISSN,E-ISSN,Source Type,All Science Journal Classification Codes (ASJC),Open Access status\n"
        "Journal A,1234-567X,2222-3333,Journal,3203; 1000,Unpaywall Open Acess\n"
        "Book A,9999-9999,,Book,3203,No\n",
        encoding="utf-8",
    )
    out = tmp_path / "web_of_science.csv"
    assert preprocess_wos(raw, out) == 2
    data = rows(out)
    assert data[0]["issn_linking"] == "1234567X"
    assert data[0]["asjc"] == 3203 or data[0]["asjc"] == "3203"
    assert data[0]["discipline"] == "social_sciences_and_humanities"
    assert data[1]["issn_linking"] == "22223333"


def test_npi_preprocessor_removes_issn_hyphens_and_splits_print_online(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "npi.csv"
    raw.write_text(
        "Original Title;Print ISSN;Online ISSN;Open Access;NPI Academic Discipline;NPI Scientific Field;"
        "Level 2025;Level 2024;Level 2023;Level 2022;Level 2021;Level 2020;Level 2019;Level 2018;Level 2017;Level 2016;Level 2015;"
        "Country of Publication;Language;Conference Proceedings;Series;Established;Ceased\n"
        "Journal A;1234-567X;8765-4321;DOAJ;Psychology;Psychology;2;1;1;1;1;1;1;1;1;1;1;NO;EN;0;0;1999;\n",
        encoding="utf-8",
    )
    out = tmp_path / "npi_out.csv"
    assert preprocess_npi(raw, out) == 2
    data = rows(out)
    assert data[0]["issn_linking"] == "1234567X"
    assert data[1]["issn_linking"] == "87654321"
    assert data[0]["npi_title"] == "Journal A"


def test_retraction_watch_preprocessor_filters_dates(tmp_path: Path) -> None:
    raw = tmp_path / "rw.csv"
    raw.write_text(
        "RetractionDate,OriginalPaperDate,Title,OriginalPaperDOI,RetractionDOI,RetractionNature,Reason\n"
        "01/02/2015 00:00,01/01/2013 00:00,Paper,10.1/x,10.1/r,Retraction,Error\n"
        "01/02/2014 00:00,01/01/2013 00:00,Old,10.1/y,10.1/ry,Retraction,Error\n",
        encoding="utf-8",
    )
    out = tmp_path / "rw_out.csv"
    assert preprocess_retraction_watch(raw, out) == 1
    data = rows(out)
    assert data[0]["doi"] == "10.1/x"
    assert str(data[0]["retraction_date"]) == "2015-01-02"


def test_wos_discipline_boundaries_match_legacy_case_when() -> None:
    assert discipline_for_asjc(1000) == "multidisciplinary"
    assert discipline_for_asjc(1111) == "life_sciences"
    assert discipline_for_asjc(3207) == "social_sciences_and_humanities"
    assert discipline_for_asjc(3616) == "health_sciences"


def test_doaj_preprocessor_matches_legacy_selected_columns(tmp_path: Path) -> None:
    raw = tmp_path / "doaj.csv"
    raw.write_text(
        "Journal title,Journal ISSN (print version),Journal EISSN (online version),Review process,APC,APC amount,Does the journal comply to DOAJ's definition of open access?,Ignored\n"
        "Journal A,1234-567X,8765-4321,Peer review,Yes,1000,Yes,x\n",
        encoding="utf-8",
    )
    out = tmp_path / "doaj_out.csv"
    assert preprocess_doaj(raw, out) == 2
    data = rows(out)
    assert data[0]["issn_linking"] == "1234567X"
    assert str(data[0]["apc_amount"]) == "1000"
    assert "ignored" not in data[0]
