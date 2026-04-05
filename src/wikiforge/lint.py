"""Lint pipeline — health-check the wiki for issues."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from wikiforge.config import WikiForgeConfig
from wikiforge.index import load_index, render_index_for_llm
from wikiforge.llm import call_llm_json
from wikiforge.manifest import load_manifest
from wikiforge.models import SourceStatus, WikiIndex
from wikiforge.schema import load_schema
from wikiforge.vault import Vault


@dataclass
class LintIssue:
    check: str
    severity: str  # "error", "warning", "info"
    article: str
    message: str
    auto_fixable: bool = False


@dataclass
class LintResult:
    issues: list[LintIssue] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)


# Structural checks (no LLM needed)


def check_broken_links(vault: Vault, index: WikiIndex) -> list[LintIssue]:
    """Find [[wikilinks]] that don't match any article title."""
    issues = []
    known_titles = {entry.title.lower() for entry in index.entries}

    for entry in index.entries:
        article_path = vault.wiki_dir / entry.path
        if not article_path.exists():
            issues.append(LintIssue(
                check="broken_links",
                severity="error",
                article=entry.path,
                message=f"Article file missing: {entry.path}",
                auto_fixable=False,
            ))
            continue

        content = article_path.read_text(encoding="utf-8")
        wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content)

        for link in wikilinks:
            if link.lower() not in known_titles:
                issues.append(LintIssue(
                    check="broken_links",
                    severity="warning",
                    article=entry.path,
                    message=f"Dangling wikilink: [[{link}]] — no matching article",
                    auto_fixable=False,
                ))

    return issues


def check_orphan_pages(vault: Vault, index: WikiIndex) -> list[LintIssue]:
    """Find articles with no inbound links from other articles."""
    issues = []
    if len(index.entries) < 2:
        return issues

    # Count inbound links for each article title
    inbound: dict[str, int] = {entry.title.lower(): 0 for entry in index.entries}

    for entry in index.entries:
        article_path = vault.wiki_dir / entry.path
        if not article_path.exists():
            continue
        content = article_path.read_text(encoding="utf-8")
        wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content)
        for link in wikilinks:
            key = link.lower()
            if key in inbound:
                inbound[key] += 1

    for entry in index.entries:
        if inbound.get(entry.title.lower(), 0) == 0:
            issues.append(LintIssue(
                check="orphan_pages",
                severity="info",
                article=entry.path,
                message=f"Orphan page: '{entry.title}' has no inbound links",
            ))

    return issues


def check_stale_sources(vault: Vault) -> list[LintIssue]:
    """Find sources that have been modified since last compile."""
    issues = []
    manifest = load_manifest(vault.manifest_path)

    for path, entry in manifest.sources.items():
        if entry.status == SourceStatus.pending:
            issues.append(LintIssue(
                check="stale_sources",
                severity="warning",
                article=f"raw/{path}",
                message=f"Source '{path}' has changes not yet compiled",
            ))

    return issues


def check_missing_sources(vault: Vault, index: WikiIndex) -> list[LintIssue]:
    """Find articles referencing sources not in the manifest."""
    issues = []
    manifest = load_manifest(vault.manifest_path)
    known_sources = set(manifest.sources.keys())

    for entry in index.entries:
        article_path = vault.wiki_dir / entry.path
        if not article_path.exists():
            continue
        content = article_path.read_text(encoding="utf-8")

        # Look for source references in frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                frontmatter = content[3:end]
                # Simple extraction of sources list
                for line in frontmatter.split("\n"):
                    line = line.strip().lstrip("- ").strip('"').strip("'")
                    if line.endswith((".md", ".txt")) and line not in known_sources:
                        # Only flag if it looks like a source path (not a section header)
                        if "/" not in line or line.count("/") <= 2:
                            issues.append(LintIssue(
                                check="missing_sources",
                                severity="info",
                                article=entry.path,
                                message=f"References source '{line}' not found in manifest",
                            ))

    return issues


# LLM-powered checks


def _parse_llm_issues(raw_json, check_name: str) -> list[LintIssue]:
    """Parse LLM JSON response into LintIssues."""
    from pydantic import BaseModel, Field

    class IssueLine(BaseModel):
        article: str = ""
        message: str = ""
        severity: str = "info"

    class IssueList(BaseModel):
        issues: list[IssueLine] = Field(default_factory=list)

    try:
        parsed = call_llm_json.__wrapped__ if hasattr(call_llm_json, '__wrapped__') else None
        # Direct parse from the model
        result = IssueList.model_validate(raw_json) if isinstance(raw_json, dict) else IssueList.model_validate_json(raw_json)
        return [
            LintIssue(
                check=check_name,
                severity=issue.severity,
                article=issue.article,
                message=issue.message,
            )
            for issue in result.issues
        ]
    except Exception:
        return []


