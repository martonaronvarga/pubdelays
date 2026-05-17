# Semantic Decisions

This document records intentional differences between the active Python pipeline and legacy outputs.

## Expected Corrections

- Missing `article_date` with a usable `pubdate` is retained for `publication_delay`; differential validation classifies new-only rows with `publication_date_source=pubdate` as `expected_correction`.
- Journals ceased before the article publication year are dropped; differential validation classifies legacy-only rows marked `ceased_before_publication=true` as `expected_correction`.

All other new-only or legacy-only rows are classified as `potential_migration_bug` until a narrower predicate is added and tested.

## Article Filtering Contract

Transform filter counts expose every row-dropping gate in order: raw records, non-deleted records, required parsed fields, received/accepted dates, journal-article publication type, linking ISSN, coherent dates, nonnegative delays, external joins, eligible journal metadata, distinct titles, and final rows.

Missing external metadata is not a row-dropping condition. Missing Scimago/WoS/DOAJ/NPI/Retraction Watch values remain explicit empty strings or `False` categorical flags in canonical output columns.

The legacy spelling `Unpaywall Open Acess` is retained only as an accepted raw WoS category while deriving the canonical boolean `open_access`; final outputs do not expose that misspelling as a schema value.

## Subject Classification Contract

The legacy scalar `asjc` and `discipline` columns remain first-category compatibility fields. The pipeline also preserves ordered, pipe-delimited `asjc_all`, `discipline_all`, and `scimago_categories` columns so multi-category journals remain analyzable from Parquet, CSV, R, and Python without row explosion.

## Intermediate Format Contract

Parser output remains JSONL by default. JSONL is append-free, line-oriented, streaming-friendly, human-auditable, and cheap to regenerate into normalized article shards. The parser also supports JSON only for small fixtures or interoperability; it is not the full-corpus default because it materializes records in one array.

Transform output remains Parquet by default (`transform.article_shard_format = "parquet"`). Parquet is the canonical intermediate for filtered/enriched article shards and final analysis because it preserves schema order, reads quickly with Polars, and avoids repeated JSON parsing during aggregation. The pipeline does not emit a secondary parser-level Parquet product unless future benchmarks show the extra storage and audit complexity beats the current JSONL-audit plus Parquet-transform split.
