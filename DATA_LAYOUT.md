# Data layout

All paths are repository-relative unless an absolute path is given in `config/default.toml`.

## Raw inputs

Place existing files here before running `pubdelays-pipeline preflight`.

```text
data/raw_data/pubmed/xmls/
  pubmed25n0001.xml.gz
  pubmed25n0001.xml.gz.md5
  ...

data/raw_data/scimago/
  scimagojr 2015.csv
  scimagojr 2016.csv
  ...
  scimagojr 2024.csv

data/raw_data/web_of_science/
  wos.csv

data/raw_data/directory_of_open_access_journals/
  doaj_2025_05_15.csv

data/raw_data/norwegian_publication_indicator/
  norwegian_list_2025_05_14.csv

data/raw_data/retraction_watch/
  retraction_watch.csv

data/raw_data/publisher_metadata/
  publishers.csv  # optional ISSN-keyed publisher enrichment
```

The PubMed parser reads `.xml.gz` directly. Do not gunzip the PubMed baseline unless you have a specific storage reason.

## Generated intermediates

```text
data/temp_data/pubmed/jsonl/        # one parsed JSONL per PubMed XML file
data/temp_data/article_parquet/     # transformed article shards, usually one per transform shard
data/manifests/pipeline.sqlite      # append-only SQLite manifest; WAL mode is enabled
data/manifests/parse_inputs.txt     # SLURM parse-array input list
data/manifests/transform_inputs.txt # SLURM transform-array input list
```

See `docs/STAGE_CONTRACTS.md` for the stage-level contract that maps these paths to CLI commands, manifest rows, resume behavior, and failure behavior.

## Generated final outputs

```text
data/processed_data/scimago.csv
data/processed_data/web_of_science.csv
data/processed_data/doaj.csv
data/processed_data/norwegian_list.csv
data/processed_data/retraction_watch.csv
data/processed_data/publisher_metadata.csv
data/processed_data/processed.parquet  # preferred analysis input
data/processed_data/processed.csv      # collaborator/export format
data/processed_data/summaries/         # derived analysis summary CSV tables
```

`processed.parquet` is the canonical `analysis_dataset_v1` input documented in `docs/ANALYSIS_DATASET_V1.md`. CSV is emitted for collaborators and tools that do not read Parquet. Multi-valued subject metadata is stored as pipe-delimited text columns (`asjc_all`, `discipline_all`, `scimago_categories`) for CSV/R/Python interoperability while scalar `asjc` and `discipline` retain first-category compatibility semantics. Optional publisher metadata joins on normalized linking ISSN; missing publisher input becomes empty publisher columns in article outputs.
