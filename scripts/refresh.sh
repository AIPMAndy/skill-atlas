#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

python3 scripts/fetch_skills.py \
  --config config/sources.json \
  --output data/skills.json \
  --csv data/skills.csv \
  --markdown docs/latest.md "$@"

python3 scripts/print_stats.py --input data/skills.json

