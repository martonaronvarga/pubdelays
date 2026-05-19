# Legacy Semantics

Legacy migration notes are maintained in `LEGACY.md` at the repository root.

The active implementation ports the old shell, Python, and R pipeline into Python modules under `src/pubdelays/` while preserving documented data semantics. Intentional corrections are documented there, including article-date fallback behavior and ceased-journal filtering by article publication year.
