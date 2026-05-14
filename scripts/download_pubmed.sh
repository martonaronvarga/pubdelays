#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
SOURCE="${SOURCE:-baseline}"
XML_DIR="${XML_DIR:-$ROOT/data/raw_data/pubmed/xmls}"

cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m pubdelays.cli download --source "$SOURCE" --output-dir "$XML_DIR" --resume

if [[ "${USE_NIX:-1}" == "1" ]] && command -v nix >/dev/null 2>&1; then
  PIPELINE=(nix run "$ROOT#pubdelays-pipeline" --)
else
  export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
  PIPELINE=(python3 -m pubdelays.cli)
fi

"${PIPELINE[@]}" download --source "$SOURCE" --output-dir "$XML_DIR" --resume
