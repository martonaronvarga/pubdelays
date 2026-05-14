"""Transform parse PubMed/MEDLINE records into pubdelay analysis rows.

This module ports the substantive filtering and enrichment logic from process_data.R
into small, named, testable operations.
It is intentionally conservative: parser semantics remain separate from study
selection semantics, and every major filter stage is counted.
"""

from __future__ import annotations
import csv
import json
import re
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pubdelays.schema import (
    CANONICAL_ARTICLE_COLUMNS,
    COVID_SYNONYMS,
    FILTER_STAGES,
    MEGAJOURNAL_ISSNS,
    REPLICATION_SYNONYMS,
    REQUIRED_PARSED_FIELDS,
)

JsonRecord = dict[str, Any]
Row = dict[str, Any]


@dataclass(frozen=True)
class ExternalInputs:
    """Optional enrichment tables used by the transformation step."""

    scimago: Path | None = None
    web_of_science: Path | None = None
    doaj: Path | None = None
    norwegian_list: Path | None = None
    retraction_watch: Path | None = None


@dataclass(frozen=True)
class TransformResult:
    output_path: Path
    filters_path: Path | None
    counts: Mapping[str, int]


def normalize_header(name: str) -> str:
    """Convert external CSV headers to snake_case names."""

    normalized = name.strip().lower()
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def normalize_issn(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^0-9Xx]", "", str(value)).upper()


def normalize_doi(value: Any) -> str:
    if value is None:
        return ""
    doi = str(value).strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.strip()


def parse_date(value: Any) -> date | None:
    """Parse PubMed dates in YYYY, YYYY-MM, or YYYY-MM-DD form.

    This mirrors the old R/lubridate behavior used for PubMed dates by filling
    missing month/day components with ``01``.
    """

    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"na", "nan", "none", "null"}:
        return None

    match = re.match(
        r"^(?P<year>\d{4})(?:-(?P<month>\d{1,2})(?:-(?P<day>\d{1,2}))?)?$", text
    )
    if not match:
        return None
    year = int(match.group("year"))
    month = int(match.group("month") or 1)
    day = int(match.group("day") or 1)
    try:
        return date(year, month, day)
    except ValueError:
        return None


def iso(value: date | None) -> str:
    return value.isoformat() if value else ""


def coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def publication_type_labels(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    labels: list[str] = []
    for part in re.split(r";\s*", text):
        if not part:
            continue
        labels.append(part.split(":", 1)[1].strip() if ":" in part else part.strip())
    return ", ".join(label for label in labels if label)


def contains_any_term(text: str, terms: Iterable[str]) -> bool:
    haystack = text or ""
    for term in terms:
        if re.search(rf"\b{re.escape(term)}\b", haystack, flags=re.IGNORECASE):
            return True
    return False


def flatten_history(record: JsonRecord) -> Row:
    row: Row = dict(record)
    history = record.get("history")
    if isinstance(history, dict):
        row.update(history)
    elif isinstance(history, list):
        # Defensive support for JSON encoders that materialize a singleton
        # history object as a one-element list.
        for item in history:
            if isinstance(item, dict):
                row.update(item)
    return row


def iter_json_records(path: Path) -> Iterator[JsonRecord]:
    if path.suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    value = json.loads(line)
                    if isinstance(value, dict):
                        yield value
        return

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
    elif isinstance(value, dict):
        yield value


def iter_input_paths(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        return sorted(
            list(input_path.rglob("*.jsonl")) + list(input_path.rglob("*.json"))
        )
    return [input_path]


def read_csv_rows(path: Path | None) -> list[Row]:
    if path is None or not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                normalize_header(key): value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def candidate_issns(row: Mapping[str, Any]) -> set[str]:
    keys = (
        "issn_linking",
        "issn",
        "issn_print",
        "issn_online",
        "eissn",
        "pissn",
        "print_issn",
        "online_issn",
    )
    values: set[str] = set()
    for key in keys:
        raw = row.get(key)
        if raw is None:
            continue
        for part in re.split(r"[,;/|]\s*", str(raw)):
            issn = normalize_issn(part)
            if issn:
                values.add(issn)
    return values


def index_by_issn(rows: Iterable[Row]) -> dict[str, list[Row]]:
    index: dict[str, list[Row]] = {}
    for row in rows:
        for issn in candidate_issns(row):
            index.setdefault(issn, []).append(row)
    return index


def index_retractions(rows: Iterable[Row]) -> dict[str, Row]:
    index: dict[str, Row] = {}
    for row in rows:
        for key in ("doi", "retraction_doi"):
            doi = normalize_doi(row.get(key))
            if doi and doi not in index:
                index[doi] = row
    return index


def merge_external(row: Row, incoming: Mapping[str, Any], source: str) -> Row:
    merged = dict(row)
    for key, value in incoming.items():
        if key in {"issn", "issn_linking", "issn_print", "issn_online"}:
            continue
        if key not in merged or merged[key] in {None, ""}:
            merged[key] = value
        else:
            merged[f"{key}_{source}"] = value
    return merged


def left_join_issn(
    rows: Iterable[Row], index: Mapping[str, list[Row]], source: str
) -> Iterator[Row]:
    for row in rows:
        issn = normalize_issn(row.get("issn_linking"))
        matches = index.get(issn)
        if not matches:
            yield row
            continue
        for match in matches:
            yield merge_external(row, match, source)


def value_for_year(row: Mapping[str, Any], prefix: str, year: int | None) -> Any:
    if year is None:
        return ""
    table_year = 2024 if year >= 2025 else year
    keys = [f"{prefix}_{table_year}"]
    if prefix == "npi_level":
        keys.append(f"npi_level_{str(table_year)[-2:]}")
    for key in keys:
        value = row.get(key)
        if value not in {None, ""}:
            return value
    return ""


def is_psychology_asjc(value: Any) -> bool:
    if value is None:
        return False
    for token in re.findall(r"\d+", str(value)):
        code = coerce_int(token)
        if code is not None and 3200 <= code <= 3207:
            return True
    return False


def compute_open_access(row: Mapping[str, Any]) -> bool:
    doaj_value = str(
        row.get("does_the_journal_comply_to_doaj_s_definition_of_open_access", "")
    ).strip()
    wos_value = str(row.get("open_access_status", "")).strip()
    npi_value = str(row.get("npi_open_access", "")).strip()
    return (
        doaj_value.lower() == "yes"
        or wos_value in {"Unpaywall Open Acess", "Unpaywall Open Access"}
        or npi_value.upper() == "DOAJ"
    )


def journal_metadata_eligible(row: Mapping[str, Any], min_received: date) -> bool:
    ceased = coerce_int(row.get("ceased"))
    is_conference = coerce_int(row.get("is_conference"))
    received = parse_date(row.get("received"))
    ceased_ok = ceased is None or ceased <= 2014
    conference_ok = is_conference == 0
    received_ok = received is not None and received >= min_received
    return ceased_ok and conference_ok and received_ok


def first_stage_record(record: JsonRecord, counts: Counter[str]) -> Row | None:
    counts["raw_records"] += 1
    if record.get("delete"):
        return None
    counts["non_deleted_records"] += 1

    if any(field not in record for field in REQUIRED_PARSED_FIELDS):
        return None
    counts["has_required_parsed_fields"] += 1

    row = flatten_history(record)
    row["publication_types"] = publication_type_labels(row.get("publication_types"))
    row["keywords"] = str(row.get("keywords") or "").replace(";", ",")
    row["issn_linking"] = normalize_issn(row.get("issn_linking"))
    row["doi"] = normalize_doi(row.get("doi"))

    received = parse_date(row.get("received"))
    accepted = parse_date(row.get("accepted"))
    pubdate = parse_date(row.get("pubdate"))
    article_dt = parse_date(row.get("article_date"))

    if received is None or accepted is None:
        return None
    counts["has_received_and_accepted_dates"] += 1

    if "Journal Article" not in row["publication_types"]:
        return None
    counts["journal_articles"] += 1

    if not row["issn_linking"]:
        return None
    counts["has_linking_issn"] += 1

    # This intentionally mirrors the old R filter, which effectively required
    # article_date to be present before computing the fallback publication delay.
    if (
        article_dt is None
        or received >= article_dt
        or accepted >= article_dt
        or accepted <= received
    ):
        return None
    counts["coherent_dates"] += 1

    acceptance_delay = (accepted - received).days
    publication_delay = (
        (article_dt - accepted).days
        if article_dt
        else ((pubdate - accepted).days if pubdate else None)
    )
    if publication_delay is None or acceptance_delay < 0 or publication_delay < 0:
        return None
    counts["nonnegative_delays"] += 1

    text_for_flags = " ".join(
        [str(row.get("title") or ""), str(row.get("keywords") or "")]
    )
    row.update(
        {
            "received": iso(received),
            "accepted": iso(accepted),
            "pubdate": iso(pubdate),
            "article_date": iso(article_dt),
            "acceptance_delay": acceptance_delay,
            "publication_delay": publication_delay,
            "is_covid": contains_any_term(text_for_flags, COVID_SYNONYMS),
            "is_replication": contains_any_term(text_for_flags, REPLICATION_SYNONYMS),
        }
    )
    return row


def enrich_rows(rows: Iterable[Row], external: ExternalInputs) -> Iterator[Row]:
    joined: Iterable[Row] = rows
    for source, path in (
        ("scimago", external.scimago),
        ("wos", external.web_of_science),
        ("doaj", external.doaj),
        ("npi", external.norwegian_list),
    ):
        index = index_by_issn(read_csv_rows(path))
        if index:
            joined = left_join_issn(joined, index, source)
    yield from joined


def finalize_row(row: Row, retractions: Mapping[str, Row]) -> Row:
    article_dt = parse_date(row.get("article_date"))
    article_year = article_dt.year if article_dt else None

    row["quartile_year"] = value_for_year(row, "quartile", article_year)
    row["npi_year"] = value_for_year(row, "npi_level", article_year)
    row["rank_year"] = value_for_year(row, "rank", article_year)
    row["h_index_year"] = value_for_year(row, "h_index", article_year)
    row["is_psych"] = is_psychology_asjc(row.get("asjc"))
    row["is_mega"] = normalize_issn(row.get("issn_linking")) in MEGAJOURNAL_ISSNS
    row["open_access"] = compute_open_access(row)

    retraction = retractions.get(normalize_doi(row.get("doi")))
    row["is_retracted"] = retraction is not None and (
        bool(retraction.get("reason"))
        or bool(retraction.get("retraction_nature"))
        or bool(retraction.get("retraction_date"))
    )
    if retraction is not None:
        original_date = parse_date(retraction.get("original_date"))
        if original_date is not None:
            row["article_date"] = iso(original_date)

    return {column: row.get(column, "") for column in CANONICAL_ARTICLE_COLUMNS}


def transform_files(
    input_path: Path,
    output_path: Path,
    *,
    filters_path: Path | None = None,
    external: ExternalInputs | None = None,
    min_received: date = date(2013, 1, 1),
) -> TransformResult:
    external = external or ExternalInputs()
    counts: Counter[str] = Counter({stage: 0 for stage in FILTER_STAGES})
    paths = iter_input_paths(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if filters_path is not None:
        filters_path.parent.mkdir(parents=True, exist_ok=True)

    retractions = index_retractions(read_csv_rows(external.retraction_watch))
    seen_titles: set[str] = set()

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(CANONICAL_ARTICLE_COLUMNS), delimiter="\t"
        )
        writer.writeheader()

        for path in paths:
            first_stage = (
                row
                for record in iter_json_records(path)
                if (row := first_stage_record(record, counts)) is not None
            )
            for row in enrich_rows(first_stage, external):
                counts["after_external_joins"] += 1
                if not journal_metadata_eligible(row, min_received):
                    continue
                counts["eligible_journal_metadata"] += 1

                title_key = str(row.get("title") or "").strip().casefold()
                if not title_key or title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                counts["distinct_titles"] += 1

                writer.writerow(finalize_row(row, retractions))
                counts["final_rows"] += 1

    if filters_path is not None:
        with filters_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["stage", "count"])
            writer.writeheader()
            for stage in FILTER_STAGES:
                writer.writerow({"stage": stage, "count": counts[stage]})

    return TransformResult(
        output_path=output_path, filters_path=filters_path, counts=dict(counts)
    )
