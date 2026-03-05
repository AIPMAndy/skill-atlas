#!/usr/bin/env python3
"""Bootstrap local open-source collection repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class BootstrapResult:
    collection_id: str
    repo: str
    url: str
    local_dir: str
    action: str
    status: str
    skill_count: int
    error: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clone or update collection repositories locally")
    parser.add_argument("--seed", default="config/collections.seed.json", help="Path to collection seed config")
    parser.add_argument("--local-root", default=".cache/collections", help="Local root for cloned repositories")
    parser.add_argument(
        "--manifest",
        default="data/collections.bootstrap.json",
        help="Output manifest path for bootstrap status",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print actions, do not run git commands")
    parser.add_argument("--no-update", action="store_true", help="Skip git pull for existing repositories")
    return parser.parse_args()


def load_seed(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Seed file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_dir_name(name: str) -> str:
    cleaned = name.strip().replace("/", "-").replace("\\", "-").replace(" ", "-")
    return cleaned or "collection"


def choose_local_dir_name(item: Dict[str, Any], used_names: Set[str]) -> str:
    candidates: List[str] = []
    for candidate in item.get("local_candidates", []):
        value = sanitize_dir_name(str(candidate))
        if value and value not in candidates:
            candidates.append(value)

    repo = str(item.get("repo", "")).strip()
    if repo and "/" in repo:
        value = sanitize_dir_name(repo.split("/")[-1])
        if value and value not in candidates:
            candidates.append(value)
    elif repo:
        value = sanitize_dir_name(repo)
        if value and value not in candidates:
            candidates.append(value)

    fallback = sanitize_dir_name(str(item.get("id", "collection")))
    if fallback not in candidates:
        candidates.append(fallback)

    for candidate in candidates:
        if candidate not in used_names:
            return candidate

    index = 2
    base = candidates[0] if candidates else "collection"
    while f"{base}-{index}" in used_names:
        index += 1
    return f"{base}-{index}"


def run_command(cmd: List[str], cwd: Path | None = None) -> Tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def count_skill_files(repo_dir: Path) -> int:
    if not repo_dir.exists():
        return 0
    return sum(1 for _ in repo_dir.rglob("SKILL.md"))


def bootstrap_collection(
    item: Dict[str, Any],
    local_root: Path,
    dir_name: str,
    *,
    dry_run: bool,
    update_existing: bool,
) -> BootstrapResult:
    collection_id = str(item.get("id", ""))
    repo = str(item.get("repo", ""))
    url = str(item.get("url", "")).strip()

    target_dir = local_root / dir_name
    action = "noop"
    status = "ok"
    error = ""

    if not url:
        return BootstrapResult(
            collection_id=collection_id,
            repo=repo,
            url=url,
            local_dir=str(target_dir),
            action="skip",
            status="error",
            skill_count=0,
            error="missing url",
        )

    if target_dir.exists() and (target_dir / ".git").exists():
        if update_existing:
            action = "pull"
            if not dry_run:
                code, _, stderr = run_command(["git", "-C", str(target_dir), "pull", "--ff-only"])
                if code != 0:
                    status = "error"
                    error = stderr.strip()[:300]
        else:
            action = "keep"
    elif target_dir.exists() and not (target_dir / ".git").exists():
        action = "skip"
        status = "error"
        error = "target exists but is not a git repository"
    else:
        action = "clone"
        if not dry_run:
            code, _, stderr = run_command(["git", "clone", "--depth", "1", url, str(target_dir)])
            if code != 0:
                status = "error"
                error = stderr.strip()[:300]

    skill_count = 0 if dry_run else count_skill_files(target_dir)
    return BootstrapResult(
        collection_id=collection_id,
        repo=repo,
        url=url,
        local_dir=str(target_dir),
        action=action,
        status=status,
        skill_count=skill_count,
        error=error,
    )


def write_manifest(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    seed = load_seed(Path(args.seed))
    collections: List[Dict[str, Any]] = list(seed.get("collections", []))
    if not collections:
        raise SystemExit("No collections configured")

    local_root = Path(args.local_root).expanduser().resolve()
    if not args.dry_run:
        local_root.mkdir(parents=True, exist_ok=True)

    results: List[BootstrapResult] = []
    used_names: Set[str] = set()
    for item in collections:
        dir_name = choose_local_dir_name(item, used_names)
        used_names.add(dir_name)
        result = bootstrap_collection(
            item,
            local_root,
            dir_name,
            dry_run=args.dry_run,
            update_existing=(not args.no_update),
        )
        results.append(result)

    payload = {
        "generated_at": utc_now(),
        "seed": args.seed,
        "local_root": str(local_root),
        "dry_run": bool(args.dry_run),
        "update_existing": not bool(args.no_update),
        "total": len(results),
        "ok": sum(1 for row in results if row.status == "ok"),
        "error": sum(1 for row in results if row.status == "error"),
        "collections": [row.__dict__ for row in results],
    }

    write_manifest(Path(args.manifest), payload)

    for row in results:
        base = f"[{row.status}] {row.collection_id}: {row.action} -> {row.local_dir}"
        if row.status == "ok":
            if args.dry_run:
                print(base)
            else:
                print(f"{base} (skills={row.skill_count})")
        else:
            print(f"{base} | {row.error}")

    print(f"[done] bootstrap collections: total={payload['total']} ok={payload['ok']} error={payload['error']}")


if __name__ == "__main__":
    main()
