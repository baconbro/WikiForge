"""WikiForge CLI — the user-facing command-line interface."""

from __future__ import annotations

from pathlib import Path

import click

from wikiforge import __version__


@click.group()
@click.version_option(version=__version__, prog_name="WikiForge")
def cli() -> None:
    """WikiForge — Raw sources in, living wiki out. Your LLM is the editor."""


@cli.command()
@click.option(
    "--path",
    type=click.Path(),
    default=".",
    help="Directory to initialize the vault in (default: current directory).",
)
@click.option("--name", default=None, help="Project name for the vault.")
def init(path: str, name: str | None) -> None:
    """Initialize a new WikiForge vault."""
    from wikiforge.config import WikiForgeConfig
    from wikiforge.vault import init_vault

    config = WikiForgeConfig()
    if name:
        config.project_name = name

    try:
        vault = init_vault(Path(path), config)
        click.echo(f"Initialized WikiForge vault at {vault.root}")
        click.echo(f"  raw/     — Add your source documents here")
        click.echo(f"  wiki/    — Compiled wiki articles (LLM-generated)")
        click.echo(f"  outputs/ — Query results and visualizations")
        click.echo()
        click.echo("Next: Add source files to raw/ and run `wf ingest`")
    except FileExistsError as e:
        raise click.ClickException(str(e))


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option("--all", "ingest_all", is_flag=True, help="Ingest all files in raw/.")
@click.option("--dry-run", is_flag=True, help="Show what would be ingested without writing.")
def ingest(files: tuple[str, ...], ingest_all: bool, dry_run: bool) -> None:
    """Process new or changed sources in raw/."""
    from wikiforge.ingest import ingest_sources
    from wikiforge.vault import resolve_vault

    vault = resolve_vault()

    file_paths = [Path(f) for f in files] if files else None
    if not file_paths and not ingest_all:
        # Default to --all if no files specified
        file_paths = None

    result = ingest_sources(vault, files=file_paths, dry_run=dry_run)

    prefix = "[dry-run] " if dry_run else ""
    click.echo(f"{prefix}Ingest complete: {result.new} new, {result.updated} updated, {result.unchanged} unchanged")


@cli.command()
@click.option("--plan-only", is_flag=True, help="Show compilation plan without writing articles.")
def compile(plan_only: bool) -> None:
    """Compile staged sources into wiki articles."""
    from wikiforge.compile import run_compile
    from wikiforge.vault import resolve_vault

    vault = resolve_vault()
    config = vault.load_config()

    if not config.get_api_key():
        raise click.ClickException(
            f"API key not found. Set the {config.llm.api_key_env} environment variable."
        )

    click.echo("Compiling..." if not plan_only else "Planning...")
    result = run_compile(vault, config, plan_only=plan_only)

    if result.plan and result.plan.articles:
        click.echo(f"\nCompilation plan ({len(result.plan.articles)} articles):")
        for ap in result.plan.articles:
            action = "+" if ap.action == "create" else "~"
            click.echo(f"  {action} [{ap.category}] {ap.title}")

    if plan_only:
        return

    if result.sources_processed == 0:
        click.echo("Nothing to compile. Run `wf ingest` first.")
        return

    click.echo(
        f"\nDone: {result.articles_created} created, {result.articles_updated} updated "
        f"from {result.sources_processed} sources"
    )

    if result.errors:
        click.echo(f"\nErrors ({len(result.errors)}):")
        for err in result.errors:
            click.echo(f"  ! {err}")


@cli.command()
@click.argument("question")
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Write answer to a file in outputs/.",
)
def query(question: str, output: str | None) -> None:
    """Ask a question against the wiki."""
    from wikiforge.query import run_query
    from wikiforge.vault import resolve_vault

    vault = resolve_vault()
    config = vault.load_config()

    if not config.get_api_key():
        raise click.ClickException(
            f"API key not found. Set the {config.llm.api_key_env} environment variable."
        )

    output_path = Path(output) if output else None
    if output_path and not output_path.is_absolute():
        output_path = vault.outputs_dir / output_path

    result = run_query(vault, config, question, output_path=output_path)

    click.echo(result.answer)

    if result.articles_used:
        click.echo(f"\n---\nBased on: {', '.join(result.articles_used)}")

    if output_path:
        click.echo(f"\nAnswer saved to {output_path}")


@cli.command()
def status() -> None:
    """Show vault statistics and pipeline state."""
    from wikiforge.index import load_index
    from wikiforge.manifest import load_manifest
    from wikiforge.models import SourceStatus
    from wikiforge.vault import resolve_vault

    vault = resolve_vault()
    config = vault.load_config()
    manifest = load_manifest(vault.manifest_path)
    index = load_index(vault.index_path)

    # Count sources by status
    total = len(manifest.sources)
    pending = sum(1 for e in manifest.sources.values() if e.status == SourceStatus.pending)
    compiled = sum(1 for e in manifest.sources.values() if e.status == SourceStatus.compiled)
    errors = sum(1 for e in manifest.sources.values() if e.status == SourceStatus.error)

    # Count files in directories
    raw_files = sum(1 for _ in vault.raw_dir.rglob("*") if _.is_file()) if vault.raw_dir.exists() else 0
    wiki_files = sum(
        1 for f in vault.wiki_dir.rglob("*.md")
        if f.is_file() and f.name != "_index.md"
    ) if vault.wiki_dir.exists() else 0
    output_files = sum(1 for _ in vault.outputs_dir.rglob("*") if _.is_file()) if vault.outputs_dir.exists() else 0

    # Categories
    categories: dict[str, int] = {}
    for entry in index.entries:
        categories[entry.category] = categories.get(entry.category, 0) + 1

    click.echo(f"WikiForge Vault: {config.project_name}")
    click.echo(f"Path: {vault.root}")
    click.echo(f"LLM: {config.llm.provider}/{config.llm.model}")
    click.echo()
    click.echo(f"Sources: {total} total ({pending} pending, {compiled} compiled, {errors} errors)")
    click.echo(f"Raw files: {raw_files}")
    click.echo(f"Wiki articles: {wiki_files}")
    click.echo(f"Index entries: {len(index.entries)}")
    click.echo(f"Output files: {output_files}")

    if categories:
        click.echo()
        click.echo("Articles by category:")
        for cat, count in sorted(categories.items()):
            click.echo(f"  {cat}: {count}")


@cli.command()
@click.argument("term")
def search(term: str) -> None:
    """Search wiki articles by keyword (non-LLM)."""
    from wikiforge.index import load_index
    from wikiforge.vault import resolve_vault

    vault = resolve_vault()
    index = load_index(vault.index_path)

    term_lower = term.lower()
    matches = [
        entry
        for entry in index.entries
        if term_lower in entry.title.lower() or term_lower in entry.summary.lower()
    ]

    if not matches:
        click.echo(f"No articles matching '{term}'")
        return

    click.echo(f"Found {len(matches)} article(s) matching '{term}':\n")
    for entry in matches:
        click.echo(f"  [{entry.category}] {entry.title}")
        click.echo(f"    {entry.summary}")
        click.echo(f"    Path: wiki/{entry.path}")
        click.echo()
