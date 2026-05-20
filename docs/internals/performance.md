---
title: Performance
description: Throughput-sensitive boundaries and benchmark recording procedure.
icon: octicons/meter-16
---

# Performance

The expected workload is large enough that IO shape and worker boundaries matter. This page records performance-sensitive contracts and how to capture benchmark evidence.

## Throughput-sensitive boundaries

- XML parsing must remain streaming through `parse_medline_xml()`.
- Full-scale parser output should remain JSONL, not a single large JSON array.
- External metadata preprocessing should use Polars, not hand-rolled CSV loops.
- Local `transform-shards` should load external metadata once per shard worker, not once per PubMed XML file.
- SLURM transform work should use modulo job arrays, per-task manifests, and file outputs rather than shared worker state.
- Aggregation should scan canonical article shards and ignore `.filters.csv` sidecars.

## Benchmark record template

Benchmark reports are generated artifacts. Write them under `data/processed_data/benchmarks/` and do not commit them.

```bash
mkdir -p data/processed_data/benchmarks
REPORT="data/processed_data/benchmarks/benchmark-$(date -u +%Y%m%dT%H%M%SZ).txt"
{
  echo "# pubdelays benchmark"
  date -u
  uname -a
  python --version
  pubdelays --help | head -1
} > "$REPORT"
TIME="/usr/bin/time -v -a -o $REPORT"
```

On Linux, `/usr/bin/time -v` records elapsed time and peak RSS. On systems without GNU time, record `time -p` output plus peak RSS from the scheduler or OS monitor.

## Stage examples

```bash
$TIME pubdelays external-all --resume
$TIME pubdelays parse --jobs 16 --format jsonl --parse-mesh-subterms --resume
$TIME pubdelays transform-shards --shards 64 --jobs 16 --format parquet --resume
$TIME pubdelays aggregate-all --resume
```

Record hardware, filesystem, Python version, Polars version, Nix/uv environment, worker counts, shard counts, and SLURM settings next to timing results.
