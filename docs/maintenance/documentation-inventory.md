---
title: Documentation inventory
description: Migration inventory for the Zensical documentation reorganization.
icon: octicons/checklist-16
status: new
---

# Documentation inventory

This inventory records the flat and scattered documentation found before the directory-structured Zensical reorganization. It is grounded in the current source tree, existing docs, config, tests, and CLI help.

## Existing documentation files

| Existing file | Current purpose | Decision | Target destination | Missing content to add | Grounding files |
| --- | --- | --- | --- | --- | --- |
| `docs/index.md` | Home page with a high-level reading order and SVG diagram links. | Rewrite | `docs/index.md` | Section cards, concrete pipeline map, links into new structure. | `README.md`, `config/default.toml`, `src/pubdelays/cli.py` |
| `docs/getting-started.md` | Single-page install, local, SLURM, and output checks. | Split | `docs/getting-started/index.md`, `docs/getting-started/installation.md`, `docs/getting-started/quickstart.md` | Separate Nix/uv setup from run sequence; keep commands verified against CLI. | `README.md`, `pyproject.toml`, `flake.nix`, `scripts/bootstrap_uv.sh` |
| `docs/cli.md` | Command examples grouped by stage family. | Move and extend | `docs/reference/cli.md` | Command table from actual help output; annotate default config behavior. | `src/pubdelays/cli.py`, `uv run python -m pubdelays.cli --help` |
| `docs/data-layout.md` | Runtime input, intermediate, manifest, and output paths. | Move and extend | `docs/reference/file-layout.md` | Tie paths back to `config/default.toml`; clarify generated data is not source. | `config/default.toml`, `.gitignore`, `DATA_LAYOUT.md` |
| `docs/hpc-slurm.md` | SLURM workflow and recovery notes. | Move | `docs/guides/production-or-hpc.md` | Explain array manifests, dependency chain, and dry-run checks. | `src/pubdelays/cli.py`, `src/pubdelays/slurm.py`, `config/default.toml`, `tests/test_slurm.py` |
| `docs/function-flow.md` | Function-level source map. | Move and correct | `docs/internals/pipeline.md` | Replace stale function names; add Mermaid flow and stage contract links. | `src/pubdelays/cli.py`, `src/pubdelays/transform/articles.py`, `src/pubdelays/shards.py` |
| `docs/PIPELINE_CONTEXT.md` | Agent-oriented architecture, semantics, failure modes. | Merge | `docs/concepts/architecture.md`, `docs/concepts/invariants.md`, `docs/internals/error-handling.md` | Convert into reader-facing architecture and invariants. | `src/pubdelays/*`, `tests/test_end_to_end_pipeline.py` |
| `docs/SEMANTIC_DECISIONS.md` | Stable semantic decisions. | Move | `docs/concepts/invariants.md` | Add code/test anchors and admonitions for correction hazards. | `src/pubdelays/schema.py`, `src/pubdelays/transform/articles.py`, `tests/test_transform_articles.py` |
| `docs/STAGE_CONTRACTS.md` | Stage input/output/manifest/resume contract. | Move | `docs/internals/pipeline.md` | Keep stage table, add failure boundaries and diagram. | `src/pubdelays/cli.py`, `src/pubdelays/manifest.py`, `src/pubdelays/shards.py` |
| `docs/ANALYSIS_DATASET_V1.md` | Final analysis schema table. | Move | `docs/reference/schemas.md` | Add parsed requirements, filter stages, shard naming schema. | `src/pubdelays/schema.py`, `src/pubdelays/shards.py`, `tests/test_analysis_schema.py` |
| `docs/VALIDATION_AND_BENCHMARKS.md` | Validation gates and benchmark plan. | Split | `docs/internals/validation.md`, `docs/internals/performance.md`, `docs/contributing/testing.md` | Separate correctness checks from performance recording and contributor commands. | `tests/`, `pyproject.toml`, `flake.nix` |
| `README.md` | Repository overview and full workflow. | Keep root, update links if needed | `README.md` | Point to new docs paths and Zensical commands. | Existing file, `zensical.toml` |
| `DATA_LAYOUT.md` | Top-level exact data placement. | Keep root, link to docs reference | `DATA_LAYOUT.md` | Avoid divergence from `docs/reference/file-layout.md`. | `config/default.toml` |
| `LEGACY.md` | Legacy-to-current semantics and corrections. | Keep root, link from concepts | `LEGACY.md`, `docs/concepts/invariants.md` | Link semantic corrections without duplicating legacy details. | `legacy/data_processing/*.R`, tests |
| `TASKS.md` | Work queue. | Keep root | `TASKS.md` | No content migration unless user asks. | Project maintenance only |
| `data/README.md` | Runtime data directory note. | Keep | `data/README.md` | None for docs site. | `.gitignore`, `config/default.toml` |

## Non-Markdown documentation sources

| Source | Documentation facts extracted |
| --- | --- |
| `config/default.toml` | Canonical default paths, PubMed/external raw and processed locations, transform shard defaults, aggregate outputs, SLURM resources. |
| `pyproject.toml` | Package name, Python version, runtime dependencies (`lxml`, `polars`), dev dependency group, console script `pubdelays`. |
| `src/pubdelays/cli.py` | Command names, option groups, manifest options, dry-run support, SLURM subcommands, workflow order. |
| `src/pubdelays/parser/medline.py` | Streaming XML parser, `.xml`/`.xml.gz` input, deletion records, publication date extraction. |
| `src/pubdelays/transform/articles.py` | Date filtering, `article_date` fallback to `pubdate`, journal eligibility, external joins, optional peer-review join, filter counts. |
| `src/pubdelays/schema.py` | `analysis_dataset_v1`, required parsed fields, filter stages, canonical output columns, schema validation. |
| `src/pubdelays/shards.py` | Canonical article shard filename pattern and completeness/schema validation rules. |
| `src/pubdelays/manifest.py` | SQLite manifest schema, WAL mode, row fields, statuses, checksums, worker metadata. |
| `src/pubdelays/slurm.py` | `sbatch` script construction, dependencies, status parsing, cleanup support. |
| `tests/` | Regression facts for parser behavior, transform semantics, shard validation, manifest rows, CLI dry-runs, full fixture pipeline. |
| `scripts/pipeline.sh` | Local pipeline wrapper shape and environment variables used by collaborators. |

## Unknown / to verify

- Whether the project wants a generated API reference. The current code exposes a CLI and source modules but no documented stable Python API.
- Whether `site/` should be committed. It is currently present as an untracked generated directory and should remain outside the documentation source unless repository policy changes.
- Whether Zensical should keep the existing custom CSS exactly. The current `docs/stylesheets/extra.css` is already modified in the worktree, so the reorganization should avoid overwriting it except for path-safe adjustments.
