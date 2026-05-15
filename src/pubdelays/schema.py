"""Canonical schema constants for the publication-delay pipeline.

The active schema is legacy-compatible with ``process_data.R`` and
``aggregate.R``: column order and inclusion semantics match the old TSV files,
while the implementation is now Python-first, resumable, and auditable.
"""

from __future__ import annotations

REQUIRED_PARSED_FIELDS: tuple[str, ...] = (
    "history",
    "journal",
    "pubdate",
    "publication_types",
    "issn_linking",
)

FILTER_STAGES: tuple[str, ...] = (
    "raw_records",
    "non_deleted_records",
    "has_required_parsed_fields",
    "has_received_and_accepted_dates",
    "journal_articles",
    "has_linking_issn",
    "coherent_dates",
    "nonnegative_delays",
    "after_external_joins",
    "eligible_journal_metadata",
    "distinct_titles",
    "final_rows",
)

# Exact legacy article TSV schema selected by process_data.R before aggregate.R
# binds rows and writes processed.csv.
CANONICAL_ARTICLE_COLUMNS: tuple[str, ...] = (
    "is_covid",
    "received",
    "article_date",
    "article_date_raw",
    "publication_date_source",
    "acceptance_delay",
    "is_psych",
    "is_mega",
    "issn_linking",
    "h_index_year",
    "open_access",
    "publication_delay",
    "publication_types",
    "title",
    "journal",
    "quartile_year",
    "rank_year",
    "discipline",
    "asjc",
    "npi_discipline",
    "npi_field",
    "npi_year",
    "is_series",
    "established",
    "country",
    "keywords",
    "apc",
    "apc_amount",
    "doi",
    "retraction_nature",
    "reason",
    "retraction_date",
    "is_retracted",
)

COVID_SYNONYMS: tuple[str, ...] = (
    "covid",
    "covid-19",
    "coronavirus disease 19",
    "sars-cov-2",
    "2019-ncov",
    "2019ncov",
    "2019-n-cov",
    "2019n-cov",
    "ncov-2019",
    "n-cov-2019",
    "coronavirus-2019",
    "wuhan pneumonia",
    "wuhan virus",
    "wuhan coronavirus",
    "coronavirus 2",
)

REPLICATION_SYNONYMS: tuple[str, ...] = (
    "replication",
    "replicating",
    "replication of",
    "replication study",
)

MEGAJOURNAL_ISSNS: frozenset[str] = frozenset(
    {
        "24701343",
        "21583226",
        "20466390",
        "20446055",
        "23251026",
        "22115463",
        "21601836",
        "21693536",
        "20513305",
        "21678359",
        "19326203",
        "20545703",
        "21582440",
        "20452322",
        "20566700",
        "23915447",
        "22991093",
        "24058440",
        "21508925",
        "2050084X",
        "20461402",
    }
)
