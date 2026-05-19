# Data Layout

Raw inputs, generated intermediates, manifests, and final outputs are documented in `DATA_LAYOUT.md` at the repository root.

Common raw input locations:

```text
data/raw_data/pubmed/xmls/
data/raw_data/scimago/
data/raw_data/web_of_science/wos.csv
data/raw_data/directory_of_open_access_journals/doaj_2025_05_15.csv
data/raw_data/norwegian_publication_indicator/norwegian_list_2025_05_14.csv
data/raw_data/retraction_watch/retraction_watch.csv
data/raw_data/publisher_metadata/publishers.csv
```

Generated outputs remain under `data/temp_data/`, `data/processed_data/`, and `data/manifests/`.
