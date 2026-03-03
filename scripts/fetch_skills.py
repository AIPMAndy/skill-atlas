#!/usr/bin/env python3
"""Fetch and aggregate skills from multiple sources."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_LINK_REGEX = (
    r"https://github\.com/(?P<repo>[^/]+/[^/]+)/(?:tree|blob)/"
    r"(?P<branch>[^/]+)/(?P<path>[^)\s#]+SKILL\.md)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class GitHubClient:
    def __init__(self, token: str = "") -> None:
        self.token = token

    def _request(self, url: str, accept: str) -> bytes:
        headers = {
            "Accept": accept,
            "User-Agent": "skill-atlas-bot/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(url=url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:200]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error for {url}: {exc}") from exc

    def get_json(self, url: str) -> Any:
        raw = self._request(url, "application/vnd.github+json")
        return json.loads(raw.decode("utf-8"))

    def get_text(self, url: str) -> str:
        raw = self._request(url, "text/plain")
        return raw.decode("utf-8", errors="replace")


@dataclass
class SkillRecord:
    uid: str
    name: str
    description: str
    slug: str
    repo: str
    branch: str
    path: str
    html_url: str
    raw_url: str
    source_ids: List[str]


def parse_frontmatter(text: str) -> Tuple[str, str]:
    if not text.startswith("---"):
        return "", ""

    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return "", ""

    block = match.group(1)
    name = ""
    description = ""

    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key == "name":
            name = value
        elif key == "description":
            description = value

    return name, description


def make_record(
    *,
    source_id: str,
    repo: str,
    branch: str,
    path: str,
    name: str,
    description: str,
) -> SkillRecord:
    slug = Path(path).parent.name
    final_name = name or slug
    uid = f"{repo}:{path}"
    html_url = f"https://github.com/{repo}/blob/{branch}/{path}"
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    return SkillRecord(
        uid=uid,
        name=final_name,
        description=description,
        slug=slug,
        repo=repo,
        branch=branch,
        path=path,
        html_url=html_url,
        raw_url=raw_url,
        source_ids=[source_id],
    )


def collect_from_github_tree(
    client: GitHubClient,
    source: Dict[str, Any],
) -> Tuple[List[SkillRecord], Dict[str, Any]]:
    source_id = source["id"]
    repo = source["repo"]
    branch = source.get("branch", "main")
    include_prefixes = source.get("include_prefixes", [])
    exclude_prefixes = source.get("exclude_prefixes", [])
    frontmatter = bool(source.get("frontmatter", False))
    frontmatter_limit = int(source.get("frontmatter_limit", 0))

    tree_url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    tree_resp = client.get_json(tree_url)
    entries = tree_resp.get("tree", [])
    truncated = bool(tree_resp.get("truncated", False))

    records: List[SkillRecord] = []
    enriched = 0

    for entry in entries:
        if entry.get("type") != "blob":
            continue

        path = entry.get("path", "")
        if not path.endswith("SKILL.md"):
            continue

        if include_prefixes and not any(path.startswith(prefix) for prefix in include_prefixes):
            continue

        if exclude_prefixes and any(path.startswith(prefix) for prefix in exclude_prefixes):
            continue

        name = ""
        description = ""
        if frontmatter and (frontmatter_limit <= 0 or enriched < frontmatter_limit):
            raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
            try:
                text = client.get_text(raw_url)
                name, description = parse_frontmatter(text)
                enriched += 1
            except Exception:
                pass

        records.append(
            make_record(
                source_id=source_id,
                repo=repo,
                branch=branch,
                path=path,
                name=name,
                description=description,
            )
        )

    stats = {
        "source_id": source_id,
        "type": "github_tree",
        "repo": repo,
        "branch": branch,
        "count": len(records),
        "truncated": truncated,
        "frontmatter_enriched": enriched,
    }
    return records, stats


def collect_from_markdown_links(
    client: GitHubClient,
    source: Dict[str, Any],
) -> Tuple[List[SkillRecord], Dict[str, Any]]:
    source_id = source["id"]
    readme_url = source["readme_url"]
    regex = source.get("link_regex", DEFAULT_LINK_REGEX)

    text = client.get_text(readme_url)
    pattern = re.compile(regex)
    seen = set()
    records: List[SkillRecord] = []

    for match in pattern.finditer(text):
        repo = match.group("repo")
        branch = match.group("branch")
        path = urllib.parse.unquote(match.group("path"))
        key = (repo, branch, path)
        if key in seen:
            continue
        seen.add(key)

        records.append(
            make_record(
                source_id=source_id,
                repo=repo,
                branch=branch,
                path=path,
                name="",
                description="",
            )
        )

    stats = {
        "source_id": source_id,
        "type": "markdown_links",
        "readme_url": readme_url,
        "count": len(records),
    }
    return records, stats


def collect_from_github_listing_fallback(
    client: GitHubClient,
    source: Dict[str, Any],
) -> Tuple[List[SkillRecord], Dict[str, Any]]:
    source_id = source["id"]
    repo = source["repo"]
    branch = source.get("branch", "main")
    include_prefixes = source.get("include_prefixes", [])
    frontmatter = bool(source.get("frontmatter", False))
    frontmatter_limit = int(source.get("frontmatter_limit", 0))
    listing_url = source.get("fallback_listing_url", "")

    if not listing_url:
        raise RuntimeError("fallback_listing_url is not configured")
    if not include_prefixes:
        raise RuntimeError("include_prefixes is required for listing fallback")

    html = client.get_text(listing_url)
    unique_paths: set[str] = set()

    for prefix in include_prefixes:
        clean_prefix = prefix.rstrip("/")
        tree_pattern = re.compile(
            rf'href="/{re.escape(repo)}/tree/{re.escape(branch)}/{re.escape(clean_prefix)}/([^"/?#]+)"'
        )
        blob_pattern = re.compile(
            rf'href="/{re.escape(repo)}/blob/{re.escape(branch)}/{re.escape(clean_prefix)}/([^"/?#]+)/SKILL\.md"'
        )

        for match in tree_pattern.finditer(html):
            unique_paths.add(f"{clean_prefix}/{match.group(1)}/SKILL.md")

        for match in blob_pattern.finditer(html):
            unique_paths.add(f"{clean_prefix}/{match.group(1)}/SKILL.md")

    if not unique_paths:
        raise RuntimeError("No SKILL paths found from fallback listing")

    enriched = 0
    records: List[SkillRecord] = []
    for path in sorted(unique_paths):
        name = ""
        description = ""
        if frontmatter and (frontmatter_limit <= 0 or enriched < frontmatter_limit):
            raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
            try:
                text = client.get_text(raw_url)
                name, description = parse_frontmatter(text)
                enriched += 1
            except Exception:
                pass

        records.append(
            make_record(
                source_id=source_id,
                repo=repo,
                branch=branch,
                path=path,
                name=name,
                description=description,
            )
        )

    stats = {
        "source_id": source_id,
        "type": "github_tree",
        "repo": repo,
        "branch": branch,
        "count": len(records),
        "truncated": False,
        "frontmatter_enriched": enriched,
        "fallback": "html_listing",
    }
    return records, stats


def merge_records(records: Iterable[SkillRecord]) -> List[SkillRecord]:
    merged: Dict[str, SkillRecord] = {}
    for record in records:
        existing = merged.get(record.uid)
        if not existing:
            merged[record.uid] = record
            continue

        if record.name and (not existing.name or existing.name == existing.slug):
            existing.name = record.name
        if record.description and not existing.description:
            existing.description = record.description
        if record.source_ids[0] not in existing.source_ids:
            existing.source_ids.append(record.source_ids[0])

    return sorted(merged.values(), key=lambda item: (item.name.lower(), item.uid.lower()))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, records: List[SkillRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "uid",
        "name",
        "description",
        "slug",
        "repo",
        "branch",
        "path",
        "html_url",
        "raw_url",
        "source_ids",
    ]
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "uid": record.uid,
                    "name": record.name,
                    "description": record.description,
                    "slug": record.slug,
                    "repo": record.repo,
                    "branch": record.branch,
                    "path": record.path,
                    "html_url": record.html_url,
                    "raw_url": record.raw_url,
                    "source_ids": ",".join(record.source_ids),
                }
            )


def write_markdown(path: Path, generated_at: str, stats: List[Dict[str, Any]], records: List[SkillRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Skill Atlas Snapshot")
    lines.append("")
    lines.append(f"- Generated at: `{generated_at}`")
    lines.append(f"- Total unique skills: `{len(records)}`")
    lines.append("")

    lines.append("## Source Coverage")
    lines.append("")
    lines.append("| Source | Type | Count | Notes |")
    lines.append("|---|---:|---:|---|")
    for item in stats:
        notes = []
        if item.get("error"):
            notes.append(f"error={item['error']}")
        if item.get("repo"):
            notes.append(item["repo"])
        if item.get("fallback"):
            notes.append(f"fallback={item['fallback']}")
        if item.get("truncated"):
            notes.append("tree-truncated")
        if item.get("frontmatter_enriched"):
            notes.append(f"frontmatter={item['frontmatter_enriched']}")
        lines.append(
            f"| {item['source_id']} | {item['type']} | {item['count']} | {'; '.join(notes)} |"
        )

    lines.append("")
    lines.append("## Sample Skills (Top 100)")
    lines.append("")
    lines.append("| Name | Source | Link |")
    lines.append("|---|---|---|")
    for record in records[:100]:
        source = ",".join(record.source_ids)
        lines.append(f"| {record.name} | {source} | [open]({record.html_url}) |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and aggregate skills from multiple sources")
    parser.add_argument("--config", default="config/sources.json", help="Path to sources config")
    parser.add_argument("--output", default="data/skills.json", help="JSON output path")
    parser.add_argument("--csv", default="data/skills.csv", help="CSV output path")
    parser.add_argument("--markdown", default="docs/latest.md", help="Markdown summary path")
    parser.add_argument("--max-skills", type=int, default=0, help="Optional max number of unique skills")
    parser.add_argument("--github-token", default="", help="GitHub token (fallback to GITHUB_TOKEN env)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    sources = config.get("sources", [])
    if not sources:
        raise SystemExit("No sources configured")

    token = args.github_token or os.getenv("GITHUB_TOKEN", "") or os.getenv("GH_TOKEN", "")
    client = GitHubClient(token=token)

    all_records: List[SkillRecord] = []
    stats: List[Dict[str, Any]] = []

    for source in sources:
        source_type = source.get("type")
        try:
            if source_type == "github_tree":
                records, source_stats = collect_from_github_tree(client, source)
            elif source_type == "markdown_links":
                records, source_stats = collect_from_markdown_links(client, source)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            all_records.extend(records)
            stats.append(source_stats)
            print(f"[ok] {source['id']}: {len(records)}")
        except Exception as exc:
            message = str(exc).replace("\n", " ")[:220]
            if source_type == "github_tree" and source.get("fallback_listing_url"):
                try:
                    records, source_stats = collect_from_github_listing_fallback(client, source)
                    source_stats["warning"] = message
                    all_records.extend(records)
                    stats.append(source_stats)
                    print(
                        f"[ok] {source['id']}: {len(records)} (fallback html listing)",
                        file=sys.stderr,
                    )
                    continue
                except Exception as fallback_exc:
                    fallback_message = str(fallback_exc).replace("\n", " ")[:180]
                    message = f"{message}; fallback_failed={fallback_message}"

            stats.append(
                {
                    "source_id": source.get("id", "unknown"),
                    "type": source_type or "unknown",
                    "count": 0,
                    "error": message,
                }
            )
            print(f"[warn] {source.get('id', 'unknown')}: {message}", file=sys.stderr)

    merged = merge_records(all_records)
    if args.max_skills > 0:
        merged = merged[: args.max_skills]

    generated_at = utc_now()
    payload = {
        "generated_at": generated_at,
        "total": len(merged),
        "sources": stats,
        "skills": [record.__dict__ for record in merged],
    }

    write_json(Path(args.output), payload)
    write_csv(Path(args.csv), merged)
    write_markdown(Path(args.markdown), generated_at, stats, merged)
    print(f"[done] total unique skills: {len(merged)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
