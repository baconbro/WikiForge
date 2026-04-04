"""Tests for the query pipeline."""

from __future__ import annotations

from unittest.mock import patch

from wikiforge.index import save_index
from wikiforge.models import IndexEntry, WikiIndex
from wikiforge.query import QueryResult, run_query, _find_relevant_articles, _tokenize
from wikiforge.vault import Vault


def test_tokenize_removes_stop_words() -> None:
    tokens = _tokenize("What is the transformer architecture?")
    assert "what" not in tokens
    assert "the" not in tokens
    assert "transformer" in tokens
    assert "architecture" in tokens


def test_find_relevant_articles() -> None:
    index = WikiIndex(entries=[
        IndexEntry(path="concepts/transformers.md", title="Transformer Architecture", summary="Neural network architecture using attention"),
        IndexEntry(path="concepts/rlhf.md", title="RLHF", summary="Reinforcement learning from human feedback"),
        IndexEntry(path="entities/openai.md", title="OpenAI", summary="AI research company", category="entities"),
    ])

    relevant = _find_relevant_articles(index, "How does the transformer architecture work?")
    assert len(relevant) >= 1
    assert relevant[0].title == "Transformer Architecture"


def test_query_empty_wiki(tmp_vault: Vault) -> None:
    config = tmp_vault.load_config()
    result = run_query(tmp_vault, config, "test question")
    assert "empty" in result.answer.lower()


def test_query_with_articles(tmp_vault: Vault) -> None:
    # Set up a wiki article
    concepts_dir = tmp_vault.wiki_dir / "concepts"
    concepts_dir.mkdir(exist_ok=True)
    (concepts_dir / "transformers.md").write_text(
        "# Transformers\n\nTransformers use self-attention mechanisms."
    )

    # Set up index
    index = WikiIndex(entries=[
        IndexEntry(
            path="concepts/transformers.md",
            title="Transformers",
            summary="Neural network architecture using self-attention",
        )
    ])
    save_index(tmp_vault.index_path, index)

    config = tmp_vault.load_config()

    with patch("wikiforge.query.call_llm", return_value="Transformers use self-attention."):
        result = run_query(tmp_vault, config, "What are transformers?")

    assert result.answer == "Transformers use self-attention."
    assert "Transformers" in result.articles_used


def test_query_saves_output(tmp_vault: Vault) -> None:
    concepts_dir = tmp_vault.wiki_dir / "concepts"
    concepts_dir.mkdir(exist_ok=True)
    (concepts_dir / "test.md").write_text("# Test\n\nContent here.")

    index = WikiIndex(entries=[
        IndexEntry(path="concepts/test.md", title="Test", summary="A test article")
    ])
    save_index(tmp_vault.index_path, index)

    config = tmp_vault.load_config()
    output_path = tmp_vault.outputs_dir / "answer.md"

    with patch("wikiforge.query.call_llm", return_value="The answer is 42."):
        run_query(tmp_vault, config, "What is the answer?", output_path=output_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "42" in content
