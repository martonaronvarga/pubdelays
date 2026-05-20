# Data Layout

All paths are repository-relative unless `config/default.toml` or `--config` points to absolute paths. Generated data should remain under `data/` and should not be committed.

## Raw Inputs

```text
data/raw_data/pubmed/xmls/                         PubMed baseline/update XML or XML.GZ files
data/raw_data/pubmed/xmls/*.xml.gz.md5             PubMed MD5 sidecars
data/raw_data/scimago/scimagojr <year>.csv         Yearly SCImago exports, 2015-2024 by default
data/raw_data/web_of_science/wos.csv               Web of Science journal categories
data/raw_data/directory_of_open_access_journals/   DOAJ journal CSV
data/raw_data/norwegian_publication_indicator/     Norwegian Publication Indicator CSV
data/raw_data/retraction_watch/retraction_watch.csv Retraction Watch CSV
data/raw_data/publisher_metadata/publishers.csv    Optional publisher enrichment
path/to/private-peer-review.csv                    Optional licensed peer-review metadata supplied with --peer-review
```

The PubMed parser reads `.xml.gz` directly; do not decompress baseline files unless you have a storage-specific reason.

## Generated Intermediates

```text
data/temp_data/pubmed/jsonl/              One parsed JSONL shard per PubMed XML file
data/temp_data/article_parquet/           Transformed article shards
data/manifests/parse_inputs.txt           SLURM parse array input list
data/manifests/transform_inputs.txt       SLURM transform array input list
data/manifests/pipeline.sqlite            Collected SQLite manifest
data/manifests/slurm/parse/*.sqlite       Per-task parse manifests on HPC
data/manifests/slurm/transform-shards/*.sqlite Per-task transform manifests on HPC
```

Per-task SLURM manifests avoid concurrent writes to a single SQLite file on shared filesystems. Use `pubdelays manifest collect` after a run if you want a consolidated manifest.

## Final Outputs

```text
data/processed_data/processed.parquet     Canonical `analysis_dataset_v1` dataset
data/processed_data/processed.csv         CSV export for collaborators
data/processed_data/summaries/            Derived analysis summary tables
data/processed_data/*.csv                 Processed external lookup tables
```

See [Stage Contracts](STAGE_CONTRACTS.md) for the command-level mapping from inputs to outputs, and [Analysis Dataset V1](ANALYSIS_DATASET_V1.md) for final columns.
