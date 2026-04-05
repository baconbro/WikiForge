"""Tests for the ingest_text pipeline and CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from wikiforge.cli import cli
from wikiforge.ingest import _slugify, ingest_text
from wikiforge.manifest import load_manifest
from wikiforge.models import SourceStatus
from wikiforge.vault import Vault


def test_slugify_basic() -> None:
    assert _slugify("Hello World") == "hello-world"


def test_slugify_special_characters() -> None:
    assert _slugify("My Doc: A Test!") == "my-doc-a-test"


def test_slugify_extra_whitespace() -> None:
    assert _slugify("  lots   of   spaces  ") == "lots-of-spaces"


def test_slugify_empty_string() -> None:
    assert _slugify("") == "untitled"


def test_slugify_only_special_chars() -> None:
    assert _slugify("!!!") == "untitled"


def test_ingest_text_creates_file(tmp_vault: Vault) -> None:
    content = "# My Knowledge\n\nSome important facts."
    file_path, result = ingest_text(tmp_vault, "My Knowledge", content)

    assert file_path.exists()
    assert file_path.name == "my-knowledge.md"
    assert file_path.read_text(encoding="utf-8") == content
    assert result.new == 1


def test_ingest_text_handles_collision(tmp_vault: Vault) -> None:
    content1 = "First version"
    content2 = "Second version"

    path1, _ = ingest_text(tmp_vault, "Same Title", content1)
    path2, _ = ingest_text(tmp_vault, "Same Title", content2)

    assert path1.name == "same-title.md"
    assert path2.name == "same-title-1.md"
    assert path1.read_text(encoding="utf-8") == content1
    assert path2.read_text(encoding="utf-8") == content2


def test_ingest_text_subdirectory(tmp_vault: Vault) -> None:
    content = "# Conversation notes"
    file_path, result = ingest_text(
        tmp_vault, "My Chat", content, subdirectory="conversations"
    )

    assert file_path.parent.name == "conversations"
    assert file_path.exists()
    assert result.new == 1


def test_ingest_text_dry_run(tmp_vault: Vault) -> None:
    _, result = ingest_text(tmp_vault, "Dry Run Doc", "content", dry_run=True)

    # File should not exist (dry_run skips writing)
    assert not (tmp_vault.raw_dir / "dry-run-doc.md").exists()
    # Manifest should not be updated
    manifest = load_manifest(tmp_vault.manifest_path)
    assert len(manifest.sources) == 0


def test_ingest_text_registers_in_manifest(tmp_vault: Vault) -> None:
    ingest_text(tmp_vault, "Registered Doc", "Some content here")

    manifest = load_manifest(tmp_vault.manifest_path)
    assert "registered-doc.md" in manifest.sources
    assert manifest.sources["registered-doc.md"].status == SourceStatus.pending


def test_ingest_text_subdirectory_manifest_path(tmp_vault: Vault) -> None:
    ingest_text(tmp_vault, "Sub Doc", "content", subdirectory="notes")

    manifest = load_manifest(tmp_vault.manifest_path)
    assert "notes/sub-doc.md" in manifest.sources


def test_ingest_text_cli_with_content(tmp_vault: Vault, monkeypatch) -> None:
    monkeypatch.chdir(tmp_vault.root)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "ingest-text", "-t", "CLI Test", "-c", "Hello from CLI", "--no-compile",
    ])

    assert result.exit_code == 0
    assert "cli-test.md" in (tmp_vault.raw_dir / "cli-test.md").name
    assert (tmp_vault.raw_dir / "cli-test.md").exists()


def test_ingest_text_cli_with_stdin(tmp_vault: Vault, monkeypatch) -> None:
    monkeypatch.chdir(tmp_vault.root)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["ingest-text", "-t", "Stdin Test", "--no-compile"],
        input="Content from stdin\n",
    )

    assert result.exit_code == 0
    assert (tmp_vault.raw_dir / "stdin-test.md").exists()
    assert (tmp_vault.raw_dir / "stdin-test.md").read_text(encoding="utf-8") == "Content from stdin\n"


def test_ingest_text_cli_empty_content(tmp_vault: Vault, monkeypatch) -> None:
    monkeypatch.chdir(tmp_vault.root)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "ingest-text", "-t", "Empty", "-c", "   ", "--no-compile",
    ])

    assert result.exit_code != 0
    assert "empty" in result.output.lower() or "Content is empty" in result.output
