#!/usr/bin/env bash
#SBATCH --job-name=pubdelays-aggregate
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
CONFIG="${CONFIG:-$ROOT/config/default.toml}"
RUN="${RUN:-pubdelays-pipeline}"

"$RUN" --config "$CONFIG" aggregate-all --resume
