# Publication Delays

Dominik Dianovics, Marton A. Varga, Miklos Bognar, Balazs Aczel

This project analyzes publication and editorial delay trends in PubMed/MEDLINE records. The pipeline extracts MEDLINE XML records, derives receipt/acceptance/publication dates, enriches articles with journal-level metadata, and produces article-level and aggregate datasets for downstream analysis.

## Current status

Implemented in the current worktree:

- `flake.nix` using `flake-parts`.
- Nix-managed Python development environment.
- Python package under `src/pubdelays/`.
- `pubdelays-pipeline` CLI.
- Local MEDLINE parser under `src/pubdelays/parser/medline.py`, so the workflow no longer requires overwriting an installed `pubmed_parser` package file.
- JSON/JSONL validation command.
- NLM journal metadata downloader/parser for `J_Medline.txt`.
- Initial Python transformation layer under `src/pubdelays/transform/articles.py`.
- Named filter-count output for the transformation step.
- Tests under `tests/`.
- Transitional shell wrapper under `scripts/pipeline.sh`.

Still transitional or legacy:

- The old scripts under `src/data_processing/` remain as references.
- `process_data.R`, `aggregate.R`, and validation/analysis scripts are not yet fully retired.
- The Python transformation layer is intended to preserve the old study logic first; semantic cleanup should happen only after filter counts and outputs are compared against the legacy R outputs.
- External enrichment files are still expected as CSV inputs in `data/processed_data/` unless overridden.

## Requirements

The intended setup is Nix-first.

```bash
nix develop
```

Useful commands inside or outside the dev shell:

```bash
nix flake check
nix run .#pubdelays-pipeline -- --help
nix run .#pubdelays-pipeline -- parse --help
nix run .#pubdelays-pipeline -- transform --help
```

A non-Nix fallback is available for quick local testing:

```bash
python3 -m pip install -e '.[dev]'
pytest -q
```

The Nix environment is the source of truth for dependencies. Avoid installing project dependencies manually except for temporary debugging.

## Repository layout

```text
config/
  default.toml                 # Repository-relative pipeline defaults.

scripts/
  pipeline.sh                  # Transitional single-entry wrapper around the Python CLI.
  download_pubmed.sh           # Convenience wrapper for PubMed XML download.

src/pubdelays/
  cli.py                       # pubdelays-pipeline command-line interface.
  schema.py                    # Canonical output columns, filter stages, vocabularies.
  parser/medline.py            # Self-vendored MEDLINE XML parser.
  transform/articles.py        # Article-level filtering and enrichment.

src/data_processing/
  *.R, *.sh, *.py              # Legacy workflow and reference implementation.

data/
  raw_data/                    # Raw PubMed XML and parsed intermediate data.
  processed_data/              # External enrichment CSVs and processed outputs.
  external/                    # Downloaded external metadata, such as NLM journals.

tests/
  test_medline_parser.py
  test_transform_articles.py
```

## Data inputs

The full pipeline expects PubMed/MEDLINE XML files and optional journal-level enrichment tables.

Default locations are defined in `config/default.toml`:

```text
data/raw_data/pubmed/xmls/             # PubMed .xml or .xml.gz files
data/raw_data/pubmed/jsonl/            # Parsed MEDLINE JSONL output
data/external/pubmed-journals.csv      # NLM journal metadata
data/processed_data/scimago.csv
data/processed_data/web_of_science.csv
data/processed_data/doaj.csv
data/processed_data/norwegian_list.csv
data/processed_data/retraction_watch.csv
```

The PubMed XML corpus is large. Downloading and parsing all baseline/update files requires substantial wall time, disk space, memory, and CPU. Run small smoke tests before launching a full HPC job.

## Recommended workflow

### 1. Enter the development environment

```bash
nix develop
```

### 2. Run tests

```bash
pytest -q
```

Expected current result:

```text
5 passed
```

### 3. Download PubMed XML files

Baseline files:

```bash
pubdelays-pipeline download \
  --source baseline \
  --output-dir data/raw_data/pubmed/xmls \
  --resume
```

Daily update files:

```bash
pubdelays-pipeline download \
  --source updatefiles \
  --output-dir data/raw_data/pubmed/xmls \
  --resume
```

For a small smoke test:

```bash
pubdelays-pipeline download \
  --source baseline \
  --output-dir data/raw_data/pubmed/xmls \
  --resume \
  --limit 2
```

The downloader keeps NCBI `.md5` sidecar files and verifies downloaded data.

### 4. Download and parse NLM journal metadata

```bash
pubdelays-pipeline journals \
  --output data/external/pubmed-journals.csv
```

### 5. Parse MEDLINE XML to JSONL

```bash
pubdelays-pipeline parse \
  --input-dir data/raw_data/pubmed/xmls \
  --output-dir data/raw_data/pubmed/jsonl \
  --jobs 8 \
  --format jsonl \
  --resume \
  --parse-mesh-subterms
```

The parser reads `.xml` and `.xml.gz` directly. Do not decompress the whole corpus unless there is a specific debugging reason.

### 6. Validate parsed JSONL

```bash
pubdelays-pipeline validate data/raw_data/pubmed/jsonl
```

### 7. Transform parsed records into the article-level dataset

```bash
pubdelays-pipeline transform \
  --input data/raw_data/pubmed/jsonl \
  --output data/processed_data/articles.tsv \
  --filters-output data/processed_data/filter_counts.csv \
  --scimago data/processed_data/scimago.csv \
  --web-of-science data/processed_data/web_of_science.csv \
  --doaj data/processed_data/doaj.csv \
  --norwegian-list data/processed_data/norwegian_list.csv \
  --retraction-watch data/processed_data/retraction_watch.csv
```

The transformation stage writes two important files:

```text
data/processed_data/articles.tsv
  Article-level analysis table.

data/processed_data/filter_counts.csv
  Counts after each named inclusion/exclusion stage.
```

### 8. Or run the transitional wrapper

```bash
scripts/pipeline.sh
```

The wrapper runs journal metadata download, parsing, validation, and transformation using repository-relative defaults. It uses Nix automatically when available.

To bypass Nix temporarily:

```bash
USE_NIX=0 scripts/pipeline.sh
```

Useful overrides:

```bash
JOBS=32 scripts/pipeline.sh
XML_DIR=/path/to/xmls JSONL_DIR=/path/to/jsonl scripts/pipeline.sh
```

## Parser policy

The local parser currently preserves the custom fields needed by the publication-delay analysis:

```text
history
article_date
grant_ids
publication_types
issn_linking
mesh_terms
keywords
pmid
doi
journal
pubdate
title
abstract
```

It also preserves `DeleteCitation` handling so that baseline/update workflows can represent deleted PubMed records explicitly.

## Transformation filter stages

The Python transformation layer records counts for the following stages:

```text
raw_records
non_deleted_records
has_required_parsed_fields
has_received_and_accepted_dates
journal_articles
has_linking_issn
coherent_dates
nonnegative_delays
after_external_joins
eligible_journal_metadata
distinct_titles
final_rows
```


## Development checks

Run:

```bash
pytest -q
nix flake check
```

Before committing pipeline changes, also run a small XML fixture or a limited PubMed download and inspect:

```text
parse_manifest.csv
filter_counts.csv
articles.tsv
```

The guiding rule is reproducibility first: fixed dependencies through Nix, explicit parser ownership, named filters, auditable intermediate files, and no manual package overwrites.
