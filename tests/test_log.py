"""Tests for the activity log."""

from __future__ import annotations

from wikiforge.log import append_log, render_recent_log
from wikiforge.vault import Vault


def test_append_log_creates_file(tmp_vault: Vault) -> None:
    assert not tmp_vault.log_path.exists()
    append_log(tmp_vault, "ingest", "1 new, 0 updated")
    assert tmp_vault.log_path.exists()


def test_append_log_content(tmp_vault: Vault) -> None:
    append_log(tmp_vault, "ingest", "2 new files", ["file1.md", "file2.md"])
    content = tmp_vault.log_path.read_text()
    assert "ingest | 2 new files" in content
    assert "- file1.md" in content
    assert "- file2.md" in content


def test_append_log_multiple(tmp_vault: Vault) -> None:
    append_log(tmp_vault, "ingest", "first")
    append_log(tmp_vault, "compile", "second")
    content = tmp_vault.log_path.read_text()
    assert "ingest | first" in content
    assert "compile | second" in content


def test_append_log_parseable(tmp_vault: Vault) -> None:
    append_log(tmp_vault, "ingest", "test")
    append_log(tmp_vault, "compile", "test2")
    content = tmp_vault.log_path.read_text()
    # Should be parseable with grep "^## \["
    headers = [line for line in content.split("\n") if line.startswith("## [")]
    assert len(headers) == 2


def test_render_recent_log_empty(tmp_vault: Vault) -> None:
    result = render_recent_log(tmp_vault)
    assert result == ""


def test_render_recent_log(tmp_vault: Vault) -> None:
    append_log(tmp_vault, "ingest", "entry1")
    append_log(tmp_vault, "compile", "entry2")
    append_log(tmp_vault, "query", "entry3")

    result = render_recent_log(tmp_vault, n=2)
    assert "entry3" in result
    assert "entry2" in result


def test_log_from_ingest(tmp_vault: Vault) -> None:
    """Verify that ingest pipeline writes to the log."""
    from wikiforge.ingest import ingest_sources

    (tmp_vault.raw_dir / "test.md").write_text("# Hello")
    ingest_sources(tmp_vault)

    assert tmp_vault.log_path.exists()
    content = tmp_vault.log_path.read_text()
    assert "ingest" in content
    assert "1 new" in content
