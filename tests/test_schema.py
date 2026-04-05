"""Tests for the schema document feature."""

from __future__ import annotations

from wikiforge.prompts.compile import build_plan_messages, build_write_messages
from wikiforge.prompts.query import build_query_messages
from wikiforge.schema import DEFAULT_SCHEMA, load_schema, save_default_schema
from wikiforge.vault import Vault


def test_init_creates_schema(tmp_vault: Vault) -> None:
    assert tmp_vault.schema_path.exists()
    content = tmp_vault.schema_path.read_text()
    assert "Wiki Schema" in content


def test_load_schema(tmp_vault: Vault) -> None:
    content = load_schema(tmp_vault.schema_path)
    assert "Wiki Schema" in content


def test_load_schema_missing_file(tmp_path) -> None:
    result = load_schema(tmp_path / "nonexistent.md")
    assert result == ""


def test_load_schema_empty_file(tmp_path) -> None:
    path = tmp_path / "schema.md"
    path.write_text("   \n  ")
    result = load_schema(path)
    assert result == ""


def test_schema_injected_in_plan_messages() -> None:
    msgs = build_plan_messages(
        index_content="empty wiki",
        source_texts={"test.md": "content"},
        schema_context="Use formal academic tone.",
    )
    user_msg = msgs[1]["content"]
    assert "## Wiki Schema" in user_msg
    assert "Use formal academic tone." in user_msg


def test_schema_not_injected_when_empty() -> None:
    msgs = build_plan_messages(
        index_content="empty wiki",
        source_texts={"test.md": "content"},
        schema_context="",
    )
    user_msg = msgs[1]["content"]
    assert "## Wiki Schema" not in user_msg


def test_schema_injected_in_write_messages() -> None:
    msgs = build_write_messages(
        title="Test",
        summary="A test",
        source_contents={"test.md": "content"},
        related=[],
        category="concepts",
        schema_context="Always include a glossary section.",
    )
    user_msg = msgs[1]["content"]
    assert "## Wiki Schema" in user_msg
    assert "Always include a glossary section." in user_msg


def test_schema_injected_in_query_messages() -> None:
    msgs = build_query_messages(
        question="What is X?",
        article_contents={"Test": "content"},
        index_summary="1 article",
        schema_context="Respond with bullet points.",
    )
    user_msg = msgs[1]["content"]
    assert "## Wiki Schema" in user_msg
    assert "Respond with bullet points." in user_msg
