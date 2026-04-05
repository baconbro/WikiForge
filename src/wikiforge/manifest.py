"""Manifest (_manifest.yaml) read/write operations."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import TypeAdapter

from wikiforge.models import Manifest, ManifestEntry, SourceStatus


def load_manifest(path: Path) -> Manifest:
    if not path.exists():
        return Manifest()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return Manifest.model_validate(data)


def save_manifest(path: Path, manifest: Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = manifest.model_dump(mode="json")
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_pending_sources(manifest: Manifest) -> list[ManifestEntry]:
    return [
        entry
        for entry in manifest.sources.values()
        if entry.status == SourceStatus.pending
    ]
