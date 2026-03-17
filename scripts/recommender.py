#!/usr/bin/env python3
"""GitHub project recommender based on user's profile and project analysis."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import urllib.request
import urllib.error


@dataclass
class GitHubRepo:
    """GitHub repository metadata."""
    name: str
    full_name: str
    description: str
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str]
    updated_at: str
    pushed_at: str
    html_url: str
    relevance_score: float = 0.0
    category: str = "other"


class GitHubClient:
    """Simple GitHub API client."""
    
    def __init__(self, token: str = ""):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
    
    def _request(self, url: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "soskill-recommender/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    
    def get_user_repos(self, username: str) -> List[GitHubRepo]:
        """Fetch all public repos for a user."""
        repos = []
        page = 1
        
        while True:
            url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}&sort=pushed"
            data = self._request(url)
            
            if not data:
                break
            
            for repo in data:
                if repo.get("fork"):
                    continue
                
                repos.append(GitHubRepo(
                    name=repo["name"],
                    full_name=repo["full_name"],
                    description=repo.get("description", ""),
                    stars=repo.get("stargazers_count", 0),
                    forks=repo.get("forks_count", 0),
                    language=repo.get("language"),
                    topics=repo.get("topics", []),
                    updated_at=repo.get("updated_at", ""),
                    pushed_at=repo.get("pushed_at", ""),
                    html_url=repo["html_url"],
                ))
            
            if len(data) < 100:
                break
            page += 1
        
        return repos


def main():
    """Main entry point."""
    client = GitHubClient()
    repos = client.get_user_repos("AIPMAndy")
    
    print(f"Found {len(repos)} repositories")
    print("\nTop 5 by stars:")
    for repo in sorted(repos, key=lambda r: -r.stars)[:5]:
        print(f"  ⭐ {repo.stars} | {repo.name} - {repo.description[:60]}...")


if __name__ == "__main__":
    main()
