"""Canonical data locations used by documentation and preflight checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pubdelays.config import PipelineConfig


@dataclass(frozen=True)
class ExpectedPath:
    label: str
    path: Path
    kind: str
    required: bool
    description: str


def expected_input_paths(config: PipelineConfig) -> list[ExpectedPath]:
    return [
        ExpectedPath(
            "PubMed XML baseline/update files",
            config.path("pubmed.xml_dir"),
            "dir",
            True,
            "Put .xml.gz files from NCBI PubMed baseline/updatefiles here; keep .md5 sidecars when available.",
        ),
        ExpectedPath(
            "Scimago yearly CSV directory",
            config.path("external.raw.scimago_dir"),
            "dir",
            True,
            "Contains files named exactly like 'scimagojr 2015.csv' ... 'scimagojr 2024.csv'.",
        ),
        ExpectedPath(
            "Web of Science raw CSV",
            config.path("external.raw.web_of_science_csv"),
            "file",
            True,
            "Raw WOS export with Print-ISSN, E-ISSN, Source Type, and ASJC columns.",
        ),
        ExpectedPath(
            "DOAJ raw CSV",
            config.path("external.raw.doaj_csv"),
            "file",
            True,
            "Raw DOAJ journal CSV export.",
        ),
        ExpectedPath(
            "Norwegian Publication Indicator raw CSV",
            config.path("external.raw.norwegian_list_csv"),
            "file",
            True,
            "Raw semicolon-separated NPI journal list.",
        ),
        ExpectedPath(
            "Retraction Watch raw CSV",
            config.path("external.raw.retraction_watch_csv"),
            "file",
            True,
            "Raw Retraction Watch CSV export.",
        ),
        ExpectedPath(
            "Publisher metadata raw CSV",
            config.path("external.raw.publisher_csv"),
            "file",
            False,
            "Optional publisher metadata keyed by linking ISSN.",
        ),
    ]


def expected_output_paths(config: PipelineConfig) -> list[ExpectedPath]:
    return [
        ExpectedPath(
            "parsed JSONL shards",
            config.path("pubmed.jsonl_dir"),
            "dir",
            False,
            "Generated.",
        ),
        ExpectedPath(
            "article Parquet shards",
            config.path("transform.article_shard_dir"),
            "dir",
            False,
            "Generated.",
        ),
        ExpectedPath(
            "processed Parquet",
            config.path("aggregate.processed_parquet"),
            "file",
            False,
            "Generated.",
        ),
        ExpectedPath(
            "processed CSV",
            config.path("aggregate.processed_csv"),
            "file",
            False,
            "Generated.",
        ),
        ExpectedPath(
            "derived summary tables",
            config.path("aggregate.summary_dir"),
            "dir",
            False,
            "Generated.",
        ),
        ExpectedPath(
            "manifest database",
            config.path("pipeline.manifest"),
            "file",
            False,
            "Generated SQLite WAL manifest.",
        ),
    ]
