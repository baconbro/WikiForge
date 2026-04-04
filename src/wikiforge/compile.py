"""Compile pipeline — orchestrate LLM planning and article writing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from wikiforge.config import WikiForgeConfig
from wikiforge.index import load_index, render_index_for_llm, save_index
from wikiforge.llm import call_llm, call_llm_json, count_tokens
from wikiforge.manifest import get_pending_sources, load_manifest, save_manifest
from wikiforge.models import (
    ArticlePlan,
    CompilePlan,
    IndexEntry,
    ManifestEntry,
    SourceStatus,
)
from wikiforge.prompts.compile import build_plan_messages, build_write_messages
from wikiforge.vault import Vault


@dataclass
class CompileResult:
    articles_created: int = 0
    articles_updated: int = 0
    sources_processed: int = 0
    plan: CompilePlan | None = None
    errors: list[str] = field(default_factory=list)


def _read_source(vault: Vault, rel_path: str, chunk_size: int) -> str:
    """Read source content, truncating if too large."""
    full_path = vault.raw_dir / rel_path
    if not full_path.exists():
        return ""
    content = full_path.read_text(encoding="utf-8")
    if len(content) > chunk_size:
        content = content[:chunk_size] + "\n\n[... truncated ...]"
    return content


def _read_existing_article(vault: Vault, category: str, filename: str) -> str | None:
    """Read an existing wiki article if it exists."""
    path = vault.wiki_dir / category / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _write_article(vault: Vault, category: str, filename: str, content: str) -> Path:
    """Write an article to the wiki directory."""
    category_dir = vault.wiki_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)
    path = category_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def run_compile(
    vault: Vault,
    config: WikiForgeConfig,
    plan_only: bool = False,
) -> CompileResult:
    """Run the compile pipeline: plan → write → update index and manifest."""
    result = CompileResult()
    manifest = load_manifest(vault.manifest_path)
    index = load_index(vault.index_path)

    pending = get_pending_sources(manifest)
    if not pending:
        return result

    # Read source contents
    source_texts: dict[str, str] = {}
    for entry in pending:
        content = _read_source(vault, entry.source_path, config.chunk_size)
        if content:
            source_texts[entry.source_path] = content

    if not source_texts:
        return result

    # Phase 1: Plan
    index_summary = render_index_for_llm(index)
    plan_messages = build_plan_messages(index_summary, source_texts)
    plan = call_llm_json(
        plan_messages,
        CompilePlan,
        model=config.llm.model,
    )
    result.plan = plan

    if plan_only:
        return result

    # Phase 2: Write articles
    for article_plan in plan.articles[: config.compile.max_articles_per_run]:
        try:
            _compile_article(vault, config, article_plan, source_texts, index, result)
        except Exception as e:
            result.errors.append(f"Error writing {article_plan.filename}: {e}")

    # Update index
    save_index(vault.index_path, index)

    # Update manifest
    now = datetime.now(timezone.utc)
    for entry in pending:
        entry.status = SourceStatus.compiled
        entry.last_compiled = now
        # Track which articles came from this source
        for ap in plan.articles:
            if entry.source_path in ap.source_refs:
                article_path = f"{ap.category}/{ap.filename}"
                if article_path not in entry.articles:
                    entry.articles.append(article_path)

    result.sources_processed = len(pending)
    save_manifest(vault.manifest_path, manifest)

    return result


def _compile_article(
    vault: Vault,
    config: WikiForgeConfig,
    plan: ArticlePlan,
    source_texts: dict[str, str],
    index,
    result: CompileResult,
) -> None:
    """Compile a single article from plan."""
    # Gather relevant source content
    relevant_sources = {
        path: text
        for path, text in source_texts.items()
        if path in plan.source_refs
    }
    # Fall back to all sources if none matched
    if not relevant_sources:
        relevant_sources = source_texts

    existing = _read_existing_article(vault, plan.category, plan.filename)

    messages = build_write_messages(
        title=plan.title,
        summary=plan.summary,
        source_contents=relevant_sources,
        related=plan.related,
        category=plan.category,
        existing_content=existing,
        target_length=config.compile.article_target_length,
    )

    article_content = call_llm(messages, model=config.llm.model)
    _write_article(vault, plan.category, plan.filename, article_content)

    # Update index
    article_path = f"{plan.category}/{plan.filename}"
    index.upsert(IndexEntry(
        path=article_path,
        title=plan.title,
        summary=plan.summary,
        category=plan.category,
    ))

    if plan.action == "create":
        result.articles_created += 1
    else:
        result.articles_updated += 1
