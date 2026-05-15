# Data layout

The pipeline reads and writes repository-relative paths configured in `config/default.toml`.

Place existing raw files here:

```text
data/raw_data/pubmed/xmls/
  pubmed25n0001.xml.gz
  pubmed25n0001.xml.gz.md5        # optional but recommended
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
```

Generated files are written here:

```text
data/temp_data/pubmed/jsonl/      # parsed JSONL, one file per PubMed XML input
data/temp_data/articles_tsv/      # transformed article TSV shards and filter-count CSVs
data/processed_data/              # cleaned external metadata and final processed.csv
data/manifests/                   # SQLite manifest, WAL files, and SLURM input lists
data/external/                    # downloaded NLM journal metadata
```

`data/temp_data/` is intentionally sharded. Shards are safer for parallel writes and faster to resume than one monolithic intermediate file.
