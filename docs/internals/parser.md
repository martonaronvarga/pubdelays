---
title: Parser internals
description: Streaming MEDLINE XML parser behavior, options, and edge cases.
icon: octicons/file-code-16
---

# Parser internals

The parser implementation lives in `src/pubdelays/parser/medline.py`. It is used by `parse-one` and `parse` through `parse_medline_xml()`.

## Input and output

- Inputs are PubMed `.xml` or `.xml.gz` files.
- `parse_medline_xml()` yields one dictionary at a time; it does not materialize the full baseline.
- `parse-one` writes `.jsonl` or `.json`; JSONL is preferred for full-scale runs.
- `DeleteCitation` records are emitted with deletion metadata so downstream counts can distinguish removed citations from ordinary articles.

## Date extraction

Parser output includes PubMed history dates such as `received` and `accepted`, journal `pubdate`, and optional `article_date`. Transform decides publication-date fallback and delay filtering; parser extraction should avoid embedding transform policy.

## Options exposed by the CLI

Common parse options include:

```bash
pubdelays parse --format jsonl --parse-mesh-subterms --resume
pubdelays parse-one input.xml.gz output.jsonl --recover-malformed-xml
```

`--recover-malformed-xml` opts into lxml recovery mode. Keep strict parsing as the default for normal production runs.

## Tests

Parser behavior is covered by `tests/test_medline_parser.py` and end-to-end fixtures in `tests/test_end_to_end_pipeline.py`, including normal articles, missing `ArticleDate`, `DeleteCitation`, DOI extraction, publication types, ISSN linking, and MeSH behavior.
