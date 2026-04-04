"""Tests for the compile pipeline (with mocked LLM)."""

from __future__ import annotations

import json
from unittest.mock import patch

from wikiforge.compile import run_compile
from wikiforge.index import load_index
from wikiforge.ingest import ingest_sources
from wikiforge.manifest import load_manifest
from wikiforge.models import SourceStatus
from wikiforge.vault import Vault


MOCK_PLAN_RESPONSE = json.dumps({
    "articles": [
        {
            "title": "Machine Learning Basics",
            "filename": "machine-learning-basics.md",
            "category": "concepts",
            "summary": "An overview of fundamental machine learning concepts.",
            "source_refs": ["intro-to-ml.md"],
            "related": [],
            "action": "create",
        }
    ]
})

MOCK_ARTICLE_CONTENT = """\
---
title: "Machine Learning Basics"
summary: "An overview of fundamental machine learning concepts."
sources:
  - "intro-to-ml.md"
tags:
  - machine-learning
  - fundamentals
category: "concepts"
---

# Machine Learning Basics

Machine learning is a subset of artificial intelligence.

## Key Concepts

- Supervised learning
- Unsupervised learning
- Reinforcement learning

## Related Concepts

## Sources
- Source: intro-to-ml.md
"""


def _mock_call_llm(messages, model="claude-sonnet-4-20250514", temperature=0.3, max_retries=3):
    """Return mock responses based on the system prompt content."""
    system_msg = messages[0]["content"] if messages else ""
    if "wiki architect" in system_msg:
        return MOCK_PLAN_RESPONSE
    return MOCK_ARTICLE_CONTENT


def test_compile_creates_articles(tmp_vault: Vault) -> None:
    # Add a source and ingest it
    (tmp_vault.raw_dir / "intro-to-ml.md").write_text(
        "# Intro to ML\n\nMachine learning is about learning from data."
    )
    ingest_sources(tmp_vault)

    config = tmp_vault.load_config()

    with patch("wikiforge.compile.call_llm", side_effect=_mock_call_llm):
        with patch("wikiforge.compile.call_llm_json") as mock_json:
            from wikiforge.models import CompilePlan
            mock_json.return_value = CompilePlan.model_validate_json(MOCK_PLAN_RESPONSE)

            result = run_compile(tmp_vault, config)

    assert result.articles_created == 1
    assert result.sources_processed == 1

    # Check article was written
    article_path = tmp_vault.wiki_dir / "concepts" / "machine-learning-basics.md"
    assert article_path.exists()

    # Check index was updated
    index = load_index(tmp_vault.index_path)
    assert len(index.entries) == 1
    assert index.entries[0].title == "Machine Learning Basics"

    # Check manifest was updated
    manifest = load_manifest(tmp_vault.manifest_path)
    assert manifest.sources["intro-to-ml.md"].status == SourceStatus.compiled


def test_compile_nothing_pending(tmp_vault: Vault) -> None:
    config = tmp_vault.load_config()
    result = run_compile(tmp_vault, config)
    assert result.sources_processed == 0
    assert result.articles_created == 0


def test_compile_plan_only(tmp_vault: Vault) -> None:
    (tmp_vault.raw_dir / "test.md").write_text("# Test content")
    ingest_sources(tmp_vault)

    config = tmp_vault.load_config()

    with patch("wikiforge.compile.call_llm_json") as mock_json:
        from wikiforge.models import CompilePlan
        mock_json.return_value = CompilePlan.model_validate_json(MOCK_PLAN_RESPONSE)

        result = run_compile(tmp_vault, config, plan_only=True)

    assert result.plan is not None
    assert len(result.plan.articles) == 1
    # No articles should have been written
    assert result.articles_created == 0
    assert result.sources_processed == 0
