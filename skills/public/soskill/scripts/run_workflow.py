#!/usr/bin/env python3
"""Run SoSkill workflows with one command."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List


def script_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_config_path(base_dir: Path, *, preferred: str, fallback: str) -> Path:
    preferred_path = base_dir / preferred
    if preferred_path.exists():
        return preferred_path
    fallback_path = base_dir / fallback
    return fallback_path


def run_command(cmd: List[str], *, dry_run: bool) -> None:
    line = shlex.join(cmd)
    print(f"[run] {line}")
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-command SoSkill workflow runner")
    parser.add_argument(
        "--mode",
        choices=["refresh", "secure-refresh", "full", "offline"],
        default="secure-refresh",
        help="Workflow mode",
    )
    parser.add_argument(
        "--skill-dir",
        default="",
        help="Base dir containing scripts/ and references/ (or config/)",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory for generated files (default: ./soskill-output)",
    )
    parser.add_argument(
        "--local-root",
        default="",
        help="Local collections root for offline mode (default: <out-dir>/.cache/collections)",
    )
    parser.add_argument(
        "--skills-input",
        default="",
        help="Existing skills snapshot for organize/offline mode (default: <out-dir>/skills.json)",
    )
    parser.add_argument("--max-skills", type=int, default=0, help="Optional max skills for fetch")
    parser.add_argument(
        "--fetch-min-total",
        type=int,
        default=0,
        help="Minimum unique skills required by fetch (0 disables guard)",
    )
    parser.add_argument("--top", type=int, default=15, help="Top repositories to print in stats")
    parser.add_argument("--min-risk-score", type=int, default=2, help="Minimum risk score for audit output")
    parser.add_argument("--include-clean", action="store_true", help="Include clean records in audit outputs")
    parser.add_argument("--deep-audit", action="store_true", help="Fetch raw SKILL.md content during audit")
    parser.add_argument("--audit-max-skills", type=int, default=500, help="Max skills for deep audit")
    parser.add_argument("--bootstrap-dry-run", action="store_true", help="Dry-run git clone/pull in offline mode")
    parser.add_argument("--no-update", action="store_true", help="Skip git pull for existing repos in offline mode")
    parser.add_argument("--python", default="python3", help="Python executable")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    base_dir = Path(args.skill_dir).expanduser().resolve() if args.skill_dir else script_root()
    scripts_dir = base_dir / "scripts"
    if not scripts_dir.exists():
        raise SystemExit(f"scripts directory not found under: {base_dir}")

    output_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else (Path.cwd() / "soskill-output")
    output_dir.mkdir(parents=True, exist_ok=True)

    sources_path = resolve_config_path(base_dir, preferred="references/sources.json", fallback="config/sources.json")
    collections_path = resolve_config_path(
        base_dir,
        preferred="references/collections.seed.json",
        fallback="config/collections.seed.json",
    )

    if not sources_path.exists():
        raise SystemExit(f"sources config not found: {sources_path}")
    if not collections_path.exists():
        raise SystemExit(f"collections seed not found: {collections_path}")

    skills_json = output_dir / "skills.json"
    skills_csv = output_dir / "skills.csv"
    latest_md = output_dir / "latest.md"
    collections_json = output_dir / "collections.json"
    collections_md = output_dir / "collections.md"
    bootstrap_json = output_dir / "collections.bootstrap.json"
    audit_json = output_dir / "skills.audit.json"
    audit_md = output_dir / "skills-audit.md"
    skills_input = Path(args.skills_input).expanduser().resolve() if args.skills_input else skills_json

    local_root = (
        Path(args.local_root).expanduser().resolve()
        if args.local_root
        else (output_dir / ".cache" / "collections").resolve()
    )

    if args.mode == "offline" and not args.dry_run and not skills_input.exists():
        raise SystemExit(
            "skills snapshot not found: "
            f"{skills_input}\n"
            f"Run `{args.python} {scripts_dir / 'run_workflow.py'} --mode refresh --out-dir {output_dir}` first, "
            "or pass --skills-input <path>."
        )

    steps: List[List[str]] = []

    if args.mode in {"refresh", "secure-refresh", "full"}:
        fetch_cmd = [
            args.python,
            str(scripts_dir / "fetch_skills.py"),
            "--config",
            str(sources_path),
            "--output",
            str(skills_json),
            "--csv",
            str(skills_csv),
            "--markdown",
            str(latest_md),
        ]
        if args.max_skills > 0:
            fetch_cmd.extend(["--max-skills", str(args.max_skills)])
        if args.fetch_min_total > 0:
            fetch_cmd.extend(["--min-total", str(args.fetch_min_total)])
        steps.append(fetch_cmd)

        steps.append(
            [
                args.python,
                str(scripts_dir / "print_stats.py"),
                "--input",
                str(skills_json),
                "--format",
                "markdown",
                "--top",
                str(args.top),
            ]
        )

    if args.mode in {"secure-refresh", "full"}:
        audit_cmd = [
            args.python,
            str(scripts_dir / "audit_skills.py"),
            "--input",
            str(skills_json),
            "--output",
            str(audit_json),
            "--markdown",
            str(audit_md),
            "--min-risk-score",
            str(args.min_risk_score),
        ]
        if args.deep_audit:
            audit_cmd.append("--fetch-content")
            if args.audit_max_skills > 0:
                audit_cmd.extend(["--max-skills", str(args.audit_max_skills)])
        if args.include_clean:
            audit_cmd.append("--include-clean")
        steps.append(audit_cmd)

    if args.mode == "full":
        steps.append(
            [
                args.python,
                str(scripts_dir / "organize_collections.py"),
                "--seed",
                str(collections_path),
                "--skills",
                str(skills_json),
                "--output",
                str(collections_json),
                "--markdown",
                str(collections_md),
            ]
        )

    if args.mode == "offline":
        steps.append(
            [
                args.python,
                str(scripts_dir / "bootstrap_collections.py"),
                "--seed",
                str(collections_path),
                "--local-root",
                str(local_root),
                "--manifest",
                str(bootstrap_json),
            ]
        )
        if args.bootstrap_dry_run:
            steps[-1].append("--dry-run")
        if args.no_update:
            steps[-1].append("--no-update")
        steps.append(
            [
                args.python,
                str(scripts_dir / "organize_collections.py"),
                "--seed",
                str(collections_path),
                "--skills",
                str(skills_input),
                "--output",
                str(collections_json),
                "--markdown",
                str(collections_md),
                "--local-root",
                str(local_root),
            ]
        )

    print(f"[mode] {args.mode}")
    print(f"[base_dir] {base_dir}")
    print(f"[out_dir] {output_dir}")
    print(f"[skills_input] {skills_input}")
    print(f"[local_root] {local_root}")

    for cmd in steps:
        run_command(cmd, dry_run=args.dry_run)

    print("[done] workflow completed")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except KeyboardInterrupt:
        sys.exit(130)
