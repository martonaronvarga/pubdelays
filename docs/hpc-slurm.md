# HPC and SLURM

SLURM is optional. Local commands work without a scheduler; SLURM commands submit explicit `sbatch` jobs with config-defined resources.

## Prepare an HPC Config

```bash
cp config/default.toml config/hpc.toml
```

Edit `config/hpc.toml` for the cluster:

```toml
[slurm]
runner = "uv run pubdelays"
log_dir = "logs/slurm"
partition = ""
account = ""
qos = ""

[external.download]
scimago_url_template = ""
publisher_url = ""
```

Set `scimago_url_template` and `publisher_url` only when you have working automated URLs. Web of Science and Norwegian Publication Indicator inputs normally remain manual/licensed files in the raw-data paths documented in `DATA_LAYOUT.md`.

## Dry Runs

```bash
uv run pubdelays --config config/hpc.toml download-external --source all --dry-run
uv run pubdelays --config config/hpc.toml slurm submit download --source baseline --dry-run
uv run pubdelays --config config/hpc.toml slurm submit download-external --external-source all --dry-run
uv run pubdelays --config config/hpc.toml slurm submit parse --dry-run
uv run pubdelays --config config/hpc.toml slurm submit transform-shards --shards 64 --dry-run
```

## Submit Data Preparation

```bash
uv run pubdelays --config config/hpc.toml slurm submit download --source baseline
uv run pubdelays --config config/hpc.toml slurm submit download-external --external-source all
uv run pubdelays --config config/hpc.toml slurm submit external-all
```

If your site disallows network access from compute nodes, run `download` and `download-external` on an approved transfer node, then submit `external-all`.

## Submit Parse to Aggregate

```bash
uv run pubdelays --config config/hpc.toml slurm workflow --shards 64
```

The workflow submits these stages with `afterok` dependencies:

1. `parse`: one XML/XML.GZ file per array task.
2. `prepare-transform`: writes `data/manifests/transform_inputs.txt`.
3. `transform-shards`: one modulo shard per array task; each worker loads external metadata once.
4. `aggregate-all`: validates expected shards and writes final Parquet/CSV outputs.

## Inspect Progress

```bash
uv run pubdelays --config config/hpc.toml slurm status <job-id>
uv run pubdelays --config config/hpc.toml manifest summary
uv run pubdelays --config config/hpc.toml manifest failed --limit 20
```

Logs default to `logs/slurm/`. Final outputs default to `data/processed_data/processed.parquet` and `data/processed_data/processed.csv`.
