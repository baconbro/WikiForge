"""Tests for vault initialization and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from wikiforge.vault import Vault, init_vault, resolve_vault


def test_init_creates_structure(tmp_path: Path) -> None:
    vault = init_vault(tmp_path / "my-vault")

    assert vault.wikiforge_dir.is_dir()
    assert vault.raw_dir.is_dir()
    assert vault.wiki_dir.is_dir()
    assert vault.outputs_dir.is_dir()
    assert vault.config_path.is_file()
    assert vault.manifest_path.is_file()
    assert vault.index_path.is_file()

    # Category dirs
    assert (vault.wiki_dir / "concepts").is_dir()
    assert (vault.wiki_dir / "entities").is_dir()


def test_init_rejects_existing_vault(tmp_vault: Vault) -> None:
    with pytest.raises(FileExistsError):
        init_vault(tmp_vault.root)


def test_resolve_finds_vault(tmp_vault: Vault) -> None:
    # Should find vault from a subdirectory
    sub = tmp_vault.raw_dir / "sub"
    sub.mkdir()
    found = resolve_vault(sub)
    assert found.root == tmp_vault.root


def test_resolve_raises_when_no_vault(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_vault(tmp_path)


def test_vault_is_valid(tmp_vault: Vault) -> None:
    assert tmp_vault.is_valid()


def test_vault_load_config(tmp_vault: Vault) -> None:
    config = tmp_vault.load_config()
    assert config.llm.model == "claude-sonnet-4-20250514"
