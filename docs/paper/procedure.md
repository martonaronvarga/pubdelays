# Procedure

## Study design and unit of observation

We assembled a retrospective article-level cohort to study the interval from manuscript receipt to acceptance and the interval from acceptance to publication. The unit of observation was a PubMed citation representing a journal article. PMID was the principal article identifier. Two records with the same title remained distinct when their PMIDs differed. Records without a PMID were identified first by normalized DOI and, when both PMID and DOI were absent, by exact title. The study period for analysis was 1 January 2016 through 31 December 2025. Source material preceding 2016 was retained where needed to establish receipt dates, journal histories, and model-development covariates.

## Data sources

Table 1 gives the source, observational level, snapshot or coverage, join field, and contribution to the study dataset. Dates identify the snapshots specified for the study, not the period represented by every field in those snapshots.

**Table 1. Study data sources and their use**

| Source | Observational level | Study snapshot or coverage | Linkage field | Variables or evidence contributed |
| --- | --- | --- | --- | --- |
| [PubMed/MEDLINE](https://pubmed.ncbi.nlm.nih.gov/download/) | Article and journal | Baseline and update XML files current at cohort construction; analysis dates 2016 to 2025 | PMID; DOI and title only for exceptional records without PMID | Title, journal title, linking ISSN, publication types, keywords, DOI, receipt date, acceptance date, article date, journal-issue date, PMID |
| [SCImago Journal & Country Rank](https://www.scimagojr.com/journalrank.php) | Journal-year | Annual files, 2015 to 2025 | Linking ISSN | Annual H-index, SJR rank, quartile, and subject categories |
| [Scopus Source List](https://www.elsevier.com/products/scopus/content) | Journal | June 2026 licensed snapshot | Print or electronic ISSN, mapped to linking ISSN | Source type, open-access status, ASJC codes, and broad discipline |
| [Directory of Open Access Journals](https://doaj.org/) | Journal | 5 July 2026 public snapshot | Print or electronic ISSN, mapped to linking ISSN | DOAJ open-access evidence, review process, APC declaration, and APC amount text |
| [Norwegian Register](https://kanalregister.hkdir.no/) | Journal and journal-year | 5 August 2026 snapshot; annual levels for 2015 to 2025 | Print or online ISSN, mapped to linking ISSN | Academic discipline, scientific field, annual level, series status, establishment and cessation years, country, conference status, and DOAJ flag |
| [Retraction Watch Database](https://retractiondatabase.org/) | Article | Public snapshot current at cohort construction | Normalized DOI of the original article | Retraction nature, reason, notice date, original-paper date, and retraction status |
| Clarivate peer-review export | Review event and article | Lawfully supplied private February 2026 export; eligible review dates 1 January 2013 to 31 December 2025 | Normalized DOI | Review round, review-event date, and accepted-event date |
| [European Central Bank reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) | Currency-day | Historical daily rates | Currency and date | Primary conversion of APC quotations to euros |
| [European Commission InforEuro](https://commission.europa.eu/funding-tenders/procedures-guidelines-tenders/information-contractors-and-beneficiaries/exchange-rate-inforeuro_en) | Currency-month | Historical monthly rates | Currency and month | Fallback conversion of APC quotations to euros |

MEDLINE is the curated bibliographic component of PubMed and is not synonymous with the entire PubMed collection. PubMed also contains citations awaiting MEDLINE indexing and citations supplied by other National Library of Medicine resources. We therefore refer to the downloaded material as PubMed/MEDLINE XML and did not infer MEDLINE indexing status from presence in PubMed. Field interpretation followed the [National Library of Medicine PubMed XML specification](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/index.html).

The external sources represent different constructs. SCImago supplies citation-based journal indicators derived from Scopus. The Scopus Source List supplies source classifications and open-access status. DOAJ supplies registry evidence concerning immediate open access and publishing practices. The Norwegian Register supplies an expert-assessed national classification of publication channels, in which Level 1 denotes a recognized academic channel, Level 2 denotes the highest category, and Level 0 denotes a channel that does not meet or has not documented the criteria for recognition. Retraction Watch supplies post-publication notices and stated reasons, not a determination of misconduct. These measures were retained as distinct variables and were not treated as interchangeable measures of article quality.

## Reproducibility and source integrity

PubMed baseline files and update files were stored separately. Every XML file was accompanied by its NLM MD5 sidecar and was admitted only when its calculated checksum equalled the supplied checksum. Public DOAJ and Retraction Watch snapshots were acquired from their public CSV endpoints. SCImago, Scopus, NPI, and peer-review inputs were dated snapshots obtained by licensed supply or manual export. No live query was used during article linkage or analysis.

Every processing stage produced an append-only audit record. Table 2 specifies the audit fields. Cryptographic hashes referred to the exact files read and written by the stage. The audit record distinguished successful, skipped, and failed work. Distributed tasks wrote separate audit records before consolidation, avoiding concurrent writes to a shared database.

**Table 2. Stage audit record**

| Field | Definition |
| --- | --- |
| Stage | Named operation performed on the data |
| Status | Success, skipped, or failed |
| Input and output | Explicit paths for every declared input and output |
| Input and output checksum | SHA-256 digest of each material file where available |
| Byte size | Size of each material input and output |
| Record count | Number of records emitted by the stage; deletion count recorded separately for PubMed parsing |
| Time | Start time, completion time, and elapsed seconds |
| Worker | Host or task identity used for distributed work |
| Stage metadata | Snapshot year, parsing options, shard identity, filter counts, or other stage-specific quantities |
| Error | Exception text for recorded failures |

## PubMed state reconstruction and XML extraction

XML was read record by record so that memory use did not increase with file size. Malformed XML caused failure; recovery parsing was reserved for an explicitly designated salvage run and was not the normal study procedure. Baseline and update files were parsed as separate ordered series. Within each series, files were ordered by filename and citations within a file retained record order. The last event for a PMID defined its live state. A final live citation replaced all earlier representations of that PMID; a final `DeleteCitation` event removed it. State reconstruction preceded every article-level exclusion.

Table 3 gives the PubMed extraction rules. Complete calendar dates were required for the three dates used to calculate delay. A history event was usable only when year, month, and day were all present.

**Table 3. PubMed field extraction and normalization**

| Study field | XML content | Rule |
| --- | --- | --- |
| PMID | `PMID` | Text retained as the primary identifier |
| Title | `ArticleTitle` | Text content retained, including text nested in inline elements; blank titles excluded |
| Journal | `Journal/Title` | Journal title retained as supplied |
| Linking ISSN | `MedlineJournalInfo/ISSNLinking` | Hyphens and other punctuation removed; letters uppercased; terminal X retained |
| DOI | Article electronic location DOI, otherwise PubMed article identifier DOI | Lowercased; surrounding whitespace, DOI URL forms, `doi:` prefixes, and leading `//` removed |
| Publication types | `PublicationTypeList` | All terms retained; article eligibility required the term `Journal Article` |
| Keywords | `KeywordList` | All terms retained; semicolon separators standardized to commas |
| Receipt date | History event whose status is `received` | Complete ISO calendar date required |
| Acceptance date | History event whose status is `accepted` | Complete ISO calendar date required |
| Article date | `ArticleDate` | Complete ISO calendar date retained when present |
| Journal-issue date | `JournalIssue/PubDate` | Complete date used when supplied; a year-only value was insufficient for delay calculation |
| Publication date | Article date, otherwise journal-issue date | Selected value retained as the study publication date; its origin recorded as `article_date` or `pubdate` |
| Raw article date | `ArticleDate` | Retained separately and left missing when the publication date came from the journal issue |
| Deletion | `DeleteCitation/PMID` | Removes the PMID only when it is the last event for that PMID |

## Article eligibility, dates, and delay outcomes

Filtering followed the fixed order in Table 4. Missingness was measured immediately before and after each row-removing step for every variable, for the complete population and separately by publication year. External sources were joined before journal-metadata eligibility and deduplication so that join coverage was calculated on the incoming eligible article population rather than on a complete-case subset.

**Table 4. Ordered cohort checkpoints**

| Order | Population retained | Exact criterion |
| ---: | --- | --- |
| 1 | Parsed records | Every reconstructed PubMed citation and deletion event selected for transformation |
| 2 | Non-deleted records | Final PubMed event was not a deletion |
| 3 | Required parsed fields | History, journal title, journal-issue publication field, publication types, linking ISSN field, and nonblank title were present |
| 4 | Dated submissions | Complete receipt and acceptance dates were present |
| 5 | Journal articles | Publication-type text contained `Journal Article` |
| 6 | Identified journals | Normalized linking ISSN was nonblank |
| 7 | Chronologically coherent records | Publication date was present and receipt date < acceptance date < publication date |
| 8 | Nonnegative calculated delays | Both calculated intervals were at least zero days; strict chronological ordering made retained intervals positive |
| 9 | Externally enriched records | All optional external sources had been left joined; no exclusion was made for a failed match |
| 10 | Eligible journal metadata | NPI conference status was missing or 0; receipt date was on or after 1 January 2013; cessation year was missing or not earlier than publication year |
| 11 | Distinct articles | All PMID-bearing records retained; among records without PMID, first occurrence retained by normalized DOI, then by exact title when DOI was also absent |
| 12 | Final rows | Canonical columns selected in fixed order |
| 13 | Analysis-valid rows | Publication date from 1 January 2016 to 31 December 2025 and the modeled delay from 1 to 1,095 days, inclusive |

The two outcomes were calculated in calendar days:

| Outcome | Definition | Permitted analysis range |
| --- | --- | --- |
| Acceptance delay | Acceptance date minus receipt date | 1 to 1,095 days |
| Publication delay | Publication date minus acceptance date | 1 to 1,095 days |

The 1,095-day ceiling was applied separately to each modeled outcome. A record could therefore be valid for one outcome and invalid for the other. Equal and reversed dates were excluded by the strict ordering rule rather than recoded.

## External-source preparation and linkage

All journal sources were reduced to one row per normalized ISSN before article linkage. Rows containing both print and electronic ISSNs were expanded so that either identifier could link to the PubMed linking ISSN. The first source row in snapshot order was retained when a normalized key remained duplicated. Article counts before and after every join were required to be equal; any increase was treated as a cardinality failure. Table 5 states the linkage and missingness interpretation for each source.

**Table 5. Linkage rules and interpretation of absence**

| Source | Prepared key and selection | Match indicator | Meaning of a nonmatch |
| --- | --- | --- | --- |
| SCImago | Each ISSN token normalized and expanded; one row per ISSN | `match_scimago` | No journal record for that ISSN in the supplied annual files |
| Scopus Source List | Journal sources only; print and electronic ISSNs expanded; ASJC entries expanded and then collected by ISSN | `match_scopus` | No journal source with that ISSN in the June 2026 snapshot |
| DOAJ | Print and electronic ISSNs expanded; first row per ISSN | `match_doaj` | No journal entry for that ISSN in the July 2026 snapshot |
| Norwegian Register | Print and online ISSNs expanded; first row per ISSN | `match_npi` | No publication channel for that ISSN in the August 2026 snapshot |
| Peer review | DOI normalized; one article-level summary per DOI | `match_peer_review` | Source not supplied, DOI absent, or DOI absent from the private export |
| Retraction Watch | Original-paper DOI preferred, retraction-notice DOI used only when original DOI was absent; one row per DOI | Not included in the public match-indicator set | DOI absent or no DOI-linked notice in the supplied snapshot |

For each join, Table 6 was produced overall and by publication year. `Source supplied` separated an unavailable optional dataset from an available dataset with zero matches.

**Table 6. Join-quality evidence**

| Quantity | Numerator or count | Denominator |
| --- | --- | --- |
| Source supplied | Incoming article rows when the source file was available, otherwise 0 | Incoming article rows |
| Source rows | Rows in the prepared source before final key reduction | Source rows |
| Unique source keys | Distinct normalized join keys | Source rows |
| Duplicate-key pressure | Source rows minus unique source keys | Source rows |
| Article key present | Incoming article rows with a nonblank key | Incoming article rows |
| Article key missing | Incoming article rows with a blank or missing key | Incoming article rows |
| Matched | Incoming article rows linked to a source row | Incoming article rows |
| Unmatched keyed | Key-present incoming rows without a source match | Incoming article rows |
| Output rows | Rows after the left join | Incoming article rows |
| Cardinality change | Output rows minus incoming rows | Incoming article rows |

## Derived journal and article variables

### Annual journal measures

Publication year selected the annual SCImago H-index, SJR rank, SJR quartile, and NPI level. Annual values were available for 2015 through 2025. A publication year later than 2025 used the 2025 value, although such rows were outside the analysis window. No temporal interpolation was performed. Missing journal-year combinations remained missing.

The Scopus ASJC code determined the broad discipline according to Table 7. A journal could retain multiple ASJC codes and disciplines; the primary code and discipline were the first values in source order, while the complete ordered sets were retained separately.

**Table 7. Broad discipline assigned from ASJC code**

| ASJC code | Broad discipline |
| --- | --- |
| 1000 | Multidisciplinary |
| 1001 to 1111; 1214 to 1315; 2313 to 2406; 2749 to 2809; 2924 to 3005 | Life sciences |
| 1112 to 1213; 1316 to 1410; 1713 to 1804; 1914 to 2003; 3110 to 3322 | Social sciences and humanities |
| 1411 to 1712; 1805 to 1913; 2004 to 2312; 2407 to 2614; 3006 to 3109 | Physical sciences |
| 2615 to 2748; 2810 to 2923; 3323 to 3616 | Health sciences |
| Missing, nonnumeric, or above 3616 | Not assigned |

### Open-access evidence

Open access was a positive-evidence classification. Table 8 gives the three conditions. The article-level indicator was true if at least one condition was true. A false value meant that none of the matched sources supplied the listed positive evidence; it did not establish subscription access. Source matches and positive-evidence indicators were retained separately.

**Table 8. Open-access classification**

| Evidence source | Positive condition | Evidence label retained |
| --- | --- | --- |
| DOAJ | The field concerning compliance with the DOAJ definition of open access equalled `Yes` | `doaj` |
| Scopus Source List | After lowercasing and removing nonletters, open-access status equalled `unpaywallopenaccess`; the source misspelling `unpaywallopenacess` was also accepted | `scopus` |
| Norwegian Register | Open-access field equalled `DOAJ` | `npi` |

### Megajournal status

Megajournal status was a fixed study classification based on normalized linking ISSN. The full positive set is given in Table 9; every other nonmissing linking ISSN was classified false.

**Table 9. Linking ISSNs classified as megajournals**

| ISSN | ISSN | ISSN |
| --- | --- | --- |
| 2470-1343 | 2158-3226 | 2046-6390 |
| 2044-6055 | 2325-1026 | 2211-5463 |
| 2160-1836 | 2169-3536 | 2051-3305 |
| 2167-8359 | 1932-6203 | 2054-5703 |
| 2158-2440 | 2045-2322 | 2056-6700 |
| 2391-5447 | 2299-1093 | 2405-8440 |
| 2150-8925 | 2050-084X | 2046-1402 |

### COVID-19 status

COVID-19 status was true when a case-insensitive whole-term search found any expression in Table 10 in the concatenated title and keyword text. It was false otherwise.

**Table 10. COVID-19 search vocabulary**

| Terms |
| --- |
| covid; covid-19; coronavirus disease 19; sars-cov-2; 2019-ncov; 2019ncov; 2019-n-cov; 2019n-cov; ncov-2019; n-cov-2019; coronavirus-2019; wuhan pneumonia; wuhan virus; wuhan coronavirus; coronavirus 2 |

### Retraction status

Retraction Watch was linked by normalized DOI. A linked article was classified as retracted when either retraction nature or reason was nonblank. Retraction date described the notice. Original-paper date was retained as a Retraction Watch field and never replaced the PubMed publication date. Retraction was treated as a publication status, not as evidence of author misconduct.

## Article-processing charge proxy

The DOAJ APC declaration and APC amount text were retained without simplification because a journal could report several amounts or currencies. Every parseable amount-currency pair was converted separately. For each quote, the reference date was the article publication date. The most recent official rate on or before that date was selected, first from daily European Central Bank rates and then, if unavailable, from the corresponding or latest preceding European Commission InforEuro monthly rate. Euro quotations had a conversion factor of one.

The article-level summaries in Table 11 were calculated over successfully converted quotes. These are historical-currency conversions of a July 2026 journal snapshot. They are proxies for journal APC policy, not charges paid for the article and not necessarily the journal price in the year of publication.

**Table 11. APC proxy fields**

| Field | Definition |
| --- | --- |
| APC declaration | DOAJ text stating whether the journal levies an APC |
| Raw APC amount | Unmodified DOAJ amount and currency text |
| EUR proxy | Median converted euro amount |
| EUR proxy minimum and maximum | Smallest and largest converted euro amounts |
| Quote count | Number of parseable amount-currency pairs |
| FX sources | Distinct rate sources used among converted quotes |
| FX rate start and end | Earliest and latest rate dates used |
| Conversion status | `converted` when every parsed quote was converted; `partially_converted` when only some were converted; `missing_rate` when none could be converted; `no_parseable_quote` when nonblank text yielded no amount-currency pair; `no_quote` when amount text was blank; `conversion_failed` when conversion output was otherwise unavailable |

## Private peer-review metadata

The private source was an event export supplied by Clarivate. It contained DOI, review-event date, accepted-event date, and review-round number. It did not contain a reviewer identifier. Review-event count was therefore not used as a proxy for reviewer count, and reviewer count was structurally missing for all articles.

Only events with a nonblank DOI and a valid review date from 1 January 2013 through 31 December 2025 entered the article summary. Events were grouped by normalized DOI. Table 12 defines all peer-review variables. Where a supplied summary interval and a date-derived interval were both available, the date-derived value took precedence.

**Table 12. Peer-review variables and definitions**

| Variable | Definition |
| --- | --- |
| Number of review rounds | Maximum recorded review-round number for the DOI |
| Number of reviews | Count of review events for the DOI |
| First review date | Earliest review-event date |
| Last review date | Latest review-event date |
| Number of reviewers | Missing; reviewer identity was absent from the export |
| First accepted-event date | Earliest accepted-event date |
| Review-cycle delay | Last review date minus first review date |
| Review-finding delay | First accepted-event date minus PubMed receipt date |
| First-decision delay | First review date minus first accepted-event date |
| Final-decision delay | PubMed acceptance date minus last review date |
| First-review delay | First review date minus PubMed receipt date |
| Peer-review delay | PubMed acceptance date minus first review date |

Peer-review dates earlier than PubMed receipt or later than PubMed acceptance were counted as quality anomalies and then set to missing. Negative peer-review intervals were likewise counted before being set to missing. These operations did not remove the article. The private source was optional: when it was not supplied, all peer-review variables were missing and the match indicator was false.

## Canonical variables and missingness meaning

Table 13 is the study analysis variable dictionary. Empty optional values denote absent source information, an unmatched source, or a structurally unavailable field as specified. Boolean derivations were populated for every final article. Match indicators referred only to whether a source row linked, not whether a particular field within that row was present.

**Table 13. Study analysis variable dictionary**

| Variables | Level | Definition and missingness |
| --- | --- | --- |
| `pmid` | Article | PubMed identifier; may be empty only for records retained by DOI or title identity |
| `is_covid` | Article | Vocabulary match defined in Table 10; always true or false |
| `received` | Article | Complete PubMed receipt date; required |
| `article_date` | Article | Selected publication date; required after chronological filtering |
| `article_date_raw` | Article | PubMed ArticleDate; empty when absent even if a journal-issue date was usable |
| `publication_date_source` | Article | `article_date` or `pubdate` |
| `acceptance_delay` | Article | Acceptance minus receipt, days |
| `is_mega` | Journal | Membership in Table 9; always true or false |
| `issn_linking` | Journal | Normalized PubMed linking ISSN; required |
| `h_index_year`, `quartile_year`, `rank_year` | Journal-year | SCImago values selected by publication year; empty for unmatched journal-years |
| `open_access` | Journal | Positive-evidence union in Table 8; always true or false |
| `match_scimago`, `match_scopus`, `match_doaj`, `match_npi`, `match_peer_review` | Article-source | True when the article linked to the named supplied source |
| `open_access_doaj_evidence`, `open_access_scopus_evidence`, `open_access_npi_evidence` | Journal-source | Source-specific positive condition in Table 8; always true or false |
| `open_access_evidence_sources` | Journal | Pipe-separated positive source labels; empty when none were positive |
| `publication_delay` | Article | Publication minus acceptance, days |
| `publication_types` | Article | PubMed publication-type terms; required to include Journal Article |
| `title` | Article | PubMed article title; required and nonblank |
| `journal` | Journal | PubMed journal title; required |
| `discipline`, `asjc` | Journal | Primary broad discipline and ASJC code from Scopus; empty when unmatched |
| `discipline_all`, `asjc_all` | Journal | Complete ordered broad-discipline and ASJC assignments from Scopus |
| `scimago_categories` | Journal | SCImago subject categories; empty when unmatched |
| `npi_discipline`, `npi_field` | Journal | Norwegian Register classifications; empty when unmatched |
| `npi_year` | Journal-year | Norwegian level selected by publication year; empty when unmatched |
| `is_series` | Journal | Norwegian Register series field; empty when unmatched |
| `established` | Journal | Establishment year; empty when unreported or unmatched |
| `country` | Journal | Norwegian country of publication when available, otherwise available PubMed journal country metadata |
| `keywords` | Article | PubMed keyword text; empty when none were supplied |
| `apc`, `apc_amount` | Journal | Unmodified DOAJ APC declaration and amount text |
| `apc_eur_proxy`, `apc_eur_proxy_min`, `apc_eur_proxy_max`, `apc_quote_count`, `apc_fx_sources`, `apc_fx_rate_start`, `apc_fx_rate_end`, `apc_conversion_status` | Article-journal | APC proxy summaries defined in Table 11 |
| `doi` | Article | Normalized DOI; empty when PubMed supplied none |
| `retraction_nature`, `reason`, `retraction_date`, `retraction_original_date` | Article | DOI-linked Retraction Watch fields; empty when unmatched or unreported |
| `is_retracted` | Article | True when linked retraction nature or reason was nonblank; otherwise false |
| `n_review_round`, `n_reviews`, `first_review_date`, `last_review_date`, `date_first_accepted`, `review_cycle_delay`, `review_finding_delay`, `first_decision_delay`, `final_decision_delay`, `first_review_delay`, `peer_review_delay` | Article | Private peer-review summaries defined in Table 12; empty when unavailable, unmatched, or invalid |
| `n_reviewers` | Article | Structurally missing because the source contained no reviewer identifier |

## Data-quality evidence

Quality evidence was consolidated only after all article shards were complete. Table 14 gives the resulting evidence tables and their contents. Overall estimates and annual estimates were kept together; zero matches and source-not-supplied conditions remained distinct.

**Table 14. Data-quality evidence produced for the study**

| Evidence table | Unit | Contents |
| --- | --- | --- |
| Cohort flow | Filter checkpoint | Rows retained, rows dropped, reason, and percentage retained at each checkpoint in Table 4 |
| Stage and join debrief | Checkpoint or source by year | Missing and present counts before and after exclusions; all join quantities in Table 6; anomaly counts for peer-review dates and intervals |
| Variable quality | Variable by year and overall | Total, present, missing, missing percentage, invalid-format count, and distinct nonmissing values |
| Variable distributions | Variable by year and overall | Numeric mean, standard deviation, minimum, 1st, 5th, 25th, 50th, 75th, 95th, 99th percentiles, and maximum; date validity and range; category frequencies for variables with at most 20 levels; otherwise text distinctness and length summaries |
| Pairwise missingness | Target variable by stratum variable, stratum, and year | Target present and missing counts and percentage within categorical levels, date years, numeric quantile bands, or present-versus-missing text strata |
| Validation checks | Dataset and rule | Fixed column order, CSV and Parquet row parity, shard completeness, join cardinality, date chronology, delay range, audit integrity, and declared output location |

## Retrospective boosting analysis

Acceptance delay and publication delay were modeled separately with CatBoost regression. The estimand was predictive association in a retrospectively assembled cohort. Journal and review characteristics observed after submission could enter the model; neither feature importance nor SHAP values were interpreted as causal effects. The primary analysis retained retracted articles and included retraction status. A complete sensitivity analysis repeated each outcome after excluding retracted articles.

Table 15 gives the exact feature set and encoding. Categorical missing values were represented by the explicit level `__MISSING__`. Numeric missing values remained missing. Calendar features were calculated from the selected publication date.

**Table 15. Model features**

| Feature class | Variables | Encoding |
| --- | --- | --- |
| Journal identity and classification | `journal`, `discipline`, `asjc`, `country` | Categorical |
| Publishing model and article status | `open_access`, `is_mega`, `is_covid`, `apc`, `is_retracted` | Categorical |
| Publication metadata | `publication_date_source`, `quartile_year`, `is_series` | Categorical |
| Annual and historical journal measures | `h_index_year`, `rank_year`, `npi_year`, `established` | Numeric |
| Peer review | `n_review_round` | Numeric |
| Calendar | Integer publication date, weekday, ordinal day of year, month, publication year | Numeric |

The model specification is given in Table 16. The validation year was used once to select the number of boosting iterations. The final model was then refitted on all development years with that iteration count, and the 2025 test set was evaluated once.

**Table 16. Model development and evaluation specification**

| Component | Specification |
| --- | --- |
| Outcomes | Acceptance delay and publication delay, each restricted to 1 to 1,095 days |
| Training partition | Publication years 2016 to 2023 |
| Iteration-selection partition | Publication year 2024 |
| Final development partition | Publication years 2016 to 2024 |
| Test partition | Publication year 2025 |
| Loss and selection metric | Root mean squared error |
| Maximum boosting iterations | 5,000 |
| Learning rate | 0.03 |
| Tree depth | 8 |
| Early stopping | 50 rounds without improvement |
| Random seed | 20250805 |
| Missing categorical value | Explicit `__MISSING__` category |
| Missing numeric value | Native missing-value handling |
| Explanatory sample | At most 10,000 test rows, sampled with the fixed seed |
| Sensitivity analysis | Entire procedure repeated after removing retracted articles |

Performance was compared with two development-data baselines: the median outcome among all 2016 to 2024 articles and the median within journal over those years. For a 2025 journal absent from development data, the journal baseline used the global development median. Table 17 specifies the evaluation evidence.

**Table 17. Model evaluation evidence**

| Evidence | Definition |
| --- | --- |
| Mean absolute error | Mean absolute difference between observed and predicted days |
| Median absolute error | Median absolute difference between observed and predicted days |
| Root mean squared error | Square root of mean squared prediction error |
| R-squared | One minus residual sum of squares divided by total sum of squares in the evaluated sample |
| Journal-grouped validation | Up to four group folds within 2016 to 2023, with each journal confined to one fold; fewer folds used when fewer journals were available |
| Test subgroups | Discipline, open-access status, megajournal status, and whether the journal occurred in the 2016 to 2024 development data |
| Prediction evidence | Article title, publication date, journal, observed delay, predicted delay, and residual for every 2025 test article |
| Interpretation evidence | Conventional feature importance; row-level SHAP values for the fixed-seed sample; mean absolute SHAP value by feature |
| Diagnostic evidence | Actual-versus-predicted plot, residual plot, feature missingness by temporal partition, selected iteration count, partition sizes, and complete model specification |

## Final computational run and empirical quality results

### Frozen run identity and computing environment

The definitive run was `final_20260805_v3`, initiated on 25 August 2026 at 15:00:06 UTC after establishing the ELTE VPN connection. It used Git commit `4b7a55187c4012064cf91761700653ca6bd47873` and the immutable configuration `config/eltehpc-final.toml` (SHA-256 `477ef38b74c418b35bdfbc4462a355fce9575e500d831ce8eb9b866160f5fa08`). The dependency lock was `uv.lock` (SHA-256 `92769e4b18b0eb88e899ea0c8bcf7e933ad85bc6747b60e2f2f4e162fd35b068`). Jobs ran on the ELTE Atlasz cluster under Slurm 18.08.5, partition `hpc2019`, Linux 4.19.0-13-amd64, `uv` 0.11.14, and CPython 3.12.13. The shell-level source-gate metadata also records the cluster login default, Python 2.7.16, which was not the interpreter used by `uv run --frozen`.

The source set was frozen at the study cutoff rather than refreshed on the execution date. It comprised 1,334 PubMed baseline XML files and 229 update XML files (1,563 XML files in total), each paired with and verified against its NLM MD5 sidecar. The last update file was `pubmed26n1563.xml`. A source-gate job recalculated all 1,563 checksums before permitting any dependent task to start; every comparison passed. It also wrote byte sizes for all XML files and sidecars and SHA-256 digests for the 20 configuration, lock, external-snapshot, and exchange-rate inputs. No input was downloaded or modified during the run.

Run outputs were isolated under `data/{temp_data,processed_data,manifests}/runs/final_20260805_v3/`; Slurm logs were isolated under `logs/slurm/final_20260805_v3/`. Parsing used one task per XML input, with at most 20 concurrent tasks. Transformation used 64 deterministic Parquet shards, also capped at 20 concurrent tasks. Each distributed task wrote its own SQLite manifest. After successful completion, 1,334 baseline parse manifests, 229 update parse manifests, and 64 transformation manifests (1,627 task manifests) were collected exactly once into `pipeline.sqlite`; no corrupt task manifest was found and SQLite integrity checking returned `ok`.

**Table 18. Principal Slurm stages in the definitive run**

| Job ID | Stage | Allocation | Elapsed | Terminal state |
| ---: | --- | --- | ---: | --- |
| 2732112 | Source checksum and freeze gate | 1 CPU, 4 GB | 00:03:55 | Completed, exit 0 |
| 2732113 | External-source preparation | 2 CPUs, 12 GB | 00:00:18 | Completed, exit 0 |
| 2732114–2732115 | Baseline parsing, two arrays | 1 CPU and 6 GB per task | Array parents 00:00:29 and 00:00:04 | Completed, exit 0 |
| 2732116 | Update-file parsing array | 1 CPU and 6 GB per task | Array parent 00:00:14 | Completed, exit 0 |
| 2732117 | PubMed state resolution | 1 CPU, 16 GB | 00:43:29 | Completed, exit 0 |
| 2732118 | Transformation preparation | 1 CPU, 2 GB | 00:00:08 | Completed, exit 0 |
| 2732119 | Article transformation, 64-task array | 4 CPUs and 24 GB per task | Array parent 00:01:30 | Completed, exit 0 |
| 2732120 | Aggregate CSV and Parquet | 4 CPUs, 48 GB | 00:00:35 | Completed, exit 0 |
| 2733762 | Quality, validation, summaries, and evidence | 18 CPUs, 84 GB | 00:11:02 | Completed, exit 0 |
| 2733763 | Acceptance-delay primary and sensitivity models | 18 CPUs, 84 GB | 09:05:00 | Completed, exit 0 |
| 2733764 | Publication-delay primary and sensitivity models | 18 CPUs, 84 GB | 09:48:44 | Completed, exit 0 |

All job dependencies used `afterok`; consequently no downstream stage could start after a failed predecessor. All parent jobs in Table 18 and all array elements ended successfully. Every final-run error log was empty. The aggregate contained 10,068,189 rows and 71 columns. Its Parquet representation was 1,056,861,826 bytes with SHA-256 `1bf1d503d738b5b525adbce6826890f76e6f71758cd8e85e1c49e871a7272ac5`; the independently written CSV representation was 7,636,136,858 bytes. The schema command matched `analysis_dataset_v3`, all 64 Parquet shards were present and readable, and strict validation reported zero failed checks.

### PubMed reconstruction and cohort flow

Baseline parsing emitted 39,994,988 citation events and update parsing emitted 4,210,704 events, for 44,205,692 parsed events. Neither series contained an event without a PMID. Updates addressed 1,881,877 distinct PMIDs; 939,625 baseline PMIDs were superseded, and the final state contained 39,055,363 retained baseline citations plus 1,875,068 live update citations. A further 6,809 PMIDs had a final deletion event. The reconstructed live population was therefore 40,930,431 citations.

**Table 19. Ordered cohort flow in the definitive run**

| Checkpoint | Retained | Removed at checkpoint | Retained from preceding checkpoint |
| --- | ---: | ---: | ---: |
| Reconstructed live citations | 40,930,431 | — | 100.0000% |
| Required parsed fields present | 40,887,936 | 42,495 | 99.8962% |
| Receipt and acceptance dates present | 13,293,109 | 27,594,827 | 32.5111% |
| Journal Article publication type | 12,672,801 | 620,308 | 95.3336% |
| Linking ISSN present | 12,513,069 | 159,732 | 98.7396% |
| Strictly coherent dates | 12,113,263 | 399,806 | 96.8049% |
| Nonnegative calculated delays | 12,113,263 | 0 | 100.0000% |
| After all left joins | 12,113,263 | 0 | 100.0000% |
| Eligible journal metadata | 10,068,189 | 2,045,074 | 83.1171% |
| Distinct final articles | 10,068,189 | 0 | 100.0000% |

All 10,068,189 final records had a unique, nonmissing PMID; DOI- or title-based fallback deduplication was therefore not invoked in this run. The analytic date window, 2016–2025 inclusive, contained 8,188,026 articles (81.3257% of final rows). Applying the 1–1,095-day range separately yielded 8,186,194 acceptance-delay observations (81.3075%) and 8,187,090 publication-delay observations (81.3164%). The intersection contained 8,185,258 articles (81.2982%). Thus, 1,832 date-window articles were excluded only from acceptance-delay analysis, 936 only from publication-delay analysis, and 2,768 from the paired cohort; outcome-specific analyses did not discard an otherwise valid outcome because its counterpart was out of range.

### Linkage coverage and variable completeness

Every journal-source join received 12,113,263 rows and returned exactly 12,113,263 rows; Retraction Watch, which was joined after journal-metadata eligibility, received and returned 10,068,189 rows. Every cardinality delta was zero. Table 20 reports coverage against the population entering the corresponding join, not against complete cases.

**Table 20. Overall external-source linkage**

| Source | Prepared unique keys | Article key present | Matched articles | Match percentage | Cardinality change |
| --- | ---: | ---: | ---: | ---: | ---: |
| SCImago | 53,404 | 12,113,263 | 11,592,221 | 95.6986% | 0 |
| Scopus Source List | 69,141 | 12,113,263 | 11,917,072 | 98.3804% | 0 |
| DOAJ | 35,433 | 12,113,263 | 4,420,598 | 36.4939% | 0 |
| Norwegian Register | 64,392 | 12,113,263 | 11,605,634 | 95.8093% | 0 |
| Private peer-review export | 4,447,396 | 12,042,070 | 1,345,729 | 11.1095% of all incoming rows | 0 |
| Retraction Watch | — | 10,025,851 | 15,744 | 0.1564% of all final rows | 0 |

The peer-review join had 71,193 incoming articles without a DOI (0.5877%); Retraction Watch had 42,338 final articles without a DOI (0.4205%). The external journal tables were reduced to unique normalized keys before linkage, so duplicate-key pressure at the actual join boundary was zero for every supplied journal source.

**Table 21. Selected overall completeness measures in the 10,068,189-row final dataset**

| Variable or construct | Present | Missing | Missing percentage |
| --- | ---: | ---: | ---: |
| PMID, receipt date, selected publication date, both calculated delays | 10,068,189 | 0 | 0.0000% |
| DOI | 10,025,851 | 42,338 | 0.4205% |
| Broad discipline and primary ASJC | 9,908,072 | 160,117 | 1.5903% |
| SCImago categories | 9,688,581 | 379,608 | 3.7704% |
| NPI discipline and field | 9,612,186 | 456,003 | 4.5291% |
| Establishment year | 9,473,648 | 594,541 | 5.9051% |
| Annual H-index and rank | 9,045,668 | 1,022,521 | 10.1560% |
| Annual quartile | 8,914,934 | 1,153,255 | 11.4544% |
| Keywords | 7,824,325 | 2,243,864 | 22.2867% |
| APC amount and converted EUR proxy | 3,942,806 | 6,125,383 | 60.8390% |
| Peer-review round and event count | 1,342,610 | 8,725,579 | 86.6648% |
| First review date | 1,110,377 | 8,957,812 | 88.9714% |
| First accepted-event date | 249,875 | 9,818,314 | 97.5182% |
| Reviewer count | 0 | 10,068,189 | 100.0000% (structural) |

All 19 strict checks passed. These checks included canonical column order, required-field completeness, date and numeric parsing, receipt-date and journal-measure ranges, Journal Article content, PMID uniqueness, fallback-key uniqueness, and the conditional requirements that all 3,942,806 nonmissing APC quotations had conversion results and all 15,744 retraction matches had a reason. Missing optional covariates were retained rather than converted into exclusions. The quality stage produced six tables, including overall and yearly quality for all 71 variables, distribution summaries, and pairwise missingness strata; validation produced 23 tables.

### Observed delay distributions

Across outcome-eligible articles, acceptance delay had mean 119.65 days, median 96 days, and interquartile range 54–156 days. Publication delay had mean 33.77 days, median 17 days, and interquartile range 6–37 days. Acceptance occurred within 30 days for 851,460 articles, within 60 days for 2,368,358, and within 180 days for 6,644,271. These cumulative counts use the 8,186,194-record acceptance cohort.

**Table 22. Annual outcome-specific cohorts and delay distributions**

| Publication year | Acceptance n | Acceptance median (IQR), days | Publication n | Publication median (IQR), days |
| ---: | ---: | ---: | ---: | ---: |
| 2016 | 540,375 | 103 (64–159) | 540,409 | 22 (9–46) |
| 2017 | 578,218 | 105 (64–163) | 578,252 | 22 (8–49) |
| 2018 | 618,002 | 103 (61–162) | 618,068 | 20 (7–44) |
| 2019 | 674,041 | 102 (59–161) | 674,118 | 20 (7–41) |
| 2020 | 837,235 | 92 (50–151) | 837,318 | 19 (7–39) |
| 2021 | 957,196 | 90 (49–150) | 957,290 | 18 (6–37) |
| 2022 | 987,196 | 86 (45–148) | 987,369 | 16 (5–34) |
| 2023 | 928,298 | 90 (50–152) | 928,458 | 14 (5–29) |
| 2024 | 974,889 | 98 (56–160) | 975,003 | 14 (5–30) |
| 2025 | 1,090,744 | 101 (58–163) | 1,090,805 | 15 (5–34) |

### Predictive-model results and reproducibility

The primary acceptance model used 6,120,561 training, 974,889 iteration-selection, and 1,090,744 test observations; early stopping selected 2,999 iterations. On the held-out 2025 cohort its mean absolute error (MAE) was 55.65 days, median absolute error 38.54 days, root mean squared error (RMSE) 83.57 days, and R-squared 0.311. The global historical-median baseline had MAE 68.77 days and the journal historical-median baseline 55.93 days. The primary publication model used 6,121,282 training, 975,003 iteration-selection, and 1,090,805 test observations; it selected 2,949 iterations. Its 2025 MAE was 16.27 days, median absolute error 7.20 days, RMSE 34.92 days, and R-squared 0.501, compared with MAEs of 23.73 and 17.33 days for the global and journal baselines.

Excluding retracted articles changed neither conclusion materially. The acceptance sensitivity model used 6,107,381 training, 974,299 validation, and 1,090,644 test rows, selected 2,441 iterations, and obtained MAE 55.64 days, RMSE 83.63 days, and R-squared 0.310. The publication sensitivity model used 6,108,105 training, 974,413 validation, and 1,090,706 test rows, selected 2,714 iterations, and obtained MAE 16.31 days, RMSE 34.87 days, and R-squared 0.502.

In the primary models, journal identity had the largest mean absolute SHAP value for both outcomes (41.85 days for acceptance and 17.51 days for publication). The next largest acceptance contributions were integer publication date (3.32), annual H-index (1.96), annual rank (1.79), and ASJC category (1.53). For publication delay they were publication-date source (5.72), integer publication date (3.53), country (3.44), APC declaration (2.67), annual H-index (2.55), and discipline (2.37). These values quantify predictive contribution on the fitted scale and do not identify causal effects.

All four model manifests record a full-sample fraction of 1.0, seed 20250805, input path, input byte size and SHA-256, feature lists, selected iteration, temporal partition sizes, package versions, artifact byte sizes, and artifact SHA-256 digests. The model environment contained CatBoost 1.2.10, pandas 3.0.5, Polars 1.40.1, NumPy 2.5.1, scikit-learn 1.9.0, and Matplotlib 3.11.1. Predictions and model binaries remain in the isolated HPC run directory; the repository evidence bundle contains only aggregate JSON/CSV evidence, manifests, and non-identifying SVG diagnostics.

The evidence supporting Tables 18–22 is archived under `docs/paper/evidence/eltehpc_final_20260805_v3/`. `paper_evidence/run_summary.json` is the machine-readable source for cohort flow, outcome eligibility, annual delays, join coverage, validation checks, and overall variable completeness. `pipeline.sqlite` is the consolidated stage audit. Each model subdirectory contains the exact model manifest, aggregate performance metrics, feature missingness, conventional and SHAP importance summaries, and diagnostic SVGs. Article-level predictions, row-level SHAP values, private source data, aggregate article data, and model binaries are deliberately excluded from the repository.

## Ethics

The study used bibliographic records, journal metadata, post-publication notices, and article-level peer-review event metadata. No individual-level reviewer identifier was available or constructed. No individuals participated in the study; ethical approval was therefore not sought.
