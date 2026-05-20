# HPC and SLURM

SLURM support is optional and explicit. Local commands work without a scheduler; SLURM commands generate `sbatch` scripts using resources from `config/default.toml` or a supplied config.

## Prepare

Use the repository defaults or copy a cluster config:

```bash
cp config/default.toml config/hpc.toml
```

Set the scheduler fields your cluster requires:

```toml
[slurm]
runner = "uv run pubdelays"
log_dir = "logs/slurm"
partition = ""
account = ""
qos = ""
max_array_size = 1001
```

`max_array_size` is the scheduler array task limit. The CLI splits oversized arrays and remaps logical task IDs so clusters that reject task IDs above `MaxArraySize - 1` still work.

## Dry Run

Inspect generated scripts before submission:

```bash
uv run pubdelays --config config/hpc.toml slurm submit parse --dry-run
uv run pubdelays --config config/hpc.toml slurm submit transform-shards --shards 64 --dry-run
uv run pubdelays --config config/hpc.toml slurm workflow --shards 64 --dry-run
```

The parse and transform scripts should include `PUBDELAYS_STAGE_MANIFEST`, which means array workers use per-task manifest files instead of sharing one SQLite DB.

## Submit Workflow

```bash
uv run pubdelays --config config/hpc.toml slurm workflow --shards 64 --max-array-size 1001
```

The workflow submits:

1. `parse`: one PubMed XML/XML.GZ file per array task.
2. `prepare-transform`: creates `data/manifests/transform_inputs.txt`.
3. `transform-shards`: one modulo shard per array task.
4. `aggregate-all`: validates shard completeness and writes final outputs.

Dependencies use `afterok`, so downstream jobs wait for upstream success.

## Monitor

```bash
squeue -u "$USER" -o "%.18i %.30j %.2t %.10M %.30R"
uv run pubdelays --config config/hpc.toml slurm status <job-id>
```

Logs default to `logs/slurm/`.

Common checks:

```bash
find data/temp_data/pubmed/jsonl -name '*.jsonl' | wc -l
find data/temp_data/article_parquet -name '*.parquet' | wc -l
```

For a 64-shard run, a complete transform has 64 article shard files.

## Recovery

Cancel dependency-blocked jobs after an upstream failure:

```bash
uv run pubdelays --config config/hpc.toml slurm cleanup <root-job-id>
uv run pubdelays --config config/hpc.toml slurm cleanup <root-job-id> --cancel
```

Check and archive a corrupt manifest without relying on the `sqlite3` shell:

```bash
uv run pubdelays --config config/hpc.toml manifest check --manifest data/manifests/pipeline.sqlite
uv run pubdelays --config config/hpc.toml manifest check \
  --manifest data/manifests/pipeline.sqlite \
  --cleanup \
  --archive-dir data/manifests/corrupt
```

After parse/transform array jobs finish, collect per-task manifests once:

```bash
uv run pubdelays --config config/hpc.toml manifest collect \
  --manifest data/manifests/pipeline.sqlite \
  --input-dir data/manifests/slurm
```

`manifest collect` is append-only and intended for one post-run audit collection. If repeated, row counts duplicate; use output file counts and shard validation as completion signals.

## Finalize

```bash
uv run pubdelays --config config/hpc.toml validate-shards --shards 64 --format parquet
uv run pubdelays --config config/hpc.toml schema --input data/processed_data/processed.parquet
```

Final outputs default to:

```text
data/processed_data/processed.parquet
data/processed_data/processed.csv
```
