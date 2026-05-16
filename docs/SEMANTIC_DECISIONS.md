# Semantic Decisions

This document records intentional differences between the active Python pipeline and legacy outputs.

## Expected Corrections

- Missing `article_date` with a usable `pubdate` is retained for `publication_delay`; differential validation classifies new-only rows with `publication_date_source=pubdate` as `expected_correction`.
- Journals ceased before the article publication year are dropped; differential validation classifies legacy-only rows marked `ceased_before_publication=true` as `expected_correction`.

All other new-only or legacy-only rows are classified as `potential_migration_bug` until a narrower predicate is added and tested.
