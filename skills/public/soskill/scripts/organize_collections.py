#!/usr/bin/env python3
"""Organize open-source skill collections from local snapshot data."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Organize seed collections using local skills snapshot")
    parser.add_argument("--seed", default="config/collections.seed.json", help="Path to collection seed config")
    parser.add_argument("--skills", default="data/skills.json", help="Path to aggregated skills snapshot")
    parser.add_argument("--output", default="data/collections.json", help="JSON output path")
    parser.add_argument("--markdown", default="docs/collections.md", help="Markdown output path")
    parser.add_argument(
        "--local-root",
        default="",
        help="Optional local root containing cloned collection repositories",
    )
    parser.add_argument("--samples", type=int, default=15, help="Sample skills to show for ready collections")
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_local_candidates(item: Dict[str, Any]) -> List[str]:
    candidates: List[str] = []

    for value in item.get("local_candidates", []):
        name = str(value).strip()
        if name and name not in candidates:
            candidates.append(name)

    repo = str(item.get("repo", "")).strip()
    if repo and "/" in repo:
        tail = repo.split("/")[-1]
        if tail not in candidates:
            candidates.append(tail)
    return candidates


def scan_local_collection(local_root: Optional[Path], item: Dict[str, Any], sample_limit: int) -> Dict[str, Any]:
    if not local_root:
        return {"count": 0, "scanned_dirs": [], "sample_skills": []}

    scanned_dirs: List[str] = []
    unique_paths: set[str] = set()
    samples: List[str] = []
    sample_seen: set[str] = set()

    for candidate in parse_local_candidates(item):
        candidate_path = (local_root / candidate).resolve()
        if not candidate_path.exists() or not candidate_path.is_dir():
            continue

        scanned_dirs.append(str(candidate_path))
        for skill_file in candidate_path.rglob("SKILL.md"):
            try:
                relative_path = str(skill_file.relative_to(candidate_path))
            except ValueError:
                relative_path = str(skill_file)

            unique_key = f"{candidate}:{relative_path}"
            if unique_key in unique_paths:
                continue
            unique_paths.add(unique_key)

            name = skill_file.parent.name.strip()
            if name and name not in sample_seen and len(samples) < max(0, sample_limit):
                sample_seen.add(name)
                samples.append(name)

    return {
        "count": len(unique_paths),
        "scanned_dirs": scanned_dirs,
        "sample_skills": samples,
    }


def build_collection_items(
    seed_payload: Dict[str, Any],
    skills_payload: Dict[str, Any],
    sample_limit: int,
    local_root: Optional[Path],
) -> List[Dict[str, Any]]:
    seed_items = seed_payload.get("collections", [])
    source_stats = {
        item.get("source_id", ""): item
        for item in skills_payload.get("sources", [])
        if item.get("source_id")
    }

    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for skill in skills_payload.get("skills", []):
        for source_id in skill.get("source_ids", []):
            by_source.setdefault(source_id, []).append(skill)

    organized: List[Dict[str, Any]] = []
    for item in seed_items:
        source_ids: List[str] = list(item.get("source_ids", []))
        merged: Dict[str, Dict[str, Any]] = {}

        source_status = []
        has_error = False
        for source_id in source_ids:
            stat = source_stats.get(source_id, {})
            if stat.get("error"):
                has_error = True
            source_status.append(
                {
                    "source_id": source_id,
                    "count": stat.get("count", 0),
                    "error": stat.get("error", ""),
                }
            )

            for skill in by_source.get(source_id, []):
                merged[skill["uid"]] = skill

        indexed_skills = sorted(
            merged.values(),
            key=lambda row: (str(row.get("name", "")).lower(), str(row.get("uid", "")).lower()),
        )
        indexed_sample = [
            str(row.get("name", "")) for row in indexed_skills[: max(0, sample_limit)] if row.get("name")
        ]
        indexed_count = len(indexed_skills)

        local_scan = scan_local_collection(local_root, item, sample_limit)
        local_count = int(local_scan.get("count", 0))
        count = max(indexed_count, local_count)

        if indexed_count > 0:
            status = "ready"
        elif local_count > 0:
            status = "ready-local"
        elif has_error:
            status = "blocked"
        else:
            status = "planned"

        samples = indexed_sample or list(local_scan.get("sample_skills", []))

        organized.append(
            {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "repo": item.get("repo", ""),
                "url": item.get("url", ""),
                "kind": item.get("kind", "community"),
                "language": item.get("language", ""),
                "notes": item.get("notes", ""),
                "source_ids": source_ids,
                "source_status": source_status,
                "status": status,
                "indexed_skill_count": indexed_count,
                "local_skill_count": local_count,
                "skill_count": count,
                "sample_skills": samples,
                "local_scan": {
                    "local_root": str(local_root) if local_root else "",
                    "scanned_dirs": local_scan.get("scanned_dirs", []),
                },
            }
        )

    status_rank = {"ready": 0, "ready-local": 1, "blocked": 2, "planned": 3}
    return sorted(
        organized,
        key=lambda row: (status_rank.get(str(row.get("status", "planned")), 9), -int(row.get("skill_count", 0))),
    )


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(
    path: Path,
    generated_at: str,
    collections: List[Dict[str, Any]],
    ready_indexed_unique_skills: int,
    local_scanned_skills_total: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    ready = [item for item in collections if item.get("status") in {"ready", "ready-local"}]
    blocked = [item for item in collections if item.get("status") == "blocked"]
    planned = [item for item in collections if item.get("status") == "planned"]

    lines: List[str] = []
    lines.append("# Open-source Skill Collections")
    lines.append("")
    lines.append(f"- Generated at: `{generated_at}`")
    lines.append(f"- Tracked collections: `{len(collections)}`")
    lines.append(f"- Ready: `{len(ready)}` | Blocked: `{len(blocked)}` | Planned: `{len(planned)}`")
    lines.append(f"- Indexed unique skills from ready collections: `{ready_indexed_unique_skills}`")
    lines.append(f"- Local scanned skills (non-dedup): `{local_scanned_skills_total}`")
    lines.append("")

    lines.append("## Collections Overview")
    lines.append("")
    lines.append("| Collection | Repo | Kind | Status | Indexed | Local | Skills | Notes |")
    lines.append("|---|---|---|---:|---:|---:|---:|---|")
    for item in collections:
        lines.append(
            "| "
            f"{item.get('name', '')} | "
            f"[{item.get('repo', '')}]({item.get('url', '')}) | "
            f"{item.get('kind', '')} | "
            f"{item.get('status', '')} | "
            f"{item.get('indexed_skill_count', 0)} | "
            f"{item.get('local_skill_count', 0)} | "
            f"{item.get('skill_count', 0)} | "
            f"{item.get('notes', '')} |"
        )

    lines.append("")
    lines.append("## Ready Collections")
    lines.append("")
    if not ready:
        lines.append("暂无可直接使用的集合。")
        lines.append("")
    else:
        for item in ready:
            lines.append(f"### {item.get('name', '')}")
            lines.append("")
            lines.append(f"- Repo: {item.get('repo', '')}")
            lines.append(f"- Status: {item.get('status', '')}")
            lines.append(f"- Indexed Skills: {item.get('indexed_skill_count', 0)}")
            lines.append(f"- Local Skills: {item.get('local_skill_count', 0)}")
            lines.append(f"- Effective Skills: {item.get('skill_count', 0)}")
            lines.append(f"- Source IDs: {', '.join(item.get('source_ids', []))}")
            scanned_dirs = list(item.get("local_scan", {}).get("scanned_dirs", []))
            if scanned_dirs:
                lines.append(f"- Local Dirs: {', '.join(scanned_dirs)}")
            if item.get("sample_skills"):
                lines.append(f"- Samples: {', '.join(item['sample_skills'])}")
            lines.append("")

    if blocked:
        lines.append("## Blocked Collections")
        lines.append("")
        for item in blocked:
            lines.append(f"- `{item.get('repo', '')}`: 关联 source 出错，请修复抓取后重试。")
        lines.append("")

    if planned:
        lines.append("## Planned Collections")
        lines.append("")
        for item in planned:
            lines.append(f"- `{item.get('repo', '')}`")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    seed_payload = load_json(Path(args.seed))
    skills_payload = load_json(Path(args.skills))
    local_root = Path(args.local_root).expanduser().resolve() if args.local_root else None

    collections = build_collection_items(seed_payload, skills_payload, args.samples, local_root)
    generated_at = utc_now()

    ready_source_ids = {
        source_id
        for item in collections
        if item.get("status") in {"ready", "ready-local"}
        for source_id in item.get("source_ids", [])
    }
    ready_indexed_unique_skills = len(
        {
            str(skill.get("uid", ""))
            for skill in skills_payload.get("skills", [])
            if any(source_id in ready_source_ids for source_id in skill.get("source_ids", []))
            and skill.get("uid")
        }
    )
    local_scanned_skills_total = sum(int(item.get("local_skill_count", 0)) for item in collections)

    output_payload = {
        "generated_at": generated_at,
        "seed": args.seed,
        "skills_snapshot": args.skills,
        "local_root": str(local_root) if local_root else "",
        "total_collections": len(collections),
        "collections": collections,
    }

    write_json(Path(args.output), output_payload)
    write_markdown(
        Path(args.markdown),
        generated_at,
        collections,
        ready_indexed_unique_skills,
        local_scanned_skills_total,
    )
    print(f"[done] collections organized: {len(collections)}")


if __name__ == "__main__":
    main()
