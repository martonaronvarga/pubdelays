---
title: Terminology
description: Project-specific terms used throughout the documentation and CLI.
icon: octicons/book-16
---

# Terminology

| Term | Meaning |
| --- | --- |
| Baseline | PubMed baseline XML release files selected by `download --source baseline`. |
| Updatefiles | PubMed update XML files selected by `download --source updatefiles`. |
| Parsed shard | One JSONL/JSON output produced from one PubMed XML/XML.GZ input. |
| Article shard | A transformed canonical table produced by `transform-shard` or `transform-shards`. |
| Modulo sharding | Assignment rule where input line index `i` belongs to shard `i % shards`. |
| Manifest | SQLite audit database at `pipeline.manifest`, default `data/manifests/pipeline.sqlite`. |
| Stage | A CLI command or subcommand that performs a pipeline unit of work and may append manifest rows. |
| Lookup table | Processed external metadata CSV used by transform joins. |
| Canonical schema | Ordered `CANONICAL_ARTICLE_COLUMNS` tuple in `src/pubdelays/schema.py`. |
| Complete output | An expected output that exists, is non-empty, and represents a whole stage product. |

Use [stage contracts](../internals/stage-contracts.md) for command-specific definitions of inputs, outputs, and row counts.
