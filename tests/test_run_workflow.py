from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_WORKFLOW = REPO_ROOT / "scripts" / "run_workflow.py"


def run_workflow(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUN_WORKFLOW), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def full_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout}\n{result.stderr}"


def test_help_lists_key_options() -> None:
    result = run_workflow("--help")
    text = full_output(result)
    assert result.returncode == 0, text
    assert "--skills-input" in text
    assert "--bootstrap-dry-run" in text
    assert "--fetch-min-total" in text


def test_refresh_dry_run_prints_expected_steps(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = run_workflow(
        "--mode",
        "refresh",
        "--out-dir",
        str(out_dir),
        "--max-skills",
        "5",
        "--fetch-min-total",
        "1",
        "--top",
        "7",
        "--dry-run",
    )
    text = full_output(result)
    assert result.returncode == 0, text
    assert "[run]" in text
    assert "fetch_skills.py" in text
    assert "--max-skills 5" in text
    assert "--min-total 1" in text
    assert "print_stats.py" in text
    assert "--top 7" in text
    assert "[outputs] skills.json, skills.csv, latest.md" in text


def test_rejects_non_positive_top_value() -> None:
    result = run_workflow("--mode", "refresh", "--top", "0", "--dry-run")
    text = full_output(result)
    assert result.returncode != 0
    assert "must be a positive integer" in text


def test_offline_requires_existing_skills_snapshot(tmp_path: Path) -> None:
    out_dir = tmp_path / "offline"
    missing_skills = out_dir / "skills.json"
    result = run_workflow(
        "--mode",
        "offline",
        "--out-dir",
        str(out_dir),
        "--skills-input",
        str(missing_skills),
    )
    text = full_output(result)
    assert result.returncode != 0
    assert "skills snapshot not found" in text
    assert "--mode refresh" in text
