"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from wikiforge.config import WikiForgeConfig
from wikiforge.vault import Vault, init_vault


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Vault:
    """Create a temporary WikiForge vault for testing."""
    vault_dir = tmp_path / "test-vault"
    vault_dir.mkdir()
    return init_vault(vault_dir)


@pytest.fixture
def config() -> WikiForgeConfig:
    return WikiForgeConfig()
