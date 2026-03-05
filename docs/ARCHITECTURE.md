# Architecture

## Pipeline

1. Load source config from `config/sources.json`
2. Fetch data from each source:
   - `github_tree`: parse repository tree + optional frontmatter
   - `markdown_links`: extract `SKILL.md` links from README-like pages
3. Normalize into a common record schema
4. Merge by `uid = <repo>:<path>`
5. Write outputs:
   - `data/skills.json`
   - `data/skills.csv`
   - `docs/latest.md`

## Workflow Orchestrator

- Script: `scripts/run_workflow.py`
- Modes:
  - `refresh`: fetch + stats
  - `secure-refresh`: fetch + stats + audit
  - `full`: fetch + stats + audit + collection organize
  - `offline`: bootstrap collections + local organize (requires existing skills snapshot)
- Key options:
  - `--skills-input <path>`: use existing `skills.json` for offline/organize stage
  - `--bootstrap-dry-run`: preview clone/pull actions in offline mode
  - `--top <N>`: control top repositories in stats output
- Goal: reduce multi-step command chains into one deterministic entry point.

## Collection Organize Pipeline (Offline-first)

1. (Optional) Bootstrap local repositories from seed config:
   - script: `scripts/bootstrap_collections.py`
   - output: `data/collections.bootstrap.json`
2. Load collection seed from `config/collections.seed.json`
3. Read local snapshot from `data/skills.json`
4. Build collection-level stats:
   - indexed count from `source_ids`
   - optional local scan count from `--local-root`
5. Mark collection status:
   - `ready`: has indexed skills
   - `ready-local`: no indexed skills but local scan found `SKILL.md`
   - `blocked`: source linked but source has error
   - `planned`: not indexed and no local scan results
6. Write outputs:
   - `data/collections.json`
   - `docs/collections.md`

## Skill Security Audit Pipeline

1. Load snapshot from `data/skills.json`
2. Scan metadata fields (`name` / `description`) for risk rules
3. Optional deep mode: fetch `raw_url` and scan SKILL content
4. Score and classify each skill risk level (`critical/high/medium/low/clean`)
5. Write outputs:
   - `data/skills.audit.json`
   - `docs/skills-audit.md`

## Fault Tolerance

- Each source is isolated; one source failure does not break the full run.
- `github_tree` sources can optionally use `fallback_listing_url` when API calls are rate-limited.
- Errors are preserved into `sources[]` in `skills.json` for observability.
- Collection organize flow does not require network and can continue with local snapshot only.

## Automation

GitHub Actions workflow (`.github/workflows/refresh-skills.yml`) supports:

- manual trigger (`workflow_dispatch`)
- external trigger (`repository_dispatch` with `event_type=refresh-skills`)
- scheduled refresh (every 6 hours)
