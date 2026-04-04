"""Tests for the ingest pipeline."""

from __future__ import annotations

from wikiforge.ingest import ingest_sources
from wikiforge.manifest import load_manifest
from wikiforge.models import SourceStatus
from wikiforge.vault import Vault


def test_ingest_discovers_new_files(tmp_vault: Vault) -> None:
    # Create source files
    (tmp_vault.raw_dir / "test.md").write_text("# Hello\nWorld")
    (tmp_vault.raw_dir / "notes.txt").write_text("Some notes")

    result = ingest_sources(tmp_vault)
    assert result.new == 2
    assert result.updated == 0
    assert result.unchanged == 0

    # Check manifest
    manifest = load_manifest(tmp_vault.manifest_path)
    assert "test.md" in manifest.sources
    assert "notes.txt" in manifest.sources
    assert manifest.sources["test.md"].status == SourceStatus.pending


def test_ingest_detects_unchanged(tmp_vault: Vault) -> None:
    (tmp_vault.raw_dir / "test.md").write_text("# Hello")
    ingest_sources(tmp_vault)

    # Ingest again without changes
    result = ingest_sources(tmp_vault)
    assert result.new == 0
    assert result.unchanged == 1


def test_ingest_detects_changes(tmp_vault: Vault) -> None:
    (tmp_vault.raw_dir / "test.md").write_text("# Version 1")
    ingest_sources(tmp_vault)

    # Modify the file
    (tmp_vault.raw_dir / "test.md").write_text("# Version 2")
    result = ingest_sources(tmp_vault)
    assert result.updated == 1


def test_ingest_dry_run(tmp_vault: Vault) -> None:
    (tmp_vault.raw_dir / "test.md").write_text("# Hello")

    result = ingest_sources(tmp_vault, dry_run=True)
    assert result.new == 1

    # Manifest should NOT be updated
    manifest = load_manifest(tmp_vault.manifest_path)
    assert len(manifest.sources) == 0


def test_ingest_ignores_unsupported_extensions(tmp_vault: Vault) -> None:
    (tmp_vault.raw_dir / "image.png").write_bytes(b"\x89PNG")
    (tmp_vault.raw_dir / "data.csv").write_text("a,b,c")
    (tmp_vault.raw_dir / "doc.md").write_text("# Real doc")

    result = ingest_sources(tmp_vault)
    assert result.new == 1  # only the .md file


def test_ingest_handles_subdirectories(tmp_vault: Vault) -> None:
    sub = tmp_vault.raw_dir / "articles"
    sub.mkdir()
    (sub / "deep.md").write_text("# Deep article")

    result = ingest_sources(tmp_vault)
    assert result.new == 1

    manifest = load_manifest(tmp_vault.manifest_path)
    assert "articles/deep.md" in manifest.sources
