.PHONY: refresh refresh-fast stats organize organize-local bootstrap-collections bootstrap-collections-dry offline-local audit audit-deep

LOCAL_ROOT ?= .cache/collections

refresh:
	python3 scripts/fetch_skills.py --config config/sources.json --output data/skills.json --csv data/skills.csv --markdown docs/latest.md
	python3 scripts/print_stats.py --input data/skills.json

refresh-fast:
	python3 scripts/fetch_skills.py --config config/sources.json --output data/skills.json --csv data/skills.csv --markdown docs/latest.md --max-skills 1000
	python3 scripts/print_stats.py --input data/skills.json

stats:
	python3 scripts/print_stats.py --input data/skills.json --format markdown

organize:
	python3 scripts/organize_collections.py --seed config/collections.seed.json --skills data/skills.json --output data/collections.json --markdown docs/collections.md

organize-local:
	python3 scripts/organize_collections.py --seed config/collections.seed.json --skills data/skills.json --output data/collections.json --markdown docs/collections.md --local-root "$(LOCAL_ROOT)"

bootstrap-collections:
	python3 scripts/bootstrap_collections.py --seed config/collections.seed.json --local-root "$(LOCAL_ROOT)" --manifest data/collections.bootstrap.json

bootstrap-collections-dry:
	python3 scripts/bootstrap_collections.py --seed config/collections.seed.json --local-root "$(LOCAL_ROOT)" --manifest data/collections.bootstrap.json --dry-run

offline-local:
	$(MAKE) bootstrap-collections LOCAL_ROOT="$(LOCAL_ROOT)"
	$(MAKE) organize-local LOCAL_ROOT="$(LOCAL_ROOT)"

audit:
	python3 scripts/audit_skills.py --input data/skills.json --output data/skills.audit.json --markdown docs/skills-audit.md --min-risk-score 2

audit-deep:
	python3 scripts/audit_skills.py --input data/skills.json --output data/skills.audit.json --markdown docs/skills-audit.md --fetch-content --max-skills 500 --min-risk-score 2 --max-retries 2
