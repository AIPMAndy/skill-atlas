#!/usr/bin/env python3
"""Audit skills snapshot for potentially unsafe patterns."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class RiskRule:
    rule_id: str
    category: str
    severity: str
    weight: int
    description: str
    pattern: Pattern[str]


SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

RULES: List[RiskRule] = [
    RiskRule(
        rule_id="remote_exec_pipe",
        category="command_execution",
        severity="critical",
        weight=6,
        description="Remote script piping to shell detected.",
        pattern=re.compile(
            r"(curl|wget)[^\n|]{0,180}\|\s*(bash|sh)\b|Invoke-Expression|IEX\s*\(",
            re.IGNORECASE,
        ),
    ),
    RiskRule(
        rule_id="destructive_delete",
        category="destructive_command",
        severity="critical",
        weight=5,
        description="Potentially destructive delete command detected.",
        pattern=re.compile(
            r"\brm\s+-rf\b|\bdel\s+/f\s+/s\s+/q\b|\bformat\s+[a-z]:\b",
            re.IGNORECASE,
        ),
    ),
    RiskRule(
        rule_id="system_rewrite",
        category="destructive_command",
        severity="high",
        weight=4,
        description="History rewrite or force push command detected.",
        pattern=re.compile(
            r"\bgit\s+reset\s+--hard\b|\bgit\s+clean\s+-fdx\b|\bgit\s+push\s+--force\b",
            re.IGNORECASE,
        ),
    ),
    RiskRule(
        rule_id="suspicious_privilege",
        category="privilege",
        severity="high",
        weight=4,
        description="Privilege escalation or weak permission command detected.",
        pattern=re.compile(
            r"\bsudo\b|\bchmod\s+777\b|\bchown\s+root\b|\bSet-ExecutionPolicy\b",
            re.IGNORECASE,
        ),
    ),
    RiskRule(
        rule_id="credential_exfiltration",
        category="data_exfiltration",
        severity="critical",
        weight=5,
        description="Potential credential exfiltration language detected.",
        pattern=re.compile(
            r"(steal|exfiltrat|leak|upload|send|post)[^\n]{0,90}(token|api[_\-\s]?key|secret|password|cookie)",
            re.IGNORECASE,
        ),
    ),
    RiskRule(
        rule_id="credential_collection",
        category="credential_handling",
        severity="high",
        weight=4,
        description="Requests for sensitive credentials detected.",
        pattern=re.compile(
            r"(provide|share|input|paste|enter)[^\n]{0,70}(api[_\-\s]?key|token|secret|password|private key)",
            re.IGNORECASE,
        ),
    ),
    RiskRule(
        rule_id="prompt_injection_override",
        category="prompt_injection",
        severity="high",
        weight=4,
        description="Prompt override / jailbreak style instruction detected.",
        pattern=re.compile(
            r"ignore\s+(all\s+)?(previous|above)\s+instructions|bypass\s+(safety|policy)|jailbreak|do anything now",
            re.IGNORECASE,
        ),
    ),
    RiskRule(
        rule_id="malware_terms",
        category="malicious_intent",
        severity="high",
        weight=4,
        description="Malware/phishing/ransomware related operation detected.",
        pattern=re.compile(
            r"keylogger|ransomware|phishing|credential\s+harvest|payload\s+delivery|backdoor",
            re.IGNORECASE,
        ),
    ),
    RiskRule(
        rule_id="eval_exec_usage",
        category="code_execution",
        severity="medium",
        weight=3,
        description="Dynamic code execution primitive detected.",
        pattern=re.compile(r"\beval\s*\(|\bexec\s*\(|subprocess\.Popen", re.IGNORECASE),
    ),
    RiskRule(
        rule_id="disable_security",
        category="security_bypass",
        severity="high",
        weight=4,
        description="Instructions to disable security protections detected.",
        pattern=re.compile(
            r"disable\s+(security|antivirus|defender|firewall)|turn\s+off\s+(security|defender|firewall)",
            re.IGNORECASE,
        ),
    ),
]

NEGATION_HINTS = [
    "do not",
    "don't",
    "never",
    "avoid",
    "禁止",
    "不要",
    "避免",
    "forbidden",
]


class HttpClient:
    def __init__(self, token: str = "", timeout: float = 20.0, max_retries: int = 1, retry_delay: float = 1.0):
        self.token = token.strip()
        self.timeout = max(1.0, float(timeout))
        self.max_retries = max(0, int(max_retries))
        self.retry_delay = max(0.0, float(retry_delay))

    def get_text(self, url: str) -> str:
        headers = {
            "Accept": "text/plain",
            "User-Agent": "soskill-audit/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(url=url, headers=headers)
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as exc:
                if exc.code in {403, 429, 500, 502, 503, 504} and attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2**attempt))
                    continue
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {exc.code}: {body[:180]}") from exc
            except urllib.error.URLError as exc:
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2**attempt))
                    continue
                raise RuntimeError(f"Network error: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit aggregated skills for suspicious content patterns")
    parser.add_argument("--input", default="data/skills.json", help="Path to skills.json")
    parser.add_argument("--output", default="data/skills.audit.json", help="Audit JSON output path")
    parser.add_argument("--markdown", default="docs/skills-audit.md", help="Audit markdown output path")
    parser.add_argument("--max-skills", type=int, default=0, help="Optional max skills to scan (0 = all)")
    parser.add_argument("--min-risk-score", type=int, default=2, help="Only emit records with score >= value")
    parser.add_argument("--max-findings-per-rule", type=int, default=2, help="Max findings per rule per skill")
    parser.add_argument("--fetch-content", action="store_true", help="Fetch raw SKILL.md content for deep audit")
    parser.add_argument("--include-clean", action="store_true", help="Include clean/low-risk records in output")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout seconds when fetching content")
    parser.add_argument("--max-retries", type=int, default=1, help="HTTP retry attempts for content fetching")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="HTTP retry base delay seconds")
    parser.add_argument("--github-token", default="", help="GitHub token (fallback to GITHUB_TOKEN/GH_TOKEN)")
    return parser.parse_args()


def load_skills(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Input file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Invalid skills payload: expected object")
    return payload


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def snippet_around(text: str, start: int, end: int, window: int = 70) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return normalize_space(text[left:right])[:220]


def is_negated(text: str, start: int) -> bool:
    window = normalize_space(text[max(0, start - 80) : start].lower())
    return any(hint in window for hint in NEGATION_HINTS)


def classify_level(score: int, max_severity_rank: int) -> str:
    if max_severity_rank >= SEVERITY_RANK["critical"] or score >= 10:
        return "critical"
    if max_severity_rank >= SEVERITY_RANK["high"] or score >= 7:
        return "high"
    if max_severity_rank >= SEVERITY_RANK["medium"] or score >= 4:
        return "medium"
    if score > 0:
        return "low"
    return "clean"


def scan_text(text: str, max_findings_per_rule: int) -> Tuple[int, str, List[Dict[str, Any]], Set[str]]:
    findings: List[Dict[str, Any]] = []
    matched_rule_ids: Set[str] = set()
    score = 0
    max_severity_rank = 0

    for rule in RULES:
        matched_for_rule = 0
        for match in rule.pattern.finditer(text):
            if is_negated(text, match.start()):
                continue

            matched_for_rule += 1
            if matched_for_rule <= max_findings_per_rule:
                findings.append(
                    {
                        "rule_id": rule.rule_id,
                        "category": rule.category,
                        "severity": rule.severity,
                        "weight": rule.weight,
                        "description": rule.description,
                        "match": normalize_space(match.group(0))[:120],
                        "snippet": snippet_around(text, match.start(), match.end()),
                    }
                )

        if matched_for_rule > 0:
            matched_rule_ids.add(rule.rule_id)
            score += rule.weight
            max_severity_rank = max(max_severity_rank, SEVERITY_RANK.get(rule.severity, 0))

    findings.sort(
        key=lambda row: (
            -SEVERITY_RANK.get(str(row.get("severity", "")), 0),
            -int(row.get("weight", 0)),
            str(row.get("rule_id", "")),
        )
    )
    return score, classify_level(score, max_severity_rank), findings, matched_rule_ids


def write_markdown(
    path: Path,
    generated_at: str,
    summary: Dict[str, Any],
    rule_hits: Counter[str],
    audits: List[Dict[str, Any]],
    fetch_errors: List[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# SoSkill Security Audit")
    lines.append("")
    lines.append(f"- Generated at: `{generated_at}`")
    lines.append(f"- Input skills: `{summary['input_total']}`")
    lines.append(f"- Scanned skills: `{summary['scanned_total']}`")
    lines.append(f"- Reported risky skills: `{summary['reported_total']}`")
    lines.append(
        f"- Fetch content: `{summary['fetch_content']}` (attempted `{summary['fetch_attempted']}`, success `{summary['fetch_success']}`, failed `{summary['fetch_failed']}`)"
    )
    lines.append(
        "- Risk levels: "
        + ", ".join(f"`{level}`={summary['risk_levels'].get(level, 0)}" for level in ["critical", "high", "medium", "low", "clean"])
    )
    lines.append("")

    lines.append("## Rule Hit Counts")
    lines.append("")
    lines.append("| Rule ID | Hits |")
    lines.append("|---|---:|")
    for rule_id, count in rule_hits.most_common():
        lines.append(f"| {rule_id} | {count} |")
    if not rule_hits:
        lines.append("| (none) | 0 |")
    lines.append("")

    lines.append("## Top Risky Skills")
    lines.append("")
    lines.append("| Skill | Level | Score | Repo | Sources | Link |")
    lines.append("|---|---|---:|---|---|---|")
    for row in audits[:100]:
        lines.append(
            "| "
            f"{row.get('name', '')} | "
            f"{row.get('risk_level', '')} | "
            f"{row.get('risk_score', 0)} | "
            f"{row.get('repo', '')} | "
            f"{','.join(row.get('source_ids', []))} | "
            f"[open]({row.get('html_url', '')}) |"
        )
    if not audits:
        lines.append("| (no risky skills found under current threshold) | clean | 0 | - | - | - |")
    lines.append("")

    if fetch_errors:
        lines.append("## Fetch Errors (Sample)")
        lines.append("")
        for message in fetch_errors[:30]:
            lines.append(f"- {message}")
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.max_skills < 0:
        raise SystemExit("--max-skills must be >= 0")
    if args.min_risk_score < 0:
        raise SystemExit("--min-risk-score must be >= 0")
    if args.max_findings_per_rule < 1:
        raise SystemExit("--max-findings-per-rule must be >= 1")

    payload = load_skills(Path(args.input))
    skills = list(payload.get("skills", []))
    input_total = len(skills)
    if args.max_skills > 0:
        skills = skills[: args.max_skills]

    token = args.github_token or os.getenv("GITHUB_TOKEN", "") or os.getenv("GH_TOKEN", "")
    client = HttpClient(
        token=token,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
    )

    audits: List[Dict[str, Any]] = []
    rule_hits: Counter[str] = Counter()
    level_counter: Counter[str] = Counter()

    fetch_attempted = 0
    fetch_success = 0
    fetch_failed = 0
    fetch_errors: List[str] = []

    for item in skills:
        uid = str(item.get("uid", ""))
        name = str(item.get("name", ""))
        repo = str(item.get("repo", ""))
        path = str(item.get("path", ""))
        html_url = str(item.get("html_url", ""))
        raw_url = str(item.get("raw_url", ""))
        source_ids = [str(value) for value in item.get("source_ids", [])]
        description = str(item.get("description", ""))

        mode = "metadata"
        fetch_error = ""
        # Path often contains usernames/slugs that can look like commands (e.g., "...-sudo"),
        # so keep audit corpus focused on human-authored text by default.
        text_parts = [name, description]

        if args.fetch_content and raw_url:
            fetch_attempted += 1
            try:
                text_parts.append(client.get_text(raw_url))
                mode = "metadata+content"
                fetch_success += 1
            except Exception as exc:
                fetch_failed += 1
                fetch_error = str(exc).replace("\n", " ")[:220]
                fetch_errors.append(f"{uid}: {fetch_error}")

        score, level, findings, matched_ids = scan_text("\n".join(text_parts), args.max_findings_per_rule)
        level_counter[level] += 1
        for rule_id in matched_ids:
            rule_hits[rule_id] += 1

        should_include = args.include_clean or score >= args.min_risk_score
        if should_include:
            audits.append(
                {
                    "uid": uid,
                    "name": name,
                    "repo": repo,
                    "path": path,
                    "source_ids": source_ids,
                    "risk_level": level,
                    "risk_score": score,
                    "findings_count": len(findings),
                    "content_mode": mode,
                    "html_url": html_url,
                    "raw_url": raw_url,
                    "findings": findings,
                    "fetch_error": fetch_error,
                }
            )

    level_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "clean": 4}
    audits.sort(
        key=lambda row: (
            level_order.get(str(row.get("risk_level", "clean")), 9),
            -int(row.get("risk_score", 0)),
            str(row.get("name", "")).lower(),
            str(row.get("uid", "")).lower(),
        )
    )

    generated_at = utc_now()
    summary = {
        "input_total": input_total,
        "scanned_total": len(skills),
        "reported_total": len(audits),
        "fetch_content": bool(args.fetch_content),
        "fetch_attempted": fetch_attempted,
        "fetch_success": fetch_success,
        "fetch_failed": fetch_failed,
        "min_risk_score": args.min_risk_score,
        "risk_levels": {level: int(level_counter.get(level, 0)) for level in ["critical", "high", "medium", "low", "clean"]},
    }

    output_payload = {
        "generated_at": generated_at,
        "input": args.input,
        "rules_version": "2026-03-05",
        "summary": summary,
        "rule_hits": dict(rule_hits.most_common()),
        "audits": audits,
    }
    write_json(Path(args.output), output_payload)
    write_markdown(Path(args.markdown), generated_at, summary, rule_hits, audits, fetch_errors)

    print(
        "[done] skill audit complete: "
        f"scanned={summary['scanned_total']} reported={summary['reported_total']} "
        f"critical={summary['risk_levels']['critical']} high={summary['risk_levels']['high']}"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
