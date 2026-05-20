---
title: Environment variables
description: Environment variables used by scripts and scheduler jobs.
icon: octicons/key-16
---

# Environment variables

The Python CLI primarily uses explicit arguments and TOML configuration. Environment variables appear in repository shell wrappers and generated SLURM scripts.

| Variable | Used by | Meaning |
| --- | --- | --- |
| `ROOT` | `scripts/pipeline.sh` | Repository root override; defaults to `git rev-parse --show-toplevel` or `pwd`. |
| `CONFIG` | `scripts/pipeline.sh` | Config path override; defaults to `$ROOT/config/default.toml`. |
| `RUN` | `scripts/pipeline.sh` | Command runner; defaults to `pubdelays`. Useful for `uv run pubdelays`. |
| `JOBS` | `scripts/pipeline.sh` | Local parse/transform worker count; defaults to `nproc` or `4`. |
| `SHARDS` | `scripts/pipeline.sh` | Transform shard count; defaults to `64`. |
| `PUBDELAYS_STAGE_MANIFEST` | Generated SLURM scripts | Per-task manifest path used by parse and transform array workers. |
| `SLURM_ARRAY_TASK_ID` | SLURM | Logical array task ID used by generated array commands. |

!!! note "Prefer config for durable settings"
    Use environment variables for local wrappers and scheduler context. Use `config/default.toml` or a copied TOML file for durable project paths and resource defaults.
