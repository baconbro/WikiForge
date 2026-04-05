"""Ingest pipeline — scan raw/ for new or changed sources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from wikiforge.manifest import load_manifest, save_manifest
from wikiforge.models import Manifest, ManifestEntry, SourceStatus
from wikiforge.vault import Vault

SUPPORTED_EXTENSIONS = {".md", ".txt"}


@dataclass
class IngestResult:
    new: int = 0
    updated: int = 0
    unchanged: int = 0


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _discover_sources(raw_dir: Path) -> list[Path]:
    sources = []
    for ext in SUPPORTED_EXTENSIONS:
        sources.extend(raw_dir.rglob(f"*{ext}"))
    return sorted(sources)


def ingest_sources(
    vault: Vault,
    files: list[Path] | None = None,
    dry_run: bool = False,
) -> IngestResult:
    """Scan raw/ for new or changed sources and register them in the manifest."""
    manifest = load_manifest(vault.manifest_path)
    result = IngestResult()

    if files:
        source_paths = [p.resolve() for p in files]
    else:
        source_paths = _discover_sources(vault.raw_dir)

    for abs_path in source_paths:
        if abs_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            rel_path = str(abs_path.relative_to(vault.raw_dir))
        except ValueError:
            continue

        file_hash = _sha256(abs_path)
        now = datetime.now(timezone.utc)

        existing = manifest.sources.get(rel_path)
        if existing is None:
            manifest.sources[rel_path] = ManifestEntry(
                source_path=rel_path,
                sha256=file_hash,
                last_ingested=now,
                status=SourceStatus.pending,
            )
            result.new += 1
        elif existing.sha256 != file_hash:
            existing.sha256 = file_hash
            existing.last_ingested = now
            existing.status = SourceStatus.pending
            result.updated += 1
        else:
            result.unchanged += 1

    if not dry_run:
        save_manifest(vault.manifest_path, manifest)

        # Log the ingest operation
        if result.new > 0 or result.updated > 0:
            from wikiforge.log import append_log

            details = []
            if result.new:
                details.append(f"{result.new} new source(s)")
            if result.updated:
                details.append(f"{result.updated} updated source(s)")
            if result.unchanged:
                details.append(f"{result.unchanged} unchanged")
            append_log(vault, "ingest", f"{result.new} new, {result.updated} updated", details)

    return result
