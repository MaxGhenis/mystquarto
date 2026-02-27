"""Click CLI for mystquarto: bidirectional MyST <-> Quarto converter."""

from __future__ import annotations

import sys

import click

from mystquarto.convert import Direction, convert_directory
from mystquarto.warnings import WarningCollector


def _run_conversion(
    path: str,
    output: str | None,
    in_place: bool,
    config_only: bool,
    no_config: bool,
    dry_run: bool,
    strict: bool,
    direction: Direction,
) -> None:
    """Shared implementation for both conversion directions.

    Args:
        path: Input file or directory path.
        output: Output directory path (or None).
        in_place: Whether to modify files in-place.
        config_only: Only convert config files.
        no_config: Skip config file conversion.
        dry_run: Show what would change without writing.
        strict: Treat warnings as errors.
        direction: Conversion direction.
    """
    collector = WarningCollector(strict=strict)

    results = convert_directory(
        input_dir=path,
        output_dir=output,
        direction=direction,
        in_place=in_place,
        config_only=config_only,
        no_config=no_config,
        dry_run=dry_run,
    )

    # Collect warnings and errors from results
    for result in results:
        for warning in result.warnings:
            collector.warn(warning)
        for error in result.errors:
            collector.error(error)

    # Report
    converted_count = sum(
        1 for r in results if not r.skipped and not r.errors
    )
    label = "Would convert" if dry_run else "Converted"

    if dry_run:
        for result in results:
            if not result.skipped and result.output_path:
                click.echo(f"  {result.input_path} -> {result.output_path}")

    click.echo(f"{label} {converted_count} file(s).")

    if collector.warnings or collector.errors:
        click.echo(collector.report())

    if collector.has_errors():
        sys.exit(1)


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--in-place", is_flag=True, help="Modify files in-place")
@click.option("--config-only", is_flag=True, help="Only convert config files")
@click.option("--no-config", is_flag=True, help="Skip config file conversion")
@click.option(
    "--dry-run", is_flag=True, help="Show what would change without writing"
)
@click.option("--strict", is_flag=True, help="Treat warnings as errors")
def myst2quarto(path, output, in_place, config_only, no_config, dry_run, strict):
    """Convert MyST markdown files to Quarto format."""
    _run_conversion(
        path=path,
        output=output,
        in_place=in_place,
        config_only=config_only,
        no_config=no_config,
        dry_run=dry_run,
        strict=strict,
        direction=Direction.MYST_TO_QUARTO,
    )


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--in-place", is_flag=True, help="Modify files in-place")
@click.option("--config-only", is_flag=True, help="Only convert config files")
@click.option("--no-config", is_flag=True, help="Skip config file conversion")
@click.option(
    "--dry-run", is_flag=True, help="Show what would change without writing"
)
@click.option("--strict", is_flag=True, help="Treat warnings as errors")
def quarto2myst(path, output, in_place, config_only, no_config, dry_run, strict):
    """Convert Quarto markdown files to MyST format."""
    _run_conversion(
        path=path,
        output=output,
        in_place=in_place,
        config_only=config_only,
        no_config=no_config,
        dry_run=dry_run,
        strict=strict,
        direction=Direction.QUARTO_TO_MYST,
    )


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Bidirectional MyST <-> Quarto converter."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command("to-quarto")
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--in-place", is_flag=True, help="Modify files in-place")
@click.option("--config-only", is_flag=True, help="Only convert config files")
@click.option("--no-config", is_flag=True, help="Skip config file conversion")
@click.option(
    "--dry-run", is_flag=True, help="Show what would change without writing"
)
@click.option("--strict", is_flag=True, help="Treat warnings as errors")
def to_quarto(path, output, in_place, config_only, no_config, dry_run, strict):
    """Convert MyST markdown files to Quarto format."""
    _run_conversion(
        path=path,
        output=output,
        in_place=in_place,
        config_only=config_only,
        no_config=no_config,
        dry_run=dry_run,
        strict=strict,
        direction=Direction.MYST_TO_QUARTO,
    )


@main.command("to-myst")
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--in-place", is_flag=True, help="Modify files in-place")
@click.option("--config-only", is_flag=True, help="Only convert config files")
@click.option("--no-config", is_flag=True, help="Skip config file conversion")
@click.option(
    "--dry-run", is_flag=True, help="Show what would change without writing"
)
@click.option("--strict", is_flag=True, help="Treat warnings as errors")
def to_myst(path, output, in_place, config_only, no_config, dry_run, strict):
    """Convert Quarto markdown files to MyST format."""
    _run_conversion(
        path=path,
        output=output,
        in_place=in_place,
        config_only=config_only,
        no_config=no_config,
        dry_run=dry_run,
        strict=strict,
        direction=Direction.QUARTO_TO_MYST,
    )
