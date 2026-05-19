# Analysis Dataset V1

`analysis_dataset_v1` is the public schema for `data/processed_data/processed.parquet` and `data/processed_data/processed.csv`.

All exported columns are stored as strings for CSV/Parquet interoperability. Boolean flags use the string values `True` and `False`; missing text, dates, and unavailable numeric metadata use the empty string. Delay columns are integer day counts encoded as strings.

Schema changes require a version bump or an explicit migration note in `docs/SEMANTIC_DECISIONS.md` and tests that update `CANONICAL_ARTICLE_COLUMNS` deliberately.

| Column | Group | Meaning | Units / values |
| --- | --- | --- | --- |
| `is_covid` | flags | Article title/keyword COVID synonym flag. | `True`/`False` |
| `received` | dates | Manuscript received date from PubMed history. | ISO date |
| `article_date` | dates | Publication date used for publication delay. | ISO date |
| `article_date_raw` | dates | Raw ArticleDate-derived date before retraction correction. | ISO date or empty |
| `publication_date_source` | dates | Source for `article_date`. | `article_date`, `pubdate`, or empty |
| `acceptance_delay` | outcomes | Accepted minus received. | days |
| `is_psych` | flags | First ASJC code is in the psychology range. | `True`/`False` |
| `is_mega` | flags | Linking ISSN is in the configured megajournal set. | `True`/`False` |
| `issn_linking` | identifiers | Normalized PubMed linking ISSN. | ISSN without punctuation |
| `h_index_year` | journal metadata | Scimago h-index for the article year. | integer string |
| `open_access` | external enrichment | Open-access flag from DOAJ, WoS, or NPI evidence. | `True`/`False` |
| `publication_delay` | outcomes | Publication date minus accepted date. | days |
| `publication_types` | article metadata | PubMed publication type labels. | semicolon/text |
| `title` | identifiers | Article title. | text |
| `journal` | identifiers | Journal title from PubMed. | text |
| `quartile_year` | journal metadata | Scimago quartile for the article year. | `Q1`-`Q4` or empty |
| `rank_year` | journal metadata | Scimago rank for the article year. | integer string |
| `discipline` | field classification | First WoS-derived umbrella discipline. | text |
| `asjc` | field classification | First WoS ASJC code. | code string |
| `discipline_all` | field classification | All WoS-derived umbrella disciplines. | pipe-delimited text |
| `asjc_all` | field classification | All WoS ASJC codes for the journal. | pipe-delimited code strings |
| `scimago_categories` | field classification | Scimago categories from current-year metadata. | pipe-delimited text |
| `publisher` | external enrichment | First non-empty publisher name for the ISSN. | text |
| `publisher_group` | external enrichment | First non-empty publisher group/parent. | text |
| `publisher_conflict` | external enrichment | Publisher rows disagree for the ISSN. | `True`/`False` or empty |
| `publisher_group_conflict` | external enrichment | Publisher-group rows disagree for the ISSN. | `True`/`False` or empty |
| `npi_discipline` | field classification | Norwegian Publication Indicator discipline. | text |
| `npi_field` | field classification | Norwegian Publication Indicator field. | text |
| `npi_year` | journal metadata | NPI level for the article year. | level string |
| `is_series` | journal metadata | NPI series flag. | source value |
| `established` | journal metadata | NPI established year. | year string |
| `country` | journal metadata | Journal country from external metadata. | text |
| `keywords` | article metadata | PubMed keyword text. | text |
| `apc` | external enrichment | DOAJ APC availability flag/value. | source value |
| `apc_amount` | external enrichment | DOAJ APC amount. | amount string |
| `doi` | identifiers | Normalized article DOI. | lowercase DOI |
| `retraction_nature` | retractions | Retraction Watch nature. | text |
| `reason` | retractions | Retraction Watch reason. | text |
| `retraction_date` | retractions | Retraction date. | ISO date or source date |
| `is_retracted` | retractions | Retraction evidence exists. | `True`/`False` |

Validate a produced dataset with:

```bash
pubdelays schema --input data/processed_data/processed.parquet
```
