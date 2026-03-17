#!/usr/bin/env python3
"""Optimized skill fetcher with incremental updates, caching, and quality scoring."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple
import urllib.request
import urllib.error
import urllib.parse


@dataclass
class SourceConfig:
    """Configuration for a single data source."""
    id: str
    type: str
    priority: int = 5
    weight: float = 1.0
    enabled: bool = True
    fallbacks: List[Dict] = field(default_factory=list)
    quality_indicators: Dict[str, Any] = field(default_factory=dict)
    
    # Type-specific configs
    repo: Optional[str] = None
    branch: str = "main"
    include_prefixes: List[str] = field(default_factory=list)
    readme_url: Optional[str] = None
    url: Optional[str] = None
    path: Optional[str] = None
    
    # Feature flags
    frontmatter: bool = False
    frontmatter_limit: int = 0
    enrich_from_github: bool = False
    watch: bool = False


@dataclass
class SkillRecord:
    """Enhanced skill record with quality metadata."""
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
    
    # Quality metadata
    quality_score: float = 0.0
    stars: int = 0
    forks: int = 0
    last_updated: Optional[str] = None
    created_at: Optional[str] = None
    has_tests: bool = False
    has_docs: bool = False
    security_status: str = "unknown"  # clean, warning, critical
    
    # Source metadata
    priority: int = 5
    weight: float = 1.0


class CacheManager:
    """Manages incremental caching with ETag support."""
    
    def __init__(self, cache_dir: Path = Path(".cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.meta_file = cache_dir / "cache_meta.json"
        self._meta = self._load_meta()
    
    def _load_meta(self) -> Dict:
        if self.meta_file.exists():
            return json.loads(self.meta_file.read_text())
        return {}
    
    def _save_meta(self):
        self.meta_file.write_text(json.dumps(self._meta, indent=2))
    
    def get(self, key: str, max_age_hours: int = 6) -> Optional[Dict]:
        """Get cached data if not expired."""
        if key not in self._meta:
            return None
        
        meta = self._meta[key]
        cached_at = datetime.fromisoformat(meta["cached_at"])
        age = datetime.now(timezone.utc) - cached_at
        
        if age > timedelta(hours=max_age_hours):
            return None
        
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        
        return {
            "data": json.loads(cache_file.read_text()),
            "etag": meta.get("etag"),
            "cached_at": meta["cached_at"]
        }
    
    def set(self, key: str, data: Any, etag: Optional[str] = None):
        """Cache data with optional ETag."""
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps(data, indent=2))
        
        self._meta[key] = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "etag": etag,
            "size": len(json.dumps(data))
        }
        self._save_meta()
    
    def get_etag(self, key: str) -> Optional[str]:
        return self._meta.get(key, {}).get("etag")


class GitHubClient:
    """Enhanced GitHub client with rate limiting and caching."""
    
    def __init__(self, token: str = "", cache: Optional[CacheManager] = None):
        self.token = token
        self.cache = cache
        self._rate_limit_remaining = 5000
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 10 requests per second max
    
    def _wait_for_rate_limit(self):
        """Respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        
        if self._rate_limit_remaining < 10:
            print("[warn] Approaching rate limit, slowing down...", file=sys.stderr)
            time.sleep(1.0)
    
    def _request(
        self,
        url: str,
        accept: str = "application/vnd.github+json",
        etag: Optional[str] = None
    ) -> Tuple[bytes, Optional[str], bool]:
        """Make request with caching support. Returns (data, etag, from_cache)."""
        self._wait_for_rate_limit()
        
        headers = {
            "Accept": accept,
            "User-Agent": "soskill-bot/2.0",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        if etag:
            headers["If-None-Match"] = etag
        
        req = urllib.request.Request(url=url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self._last_request_time = time.time()
                self._rate_limit_remaining = int(resp.headers.get("X-RateLimit-Remaining", 5000))
                
                new_etag = resp.headers.get("ETag")
                return resp.read(), new_etag, False
                
        except urllib.error.HTTPError as e:
            self._last_request_time = time.time()
            
            if e.code == 304 and etag:  # Not modified
                return b"", etag, True
            
            raise
    
    def get_json(self, url: str, cache_key: Optional[str] = None, max_age_hours: int = 6) -> Any:
        """Get JSON with caching."""
        etag = None
        
        if self.cache and cache_key:
            cached = self.cache.get(cache_key, max_age_hours)
            if cached:
                etag = cached["etag"]
        
        data, new_etag, from_cache = self._request(url, etag=etag)
        
        if from_cache and self.cache and cache_key:
            cached = self.cache.get(cache_key, max_age_hours)
            return cached["data"]
        
        result = json.loads(data.decode("utf-8"))
        
        if self.cache and cache_key:
            self.cache.set(cache_key, result, new_etag)
        
        return result
    
    def get_text(self, url: str) -> str:
        """Get plain text."""
        data, _, _ = self._request(url, accept="text/plain")
        return data.decode("utf-8", errors="replace")


class SourceFetcher(Protocol):
    """Protocol for source fetchers."""
    
    def fetch(self, config: SourceConfig) -> Tuple[List[SkillRecord], Dict]:
        """Fetch skills from source. Returns (records, stats)."""
        ...


class GitHubTreeFetcher:
    """Fetch skills from GitHub tree API with incremental updates."""
    
    def __init__(self, client: GitHubClient):
        self.client = client
    
    def fetch(self, config: SourceConfig) -> Tuple[List[SkillRecord], Dict]:
        cache_key = f"tree_{config.repo.replace('/', '_')}_{config.branch}"
        
        tree_url = f"https://api.github.com/repos/{config.repo}/git/trees/{config.branch}?recursive=1"
        
        try:
            tree_resp = self.client.get_json(tree_url, cache_key=cache_key, max_age_hours=6)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch tree: {e}")
        
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
            
            if config.include_prefixes and not any(
                path.startswith(prefix) for prefix in config.include_prefixes
            ):
                continue
            
            # Extract metadata
            name, description = "", ""
            if config.frontmatter and (
                config.frontmatter_limit <= 0 or enriched < config.frontmatter_limit
            ):
                raw_url = f"https://raw.githubusercontent.com/{config.repo}/{config.branch}/{path}"
                try:
                    text = self.client.get_text(raw_url)
                    name, description = self._parse_frontmatter(text)
                    enriched += 1
                except Exception:
                    pass
            
            slug = Path(path).parent.name
            record = SkillRecord(
                uid=f"{config.repo}:{path}",
                name=name or slug,
                description=description,
                slug=slug,
                repo=config.repo,
                branch=config.branch,
                path=path,
                html_url=f"https://github.com/{config.repo}/blob/{config.branch}/{path}",
                raw_url=raw_url,
                source_ids=[config.id],
                priority=config.priority,
                weight=config.weight,
            )
            records.append(record)
        
        stats = {
            "source_id": config.id,
            "type": "github_tree",
            "repo": config.repo,
            "branch": config.branch,
            "count": len(records),
            "truncated": truncated,
            "frontmatter_enriched": enriched,
            "from_cache": False,  # Will be set by caller
        }
        
        return records, stats
    
    def _parse_frontmatter(self, text: str) -> Tuple[str, str]:
        """Parse YAML frontmatter from markdown."""
        if not text.startswith("---"):
            return "", ""
        
        match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return "", ""
        
        block = match.group(1)
        name, description = "", ""
        
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            if key == "name":
                name = value
            elif key == "description":
                description = value
        
        return name, description


class MarkdownLinksFetcher:
    """Fetch skills from markdown links."""
    
    DEFAULT_REGEX = r"https://github\.com/([^/]+/[^/]+)/(?:tree|blob)/([^/]+)/([^)\\s#]+SKILL\.md)"
    
    def __init__(self, client: GitHubClient):
        self.client = client
    
    def fetch(self, config: SourceConfig) -> Tuple[List[SkillRecord], Dict]:
        text = self.client.get_text(config.readme_url)
        regex = config.readme_url or self.DEFAULT_REGEX
        
        pattern = re.compile(regex)
        seen = set()
        records: List[SkillRecord] = []
        
        for match in pattern.finditer(text):
            repo = match.group(1)
            branch = match.group(2)
            path = urllib.parse.unquote(match.group(3))
            key = (repo, branch, path)
            
            if key in seen:
                continue
            seen.add(key)
            
            slug = Path(path).parent.name
            record = SkillRecord(
                uid=f"{repo}:{path}",
                name=slug,
                description="",
                slug=slug,
                repo=repo,
                branch=branch,
                path=path,
                html_url=f"https://github.com/{repo}/blob/{branch}/{path}",
                raw_url=f"https://raw.githubusercontent.com/{repo}/{branch}/{path}",
                source_ids=[config.id],
                priority=config.priority,
                weight=config.weight,
            )
            records.append(record)
        
        # Enrich from GitHub if enabled
        if config.enrich_from_github:
            records = self._enrich_records(records)
        
        stats = {
            "source_id": config.id,
            "type": "markdown_links",
            "readme_url": config.readme_url,
            "count": len(records),
            "enriched": config.enrich_from_github,
        }
        
        return records, stats
    
    def _enrich_records(self, records: List[SkillRecord]) -> List[SkillRecord]:
        """Enrich records with GitHub metadata."""
        for record in records:
            try:
                # Fetch repo info
                api_url = f"https://api.github.com/repos/{record.repo}"
                repo_info = self.client.get_json(api_url, max_age_hours=24)
                
                record.stars = repo_info.get("stargazers_count", 0)
                record.forks = repo_info.get("forks_count", 0)
                record.last_updated = repo_info.get("updated_at")
                record.created_at = repo_info.get("created_at")
                
                # Check for tests
                record.has_tests = self._check_file_exists(
                    record.repo, record.branch, "tests"
                )
                record.has_docs = self._check_file_exists(
                    record.repo, record.branch, "docs"
                )
                
            except Exception:
                pass
        
        return records
    
    def _check_file_exists(self, repo: str, branch: str, path: str) -> bool:
        """Check if a file/directory exists in repo."""
        try:
            url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
            self.client.get_json(url, max_age_hours=168)  # Cache for a week
            return True
        except Exception:
            return False


class QualityScorer:
    """Calculate quality scores for skills."""
    
    def __init__(self, weights: Dict[str, float]):
        self.weights = weights
    
    def score(self, record: SkillRecord) -> float:
        """Calculate quality score for a skill."""
        score = 0.0
        
        # Base weight from source
        score += record.weight
        
        # Stars and forks
        score += record.stars * self.weights.get("stars", 0.001)
        score += record.forks * self.weights.get("forks", 0.002)
        
        # Recency
        if record.last_updated:
            try:
                updated = datetime.fromisoformat(record.last_updated.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - updated).days
                if age_days < 30:
                    score += self.weights.get("recent_update", 1.5)
            except Exception:
                pass
        
        # Has tests and docs
        if record.has_tests:
            score += self.weights.get("has_tests", 1.2)
        if record.has_docs:
            score += self.weights.get("has_docs", 1.1)
        
        # Security status
        if record.security_status == "clean":
            score += self.weights.get("security_audit_pass", 1.3)
        elif record.security_status == "critical":
            score *= 0.1  # Heavy penalty for critical issues
        
        return max(0.0, score)


class SkillMerger:
    """Merge skills from multiple sources with deduplication."""
    
    def merge(self, records: List[SkillRecord]) -> List[SkillRecord]:
        """Merge records by UID, keeping highest quality info."""
        merged: Dict[str, SkillRecord] = {}
        
        for record in records:
            existing = merged.get(record.uid)
            
            if not existing:
                merged[record.uid] = record
                continue
            
            # Keep better name/description
            if record.name and (not existing.name or existing.name == existing.slug):
                existing.name = record.name
            if record.description and not existing.description:
                existing.description = record.description
            
            # Merge source IDs
            if record.source_ids[0] not in existing.source_ids:
                existing.source_ids.append(record.source_ids[0])
            
            # Keep highest priority/weight
            if record.priority < existing.priority:
                existing.priority = record.priority
                existing.weight = record.weight
            
            # Keep best quality metadata
            existing.stars = max(existing.stars, record.stars)
            existing.forks = max(existing.forks, record.forks)
            
            if record.last_updated and (
                not existing.last_updated or record.last_updated > existing.last_updated
            ):
                existing.last_updated = record.last_updated
            
            existing.has_tests = existing.has_tests or record.has_tests
            existing.has_docs = existing.has_docs or record.has_docs
        
        # Sort by quality score
        return sorted(merged.values(), key=lambda r: (-r.quality_score, r.name.lower()))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fetch skills with incremental updates")
    parser.add_argument("--config", default="config/sources_v2.json")
    parser.add_argument("--output", default="data/skills_v2.json")
    parser.add_argument("--cache-dir", default=".cache")
    parser.add_argument("--github-token", default=os.getenv("GITHUB_TOKEN", ""))
    args = parser.parse_args()
    
    # Load config
    config = json.loads(Path(args.config).read_text())
    
    # Initialize components
    cache = CacheManager(Path(args.cache_dir))
    client = GitHubClient(args.github_token, cache)
    scorer = QualityScorer(config.get("scoring", {}).get("weights", {}))
    merger = SkillMerger()
    
    # Fetch from all sources
    all_records: List[SkillRecord] = []
    all_stats: List[Dict] = []
    
    fetchers = {
        "github_tree": GitHubTreeFetcher(client),
        "markdown_links": MarkdownLinksFetcher(client),
    }
    
    for source_data in config.get("sources", []):
        if not source_data.get("enabled", True):
            continue
        
        source_config = SourceConfig(**{k: v for k, v in source_data.items() if k in SourceConfig.__dataclass_fields__})
        fetcher = fetchers.get(source_config.type)
        
        if not fetcher:
            print(f"[warn] Unknown source type: {source_config.type}")
            continue
        
        try:
            records, stats = fetcher.fetch(source_config)
            
            # Calculate quality scores
            for record in records:
                record.quality_score = scorer.score(record)
            
            all_records.extend(records)
            all_stats.append(stats)
            print(f"[ok] {source_config.id}: {len(records)} skills")
            
        except Exception as e:
            print(f"[error] {source_config.id}: {e}", file=sys.stderr)
            all_stats.append({
                "source_id": source_config.id,
                "error": str(e),
                "count": 0,
            })
    
    # Merge and sort
    merged = merger.merge(all_records)
    
    # Output
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(merged),
        "sources": all_stats,
        "skills": [
            {
                **{k: v for k, v in record.__dict__.items() if v is not None},
                "quality_score": round(record.quality_score, 2),
            }
            for record in merged
        ],
    }
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False))
    
    print(f"\n[done] Total: {len(merged)} unique skills")
    print(f"[done] Output: {args.output}")


    main()


if __name__ == "__main__":
    main()