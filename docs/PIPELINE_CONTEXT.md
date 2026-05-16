# Pipeline Context

This document gives enough context for an in-tree coding agent to modify the PubMed/MEDLINE pipeline without rediscovering the project every session.

## Project goal

The project analyzes publication and editorial delays in PubMed/MEDLINE records. The central measurements are:

```text
acceptance_delay  = accepted_date - received_date
publication_delay = publication_date - accepted_date
```

The publication date is defined as:

```text
publication_date = article_date if present else pubdate
```

This is an intentional correction relative to the legacy pipeline, which dropped missing-`article_date` rows before the fallback could contribute.

## Data flow

```text
NCBI PubMed XML/XML.GZ
  -> streaming MEDLINE parser
  -> JSONL parser shards
  -> Polars transform shards joined with external metadata
  -> Parquet article shards
  -> final processed.parquet + processed.csv
```

External metadata flow:

```text
raw Scimago yearly CSVs         -> processed Scimago table
raw Web of Science categories   -> processed WoS table
raw DOAJ CSV                    -> processed DOAJ table
raw Norwegian Publication list  -> processed NPI table
raw Retraction Watch CSV        -> processed retraction table
```

## Canonical directories

Raw inputs:

```text
data/raw_data/pubmed/xmls/
data/raw_data/scimago/
data/raw_data/web_of_science/
data/raw_data/directory_of_open_access_journals/
data/raw_data/norwegian_publication_indicator/
data/raw_data/retraction_watch/
```

Generated intermediates:

```text
data/temp_data/pubmed/jsonl/
data/temp_data/article_parquet/
```

Generated final outputs:

```text
data/processed_data/processed.parquet
data/processed_data/processed.csv
```

Generated manifest:

```text
data/manifests/pipeline.sqlite
```

These directories are runtime data locations. They are ignored by git except for `.gitkeep`/README placeholders.

## Active modules

```text
src/pubdelays/parser/medline.py
```

Streaming parser. It must preserve low memory use and support `.xml` and `.xml.gz`.

```text
src/pubdelays/external/*.py
```

Polars-native preprocessors for external journal metadata. These should not contain manual CSV parsing.

```text
src/pubdelays/transform/articles.py
```

Article-level filtering, enrichment, delay calculation, flags, and final schema construction.

```text
src/pubdelays/aggregate.py
```

Parquet shard aggregation and final output writing.

```text
src/pubdelays/manifest.py
```

SQLite manifest with process-safe append semantics.

```text
src/pubdelays/cli.py
```

Command-line API. Keep it thin: parse args, load config, call modules.

## Legacy semantic sources

Legacy files are references only:

```text
legacy/data_processing/xmls2json.py
legacy/data_processing/process_data.R
legacy/data_processing/scimago.R
legacy/data_processing/wos.R
legacy/data_processing/doaj.R
legacy/data_processing/npi.R
legacy/data_processing/retraction_watch.R
legacy/data_processing/aggregate.R
```

Do not invoke these from the new pipeline.

## Important semantic choices

### Article date fallback

Use:

```python
publication_dt = article_dt or pubdate
```

Rows with missing `article_date` but valid `pubdate` should be retained when all other date logic passes.

### Ceased journals

Use article publication year:

```text
keep if ceased_year is missing or ceased_year >= publication_year
```

Do not preserve the legacy `ceased = is.numeric(ceased)` behavior.

### Join keys

Normalize ISSNs before joins:

```text
remove hyphens
uppercase X
trim whitespace
empty string/null means missing
```

Use DOI joins for Retraction Watch after normalizing DOI case/spacing.

### Final data format

Use Parquet as the canonical analysis format. CSV exists for portability.

## Common failure modes

1. Nix builds an old or partial package because files are untracked or source filtering is wrong.
2. CLI imports a module that is not packaged.
3. Generated data/caches enter the source tree.
4. External metadata is loaded once per PubMed file under SLURM.
5. A worker writes partial outputs that look complete.
6. Path defaults drift between `README.md`, `config/default.toml`, scripts, and CLI.
7. Legacy bugs are accidentally reintroduced in the name of parity.

## Minimal smoke sequence

```bash
pubdelays-pipeline init-dirs
pubdelays-pipeline preflight
pubdelays-pipeline external-all --resume
pubdelays-pipeline parse --limit 2 --jobs 2 --format jsonl --parse-mesh-subterms --resume
pubdelays-pipeline transform-shards --shards 2 --jobs 2 --format parquet --resume
pubdelays-pipeline aggregate-all --resume
pubdelays-pipeline manifest --limit 20
```

Adjust commands depending on available raw data.
