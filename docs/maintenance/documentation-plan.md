---
title: Documentation migration plan
description: Patch plan and validation notes for the directory-structured Zensical documentation site.
icon: octicons/project-roadmap-16
status: new
---

# Documentation migration plan

## Goal

Convert the current flat `docs/` tree into a Zensical site organized by reader intent: getting started, concepts, guides, reference, internals, contributing, and maintenance. Pages must be grounded in repository facts from source code, configuration, tests, scripts, CLI help, and existing documentation.

## Patch plan

1. Create maintenance records.
    - Add `docs/maintenance/documentation-inventory.md`.
    - Add this migration plan before broader edits.
2. Move or split flat pages into sections.
    - Move `docs/getting-started.md` to `docs/getting-started/quickstart.md` and add a section index plus installation page.
    - Move `docs/cli.md` to `docs/reference/cli.md`.
    - Move `docs/data-layout.md` to `docs/reference/file-layout.md`.
    - Move `docs/hpc-slurm.md` to `docs/guides/production-or-hpc.md`.
    - Move `docs/function-flow.md` to `docs/internals/pipeline.md`.
    - Move `docs/ANALYSIS_DATASET_V1.md` to `docs/reference/schemas.md`.
    - Merge `docs/STAGE_CONTRACTS.md`, `docs/PIPELINE_CONTEXT.md`, `docs/SEMANTIC_DECISIONS.md`, and `docs/VALIDATION_AND_BENCHMARKS.md` into the relevant new pages, then remove or replace the old flat files.
3. Add section landing pages.
    - `docs/concepts/index.md`
    - `docs/guides/index.md`
    - `docs/reference/index.md`
    - `docs/internals/index.md`
    - `docs/contributing/index.md`
4. Extend concrete content.
    - Architecture: module boundaries, data/control flow, manifests, failure boundaries.
    - CLI reference: commands and examples from actual help output and `src/pubdelays/cli.py`.
    - Data/model reference: default paths from `config/default.toml`, final columns from `src/pubdelays/schema.py`, shard rules from `src/pubdelays/shards.py`.
    - Development docs: Nix/uv commands from `README.md`, `pyproject.toml`, and existing validation docs.
5. Add maintainable diagrams.
    - Store reusable Mermaid sources under `docs/assets/diagrams/`.
    - Use Mermaid for pipeline, stage lifecycle, and SLURM workflow diagrams.
    - Do not replace logo/favicon assets; do not add opaque SVG diagrams.
6. Update Zensical configuration.
    - Point explicit nav to new directories.
    - Keep only Markdown extensions used by the new pages.
    - Enable Mermaid through `pymdownx.superfences` custom fences.
    - Keep `content.code.copy`, `content.code.select`, and add `content.code.annotate` because annotated code blocks are used.
7. Validate.
    - Run the available docs build command (`uv run zensical build`, then `uv run zensical build --strict` if accepted by the installed CLI).
    - Run link/navigation checks via the strict build.
    - Run `git diff --check`.
    - Run narrow smoke commands available in the current environment. If local Python lacks runtime dependencies, use `uv run`.

## Semantic invariants at risk

- The documented CLI name is `pubdelays`, from `pyproject.toml` `[project.scripts]`. Do not introduce the old `pubdelays-pipeline` name except as historical context.
- `article_date` fallback to `pubdate` is an intentional correction covered by transform tests; do not document missing `article_date` as a drop condition.
- Ceased journals are filtered against article publication year, not current year or received year.
- JSONL is the full-scale parse format; JSON is only for small fixtures/interoperability.
- Article shard names encode both shard index and total shard count: `articles-shard-00000-of-00064.parquet`.
- SLURM array tasks should use per-task manifests and later `manifest collect`; do not suggest concurrent shared-progress files.
- Generated data under `data/raw_data/`, `data/temp_data/`, `data/processed_data/`, and `data/manifests/` should not be committed.

## Validation log

Record commands here as they are run.

| Command | Result | Notes |
| --- | --- | --- |
| `PYTHONPATH=src python -m pubdelays.cli --help` | Failed before edits | Local Python environment lacked `polars`; use `uv run` for CLI inspection. |
| `uv run python -m pubdelays.cli --help` | Passed before edits | Confirmed command list and main workflow. |
| `uv run python -m pubdelays.cli transform-shards --help` | Passed before edits | Confirmed sharding options, dry-run, external inputs, manifest flags. |
| `uv run python -m pubdelays.cli slurm workflow --help` | Passed before edits | Confirmed workflow options and array throttling/max-size flags. |
| `uv run zensical build` | Failed after first config edit, then passed | Initial failure was an invalid superfences `format` string and front-matter icon paths using `octicons-...`; fixed to `pymdownx.superfences.fence_code_format` and `octicons/...`. |
| `uv run zensical build --strict` | Passed | Strict Zensical build reported no issues. |
| Custom Python Markdown link check over `docs/**/*.md` | Passed | Verified relative links resolve to existing source files/assets. |
| `git diff --check` | Passed | Removed trailing whitespace from existing CSS. |
| `uv run python -m pubdelays.cli schema` | Passed | Printed `analysis_dataset_v1` columns from current source. |
| `git ls-files | rg '(__pycache__|\.pyc$|\.pytest_cache|data/(raw_data|temp_data|processed_data|manifests)|^result)' || true` | Passed | No tracked generated/cache files matched the repository hygiene pattern. |

## Pre-existing worktree state

The repository was dirty before this migration began. Notable pre-existing changes included modified docs pages/assets/CSS, deleted `mkdocs.yml`, modified `pyproject.toml`/`uv.lock`, untracked `.github/`, `site/`, `zensical.toml`, and a TSV data file. This documentation migration must not revert unrelated user changes.
