"""File discovery and conversion orchestration."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum

import yaml

from mystquarto.config import convert_myst_config, convert_quarto_config
from mystquarto.frontmatter import (
    extract_frontmatter,
    myst_to_quarto_frontmatter,
    quarto_to_myst_frontmatter,
)
from mystquarto.transforms.myst_to_quarto import convert_myst_to_quarto
from mystquarto.transforms.quarto_to_myst import convert_quarto_to_myst


class Direction(Enum):
    """Conversion direction."""

    MYST_TO_QUARTO = "myst_to_quarto"
    QUARTO_TO_MYST = "quarto_to_myst"


@dataclass
class ConversionResult:
    """Result of converting a single file."""

    input_path: str
    output_path: str | None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: bool = False
    dry_run: bool = False


# File extensions for each direction
_MYST_EXTENSIONS = {".md"}
_QUARTO_EXTENSIONS = {".qmd"}
_MYST_CONFIG = "myst.yml"
_QUARTO_CONFIG = "_quarto.yml"


def discover_files(directory: str, direction: Direction) -> list[str]:
    """Find all convertible files in a directory.

    For MyST->Quarto: finds .md files + myst.yml
    For Quarto->MyST: finds .qmd files + _quarto.yml

    Args:
        directory: Path to the directory to search.
        direction: Conversion direction.

    Returns:
        List of absolute file paths.
    """
    if direction == Direction.MYST_TO_QUARTO:
        extensions = _MYST_EXTENSIONS
        config_name = _MYST_CONFIG
    else:
        extensions = _QUARTO_EXTENSIONS
        config_name = _QUARTO_CONFIG

    # Directories to skip
    skip_dirs = {
        "_build", ".git", ".hg", "__pycache__", "node_modules",
        ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache",
        "_site", ".quarto",
    }

    files: list[str] = []

    for root, dirs, filenames in os.walk(directory):
        # Prune skipped directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for filename in filenames:
            filepath = os.path.join(root, filename)
            _, ext = os.path.splitext(filename)

            if ext in extensions:
                files.append(filepath)
            elif filename == config_name:
                files.append(filepath)

    return sorted(files)


def convert_file(
    input_path: str,
    output_path: str,
    direction: Direction,
    dry_run: bool = False,
) -> ConversionResult:
    """Convert a single markdown file.

    Args:
        input_path: Path to the input file.
        output_path: Path for the output file.
        direction: Conversion direction.
        dry_run: If True, do not write output.

    Returns:
        ConversionResult with details about the conversion.
    """
    result = ConversionResult(
        input_path=input_path,
        output_path=output_path,
        dry_run=dry_run,
    )

    # Read input
    try:
        with open(input_path) as f:
            text = f.read()
    except (OSError, IOError) as e:
        result.errors.append(f"Could not read {input_path}: {e}")
        return result

    # Extract and transform frontmatter
    fm, body = extract_frontmatter(text)
    if fm:
        if direction == Direction.MYST_TO_QUARTO:
            new_fm = myst_to_quarto_frontmatter(fm)
        else:
            new_fm = quarto_to_myst_frontmatter(fm)
    else:
        new_fm = None

    # Transform body text
    if direction == Direction.MYST_TO_QUARTO:
        transformed_body = convert_myst_to_quarto(body)
    else:
        transformed_body = convert_quarto_to_myst(body)

    # Reconstruct full text
    if new_fm:
        fm_yaml = yaml.dump(new_fm, default_flow_style=False, sort_keys=False)
        output_text = "---\n" + fm_yaml + "---\n" + transformed_body
    else:
        output_text = transformed_body

    # Write output (unless dry_run)
    if not dry_run:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        try:
            with open(output_path, "w") as f:
                f.write(output_text)
        except (OSError, IOError) as e:
            result.errors.append(f"Could not write {output_path}: {e}")

    return result


def _get_output_path(
    input_path: str,
    input_dir: str,
    output_dir: str,
    direction: Direction,
) -> str:
    """Compute the output path for a file, changing extension as needed.

    Args:
        input_path: Absolute path to the input file.
        input_dir: The base input directory.
        output_dir: The base output directory.
        direction: Conversion direction.

    Returns:
        The output file path.
    """
    # Get relative path from input dir
    rel_path = os.path.relpath(input_path, input_dir)
    base, ext = os.path.splitext(rel_path)

    # Change extension
    if direction == Direction.MYST_TO_QUARTO:
        if ext == ".md":
            new_ext = ".qmd"
        else:
            new_ext = ext
    else:
        if ext == ".qmd":
            new_ext = ".md"
        else:
            new_ext = ext

    return os.path.join(output_dir, base + new_ext)


def _default_output_dir(input_dir: str, direction: Direction) -> str:
    """Generate a default output directory name.

    Args:
        input_dir: The input directory path.
        direction: Conversion direction.

    Returns:
        Path to the default output directory.
    """
    suffix = "-quarto" if direction == Direction.MYST_TO_QUARTO else "-myst"
    return input_dir.rstrip(os.sep) + suffix


def convert_directory(
    input_dir: str,
    output_dir: str | None,
    direction: Direction,
    in_place: bool = False,
    config_only: bool = False,
    no_config: bool = False,
    dry_run: bool = False,
) -> list[ConversionResult]:
    """Convert all files in a directory.

    Args:
        input_dir: Path to input directory or single file.
        output_dir: Path to output directory (None for default).
        direction: Conversion direction.
        in_place: If True, overwrite source files.
        config_only: If True, only convert config files.
        no_config: If True, skip config file conversion.
        dry_run: If True, do not write any files.

    Returns:
        List of ConversionResult for each processed file.
    """
    results: list[ConversionResult] = []

    # Handle single file path
    if os.path.isfile(input_dir):
        return _convert_single_file_path(
            input_dir, output_dir, direction, dry_run
        )

    # Determine output directory
    if in_place:
        effective_output_dir = input_dir
    elif output_dir:
        effective_output_dir = output_dir
    else:
        effective_output_dir = _default_output_dir(input_dir, direction)

    # Create output directory if needed (unless dry_run)
    if not dry_run:
        os.makedirs(effective_output_dir, exist_ok=True)

    # Discover files
    all_files = discover_files(input_dir, direction)

    # Separate config files from markdown files
    config_name = _MYST_CONFIG if direction == Direction.MYST_TO_QUARTO else _QUARTO_CONFIG
    config_files = [f for f in all_files if os.path.basename(f) == config_name]
    md_files = [f for f in all_files if os.path.basename(f) != config_name]

    # Convert config files
    if not no_config:
        for config_path in config_files:
            config_result = _convert_config_file(
                config_path, input_dir, effective_output_dir, direction, dry_run
            )
            results.append(config_result)

    # Convert markdown files (unless config_only)
    if not config_only:
        for md_path in md_files:
            out_path = _get_output_path(
                md_path, input_dir, effective_output_dir, direction
            )
            md_result = convert_file(md_path, out_path, direction, dry_run)
            results.append(md_result)

            # If in-place, remove original file (it has been renamed)
            if in_place and not dry_run and not md_result.errors:
                if md_path != out_path and os.path.exists(md_path):
                    os.remove(md_path)

    # Copy non-markdown assets to output (bib, images, etc.)
    if not in_place and not dry_run and not config_only:
        _copy_assets(input_dir, effective_output_dir, direction)

    return results


def _convert_single_file_path(
    file_path: str,
    output_dir: str | None,
    direction: Direction,
    dry_run: bool,
) -> list[ConversionResult]:
    """Handle conversion when input path is a single file."""
    parent_dir = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    base, ext = os.path.splitext(filename)

    # Determine output directory
    if output_dir is None:
        output_dir = _default_output_dir(parent_dir, direction)

    # Create output directory
    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)

    # Determine output filename with new extension
    if direction == Direction.MYST_TO_QUARTO and ext == ".md":
        out_filename = base + ".qmd"
    elif direction == Direction.QUARTO_TO_MYST and ext == ".qmd":
        out_filename = base + ".md"
    else:
        out_filename = filename

    out_path = os.path.join(output_dir, out_filename)

    result = convert_file(file_path, out_path, direction, dry_run)
    return [result]


def _copy_assets(
    input_dir: str, output_dir: str, direction: Direction
) -> None:
    """Copy non-markdown assets (bib, images, static dirs) to output."""
    skip_dirs = {
        "_build", ".git", ".hg", "__pycache__", "node_modules",
        ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache",
        "_site", ".quarto",
    }
    md_exts = _MYST_EXTENSIONS | _QUARTO_EXTENSIONS
    config_names = {_MYST_CONFIG, _QUARTO_CONFIG}

    for root, dirs, filenames in os.walk(input_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext in md_exts or filename in config_names:
                continue

            src = os.path.join(root, filename)
            rel = os.path.relpath(src, input_dir)
            dst = os.path.join(output_dir, rel)

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)


def _convert_config_file(
    config_path: str,
    input_dir: str,
    output_dir: str,
    direction: Direction,
    dry_run: bool,
) -> ConversionResult:
    """Convert a config file (myst.yml or _quarto.yml).

    Args:
        config_path: Path to the config file.
        input_dir: Base input directory.
        output_dir: Base output directory.
        direction: Conversion direction.
        dry_run: If True, do not write.

    Returns:
        ConversionResult for the config conversion.
    """
    result = ConversionResult(
        input_path=config_path,
        output_path=None,
        dry_run=dry_run,
    )

    if dry_run:
        if direction == Direction.MYST_TO_QUARTO:
            result.output_path = os.path.join(output_dir, _QUARTO_CONFIG)
        else:
            result.output_path = os.path.join(output_dir, _MYST_CONFIG)
        return result

    try:
        os.makedirs(output_dir, exist_ok=True)

        if direction == Direction.MYST_TO_QUARTO:
            out_path = convert_myst_config(config_path, output_dir)
        else:
            out_path = convert_quarto_config(config_path, output_dir)

        result.output_path = out_path
    except Exception as e:
        result.errors.append(f"Config conversion failed: {e}")

    return result