def check_consistency(vault: Vault, config: WikiForgeConfig, index: WikiIndex) -> list[LintIssue]:
    """Use LLM to find contradictions between articles."""
    from wikiforge.prompts.lint import build_consistency_messages
    from wikiforge.llm import call_llm

    if len(index.entries) < 2:
        return []

    # Load all article contents (limit to avoid token overflow)
    article_contents: dict[str, str] = {}
    for entry in index.entries[:20]:
        path = vault.wiki_dir / entry.path
        if path.exists():
            article_contents[entry.path] = path.read_text(encoding="utf-8")

    if not article_contents:
        return []

    messages = build_consistency_messages(article_contents)
    raw = call_llm(messages, model=config.llm.model, temperature=0.1)

    return _parse_llm_issues(raw, "consistency")


def check_gaps(vault: Vault, config: WikiForgeConfig, index: WikiIndex) -> list[LintIssue]:
    """Use LLM to identify knowledge gaps."""
    from wikiforge.prompts.lint import build_gaps_messages
    from wikiforge.llm import call_llm

    index_summary = render_index_for_llm(index)
    schema_context = load_schema(vault.schema_path)

    messages = build_gaps_messages(index_summary, schema_context)
    raw = call_llm(messages, model=config.llm.model, temperature=0.3)

    return _parse_llm_issues(raw, "gaps")


# Orchestrator


STRUCTURAL_CHECKS = {
    "broken_links": check_broken_links,
    "orphan_pages": check_orphan_pages,
    "stale_sources": check_stale_sources,
    "missing_sources": check_missing_sources,
}

LLM_CHECKS = {
    "consistency": check_consistency,
    "gaps": check_gaps,
}

ALL_CHECKS = list(STRUCTURAL_CHECKS.keys()) + list(LLM_CHECKS.keys())


def run_lint(
    vault: Vault,
    config: WikiForgeConfig,
    checks: list[str] | None = None,
    fix: bool = False,
) -> LintResult:
    """Run lint checks on the wiki."""
    result = LintResult()
    index = load_index(vault.index_path)

    checks_to_run = checks or list(STRUCTURAL_CHECKS.keys())

    for check_name in checks_to_run:
        if check_name in STRUCTURAL_CHECKS:
            fn = STRUCTURAL_CHECKS[check_name]
            if check_name in ("broken_links", "orphan_pages", "missing_sources"):
                issues = fn(vault, index)
            else:
                issues = fn(vault)
            result.issues.extend(issues)
            result.checks_run.append(check_name)
        elif check_name in LLM_CHECKS:
            fn = LLM_CHECKS[check_name]
            issues = fn(vault, config, index)
            result.issues.extend(issues)
            result.checks_run.append(check_name)

    # Write report
    _write_report(vault, result)

    # Log the lint
    from wikiforge.log import append_log

    details = [f"Checks: {', '.join(result.checks_run)}"]
    by_severity = {}
    for issue in result.issues:
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
    for sev, count in sorted(by_severity.items()):
        details.append(f"{count} {sev}(s)")
    append_log(vault, "lint", f"{len(result.issues)} issues found", details)

    return result


def _write_report(vault: Vault, result: LintResult) -> None:
    """Write lint report to outputs/."""
    vault.outputs_dir.mkdir(parents=True, exist_ok=True)
    path = vault.outputs_dir / "_lint_report.md"

    lines = ["# Lint Report\n\n"]
    lines.append(f"**{len(result.issues)} issues** found across {len(result.checks_run)} checks.\n\n")
    lines.append(f"Checks run: {', '.join(result.checks_run)}\n\n")

    if not result.issues:
        lines.append("No issues found.\n")
    else:
        by_check: dict[str, list[LintIssue]] = {}
        for issue in result.issues:
            by_check.setdefault(issue.check, []).append(issue)

        for check, issues in by_check.items():
            lines.append(f"## {check}\n\n")
            for issue in issues:
                icon = {"error": "x", "warning": "!", "info": "i"}.get(issue.severity, "?")
                lines.append(f"- [{icon}] **{issue.article}**: {issue.message}\n")
            lines.append("\n")

    path.write_text("".join(lines), encoding="utf-8")
