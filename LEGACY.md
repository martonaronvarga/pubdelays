# Legacy migration notes

The historical pipeline mixed shell scripts, patched `pubmed_parser`, Python JSON conversion, and R/dplyr scripts. The active implementation ports the behavior into `src/pubdelays/` and removes the old execution path.

## Ported stages

| Legacy file | Active implementation |
| --- | --- |
| `xmls2json.py` + patched `medline_parser.py` | `src/pubdelays/parser/medline.py` and `pubdelays-pipeline parse` |
| `scimago.R` | `src/pubdelays/external/scimago.py` |
| `wos.R` | `src/pubdelays/external/wos.py` |
| `doaj.R` | `src/pubdelays/external/doaj.py` |
| `npi.R` | `src/pubdelays/external/npi.py` |
| `retraction_watch.R` | `src/pubdelays/external/retraction_watch.py` |
| `process_data.R` | `src/pubdelays/transform/articles.py` |
| `aggregate.R` | `src/pubdelays/aggregate.py` |

## Intended semantic preservation

The active transform preserves the old high-level sequence:

1. unnest MEDLINE/PubMed history dates;
2. require received and accepted dates;
3. keep publication type `Journal Article`;
4. normalize linking ISSN by removing punctuation and uppercasing `X`;
5. require coherent dates: `received < accepted < publication_date`;
6. compute acceptance and publication delays in days;
7. join Scimago, Web of Science, DOAJ, and NPI by `issn_linking`;
8. choose year-specific Scimago/NPI metadata using article publication year, with 2025 falling back to 2024 Scimago/NPI metadata;
9. mark psychology, megajournal, open-access, COVID, and retraction flags;
10. keep the first article per title.

## Intentional corrections

Two legacy defects are deliberately corrected:

1. If `article_date` is missing, `pubdate` is now allowed to supply the publication date for `publication_delay`. Legacy R filtered on `article_date` before its own `pubdate` fallback could contribute.
2. Ceased journals are filtered against the article publication year. Legacy `ceased = is.numeric(ceased)` destroyed the ceased-year information before filtering.

