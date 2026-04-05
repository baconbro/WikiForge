"""Tests for manifest operations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from wikiforge.manifest import get_pending_sources, load_manifest, save_manifest
from wikiforge.models import Manifest, ManifestEntry, SourceStatus


def test_load_empty_manifest(tmp_path: Path) -> None:
    manifest = load_manifest(tmp_path / "nonexistent.yaml")
    assert manifest.version == 1
    assert len(manifest.sources) == 0


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "_manifest.yaml"
    manifest = Manifest(
        sources={
            "test.md": ManifestEntry(
                source_path="test.md",
                sha256="abc123",
                last_ingested=datetime(2025, 1, 1, tzinfo=timezone.utc),
                status=SourceStatus.pending,
            )
        }
    )

    save_manifest(path, manifest)
    loaded = load_manifest(path)

    assert len(loaded.sources) == 1
    assert loaded.sources["test.md"].sha256 == "abc123"
    assert loaded.sources["test.md"].status == SourceStatus.pending


def test_get_pending_sources() -> None:
    now = datetime.now(timezone.utc)
    manifest = Manifest(
        sources={
            "a.md": ManifestEntry(
                source_path="a.md",
                sha256="aaa",
                last_ingested=now,
                status=SourceStatus.pending,
            ),
            "b.md": ManifestEntry(
                source_path="b.md",
                sha256="bbb",
                last_ingested=now,
                status=SourceStatus.compiled,
            ),
            "c.md": ManifestEntry(
                source_path="c.md",
                sha256="ccc",
                last_ingested=now,
                status=SourceStatus.pending,
            ),
        }
    )

    pending = get_pending_sources(manifest)
    assert len(pending) == 2
    paths = {e.source_path for e in pending}
    assert paths == {"a.md", "c.md"}
