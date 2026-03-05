---
name: soskill
description: Aggregate and analyze Codex/OpenClaw skills across GitHub sources with deterministic scripts. Use when tasks involve fetching SKILL.md indexes from official or community repositories, generating skills snapshots (JSON/CSV/Markdown), printing source and repository statistics, bootstrapping local collection clones, or organizing collection coverage reports.
---

# Soskill

## Overview
Use this skill to build and maintain a structured skill index from multiple GitHub sources.

## Quick Start
Run from any directory and keep outputs outside the skill folder.

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/soskill"
OUT_DIR="${PWD}/soskill-output"
mkdir -p "$OUT_DIR"

python3 "$SKILL_DIR/scripts/fetch_skills.py" \
  --config "$SKILL_DIR/references/sources.json" \
  --output "$OUT_DIR/skills.json" \
  --csv "$OUT_DIR/skills.csv" \
  --markdown "$OUT_DIR/latest.md"

python3 "$SKILL_DIR/scripts/print_stats.py" --input "$OUT_DIR/skills.json"
```

Set `GITHUB_TOKEN` (or `GH_TOKEN`) when you need higher GitHub API limits.

## Workflow Selection
- Refresh aggregated skill index: run `scripts/fetch_skills.py`.
- Print quick totals and top repositories: run `scripts/print_stats.py`.
- Build collection readiness report from index data: run `scripts/organize_collections.py`.
- Clone/pull collection repos for offline scanning: run `scripts/bootstrap_collections.py`.

## Task Playbooks

### 1. Fetch and Aggregate Skills
```bash
python3 "$SKILL_DIR/scripts/fetch_skills.py" \
  --config "$SKILL_DIR/references/sources.json" \
  --output "$OUT_DIR/skills.json" \
  --csv "$OUT_DIR/skills.csv" \
  --markdown "$OUT_DIR/latest.md"
```

Use `--max-skills <N>` to do a faster bounded run.

### 2. Print Summary Stats
```bash
python3 "$SKILL_DIR/scripts/print_stats.py" \
  --input "$OUT_DIR/skills.json" \
  --format markdown \
  --top 15
```

### 3. Organize Collection Coverage
```bash
python3 "$SKILL_DIR/scripts/organize_collections.py" \
  --seed "$SKILL_DIR/references/collections.seed.json" \
  --skills "$OUT_DIR/skills.json" \
  --output "$OUT_DIR/collections.json" \
  --markdown "$OUT_DIR/collections.md"
```

To include local clone scanning, add `--local-root <path>`.

### 4. Bootstrap Local Collections
```bash
python3 "$SKILL_DIR/scripts/bootstrap_collections.py" \
  --seed "$SKILL_DIR/references/collections.seed.json" \
  --local-root "$OUT_DIR/.cache/collections" \
  --manifest "$OUT_DIR/collections.bootstrap.json"
```

Use `--dry-run` to preview clone/pull actions without changing local repositories.

## References
- `references/sources.json`: source definitions for index fetching.
- `references/collections.seed.json`: tracked collection metadata and source mapping.
- `references/architecture.md`: pipeline structure and design intent.
- `references/collections.md`: collection status model and output semantics.
