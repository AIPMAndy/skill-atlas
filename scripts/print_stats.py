#!/usr/bin/env python3
"""Print summary stats for aggregated skills data."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print stats from skills.json")
    parser.add_argument("--input", default="data/skills.json", help="Path to skills.json")
    parser.add_argument("--format", choices=["text", "markdown"], default="text")
    parser.add_argument("--top", type=int, default=10, help="Top N repos to show")
    return parser.parse_args()


def source_counts(sources: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for source in sources:
        sid = source.get("source_id", "unknown")
        count = source.get("count", 0)
        if source.get("error"):
            lines.append(f"{sid}: {count} (error)")
        elif source.get("fallback"):
            lines.append(f"{sid}: {count} (fallback={source['fallback']})")
        else:
            lines.append(f"{sid}: {count}")
    return lines


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    skills = payload.get("skills", [])
    sources = payload.get("sources", [])

    repo_counter = Counter(item.get("repo", "") for item in skills if item.get("repo"))
    top_repos = repo_counter.most_common(args.top)

    if args.format == "markdown":
        print("## Skill Atlas Summary")
        print("")
        print(f"- Generated at: `{payload.get('generated_at', '')}`")
        print(f"- Total unique skills: `{payload.get('total', 0)}`")
        print("")
        print("### Sources")
        for line in source_counts(sources):
            print(f"- {line}")
        print("")
        print(f"### Top {args.top} repositories by skill count")
        for repo, count in top_repos:
            print(f"- `{repo}`: {count}")
        return

    print(f"generated_at={payload.get('generated_at', '')}")
    print(f"total={payload.get('total', 0)}")
    print("sources:")
    for line in source_counts(sources):
        print(f"  - {line}")
    print(f"top_repos_{args.top}:")
    for repo, count in top_repos:
        print(f"  - {repo}: {count}")


if __name__ == "__main__":
    main()

