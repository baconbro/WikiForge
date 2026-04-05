"""Tests for the lint pipeline."""

from __future__ import annotations

from wikiforge.index import save_index
from wikiforge.lint import (
    check_broken_links,
    check_orphan_pages,
    check_stale_sources,
    run_lint,
)
from wikiforge.models import IndexEntry, WikiIndex
from wikiforge.vault import Vault


def _setup_wiki(tmp_vault: Vault) -> WikiIndex:
    """Create a small wiki for testing."""
    concepts = tmp_vault.wiki_dir / "concepts"
    concepts.mkdir(exist_ok=True)

    (concepts / "alpha.md").write_text(
        "---\ntitle: Alpha\n---\n# Alpha\n\nSee also [[Beta]] and [[Missing]].\n"
    )
    (concepts / "beta.md").write_text(
        "---\ntitle: Beta\n---\n# Beta\n\nRelated to [[Alpha]].\n"
    )

    index = WikiIndex(entries=[
        IndexEntry(path="concepts/alpha.md", title="Alpha", summary="First article"),
        IndexEntry(path="concepts/beta.md", title="Beta", summary="Second article"),
    ])
    save_index(tmp_vault.index_path, index)
    return index


def test_check_broken_links(tmp_vault: Vault) -> None:
    index = _setup_wiki(tmp_vault)
    issues = check_broken_links(tmp_vault, index)

    # [[Missing]] should be flagged
    dangling = [i for i in issues if "Missing" in i.message]
    assert len(dangling) == 1
    assert dangling[0].check == "broken_links"
    assert dangling[0].severity == "warning"


def test_check_no_broken_links(tmp_vault: Vault) -> None:
    concepts = tmp_vault.wiki_dir / "concepts"
    concepts.mkdir(exist_ok=True)
    (concepts / "solo.md").write_text("# Solo\n\nNo links here.\n")

    index = WikiIndex(entries=[
        IndexEntry(path="concepts/solo.md", title="Solo", summary="No links"),
    ])
    issues = check_broken_links(tmp_vault, index)
    assert len(issues) == 0


def test_check_orphan_pages(tmp_vault: Vault) -> None:
    index = _setup_wiki(tmp_vault)
    issues = check_orphan_pages(tmp_vault, index)

    # Beta links to Alpha, Alpha links to Beta — no orphans
    # But actually Alpha links to Beta and Missing, Beta links to Alpha
    # So both have inbound links — no orphans
    orphan_titles = [i.message for i in issues]
    assert all("Alpha" not in t for t in orphan_titles)
    assert all("Beta" not in t for t in orphan_titles)


def test_check_orphan_with_actual_orphan(tmp_vault: Vault) -> None:
    concepts = tmp_vault.wiki_dir / "concepts"
    concepts.mkdir(exist_ok=True)
    (concepts / "linked.md").write_text("# Linked\n\nContent.\n")
    (concepts / "orphan.md").write_text("# Orphan\n\nAlone here.\n")

    index = WikiIndex(entries=[
        IndexEntry(path="concepts/linked.md", title="Linked", summary="Has no links"),
        IndexEntry(path="concepts/orphan.md", title="Orphan", summary="Also no links"),
    ])
    issues = check_orphan_pages(tmp_vault, index)

    # Both are orphans since neither links to the other
    assert len(issues) == 2


def test_check_stale_sources(tmp_vault: Vault) -> None:
    from wikiforge.ingest import ingest_sources

    (tmp_vault.raw_dir / "test.md").write_text("# Content")
    ingest_sources(tmp_vault)

    issues = check_stale_sources(tmp_vault)
    assert len(issues) == 1
    assert issues[0].check == "stale_sources"
    assert "test.md" in issues[0].message


def test_run_lint_structural(tmp_vault: Vault) -> None:
    _setup_wiki(tmp_vault)
    config = tmp_vault.load_config()

    result = run_lint(tmp_vault, config)

    assert len(result.checks_run) > 0
    assert "broken_links" in result.checks_run

    # Report should be written
    report_path = tmp_vault.outputs_dir / "_lint_report.md"
    assert report_path.exists()


def test_run_lint_empty_wiki(tmp_vault: Vault) -> None:
    config = tmp_vault.load_config()
    result = run_lint(tmp_vault, config)
    assert len(result.issues) == 0
