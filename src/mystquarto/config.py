"""Config conversion: myst.yml <-> _quarto.yml."""

from __future__ import annotations

import os

import yaml


def _is_book_project(myst_config: dict) -> bool:
    """Detect if a MyST config represents a book-type project.

    Book type is indicated by either:
    - site.template == "book-theme"
    - presence of project.toc
    """
    site = myst_config.get("site", {})
    if site.get("template") == "book-theme":
        return True
    project = myst_config.get("project", {})
    if "toc" in project:
        return True
    return False


def _toc_to_chapters(toc: list[dict]) -> list[str]:
    """Convert MyST toc entries to Quarto chapter file list.

    Each entry is a dict with a 'file' key (with or without extension).
    Returns list of filenames with .qmd extension.
    """
    chapters = []
    for entry in toc:
        if isinstance(entry, dict) and "file" in entry:
            name = entry["file"]
        elif isinstance(entry, str):
            name = entry
        else:
            continue
        # Strip existing .md extension before adding .qmd
        if name.endswith(".md"):
            name = name[:-3]
        chapters.append(f"{name}.qmd")
    return chapters


def _chapters_to_toc(chapters: list[str]) -> list[dict]:
    """Convert Quarto chapter file list to MyST toc entries.

    Each chapter is a filename (possibly with .qmd extension).
    Returns list of dicts with 'file' key (no extension).
    """
    toc = []
    for chapter in chapters:
        filename = chapter
        # Strip .qmd or .md extension
        for ext in (".qmd", ".md"):
            if filename.endswith(ext):
                filename = filename[: -len(ext)]
                break
        toc.append({"file": filename})
    return toc


def _convert_authors_myst_to_quarto(authors: list[dict]) -> list[dict]:
    """Convert MyST author entries to Quarto format.

    Both use similar structures with name and affiliations.
    """
    result = []
    for author in authors:
        entry = {}
        if "name" in author:
            entry["name"] = author["name"]
        if "affiliations" in author:
            entry["affiliations"] = author["affiliations"]
        # Pass through any other fields
        for key, value in author.items():
            if key not in ("name", "affiliations"):
                entry[key] = value
        result.append(entry)
    return result


def _convert_exports_to_format(exports: list[dict]) -> dict:
    """Convert MyST exports list to Quarto format block.

    Each export has a 'format' key (pdf, docx, etc.) and other options.
    """
    format_block = {}
    for export in exports:
        fmt = export.get("format")
        if not fmt:
            continue
        # Copy all options except 'format' itself
        options = {k: v for k, v in export.items() if k != "format"}
        format_block[fmt] = options if options else {}
    return format_block


def _convert_format_to_exports(format_block: dict) -> list[dict]:
    """Convert Quarto format block to MyST exports list."""
    exports = []
    for fmt, options in format_block.items():
        export = {"format": fmt}
        if isinstance(options, dict):
            export.update(options)
        exports.append(export)
    return exports


def myst_to_quarto_config(myst_config: dict) -> dict:
    """Convert a parsed myst.yml dict to a _quarto.yml dict.

    Handles both book-type and article/manuscript projects.
    """
    if not myst_config:
        return {}

    project = myst_config.get("project", {})
    if not project:
        return {}

    result = {}
    is_book = _is_book_project(myst_config)

    if is_book:
        # Book-type project
        result["project"] = {"type": "book"}
        book = {}

        if "title" in project:
            book["title"] = project["title"]
        if "authors" in project:
            book["author"] = _convert_authors_myst_to_quarto(project["authors"])
        if "toc" in project:
            book["chapters"] = _toc_to_chapters(project["toc"])

        result["book"] = book
    else:
        # Article/manuscript project
        if "title" in project:
            result["title"] = project["title"]
        if "authors" in project:
            result["author"] = _convert_authors_myst_to_quarto(project["authors"])

    # Fields that apply to both types
    if "bibliography" in project:
        result["bibliography"] = project["bibliography"]

    if "exports" in project:
        result["format"] = _convert_exports_to_format(project["exports"])

    if "github" in project:
        result["repo-url"] = project["github"]

    if "license" in project:
        result["license"] = project["license"]

    if "keywords" in project:
        result["keywords"] = project["keywords"]

    if "date" in project:
        result["date"] = project["date"]

    if "subject" in project:
        result["description"] = project["subject"]

    return result


def quarto_to_myst_config(quarto_config: dict) -> dict:
    """Convert a parsed _quarto.yml dict to a myst.yml dict.

    Handles both book-type and article/manuscript projects.
    """
    if not quarto_config:
        return {}

    result = {}
    project = {}
    is_book = (
        quarto_config.get("project", {}).get("type") == "book"
        or "book" in quarto_config
    )

    if is_book:
        book = quarto_config.get("book", {})
        if "title" in book:
            project["title"] = book["title"]
        if "author" in book:
            project["authors"] = book["author"]
        if "chapters" in book:
            project["toc"] = _chapters_to_toc(book["chapters"])
        result["site"] = {"template": "book-theme"}
    else:
        if "title" in quarto_config:
            project["title"] = quarto_config["title"]
        if "author" in quarto_config:
            project["authors"] = quarto_config["author"]

    # Fields that apply to both types
    if "bibliography" in quarto_config:
        project["bibliography"] = quarto_config["bibliography"]

    if "format" in quarto_config:
        project["exports"] = _convert_format_to_exports(quarto_config["format"])

    if "repo-url" in quarto_config:
        project["github"] = quarto_config["repo-url"]

    if "license" in quarto_config:
        project["license"] = quarto_config["license"]

    if "keywords" in quarto_config:
        project["keywords"] = quarto_config["keywords"]

    if "date" in quarto_config:
        project["date"] = quarto_config["date"]

    if "description" in quarto_config:
        project["subject"] = quarto_config["description"]

    if project:
        result["project"] = project

    return result


def convert_myst_config(myst_yml_path: str, output_dir: str) -> str:
    """Read myst.yml, convert to _quarto.yml, write to output_dir.

    Args:
        myst_yml_path: Path to the input myst.yml file.
        output_dir: Directory to write _quarto.yml to.

    Returns:
        Path to the output _quarto.yml file.
    """
    with open(myst_yml_path) as f:
        myst_config = yaml.safe_load(f) or {}

    quarto_config = myst_to_quarto_config(myst_config)

    output_path = os.path.join(output_dir, "_quarto.yml")
    with open(output_path, "w") as f:
        yaml.dump(quarto_config, f, default_flow_style=False, sort_keys=False)

    return output_path


def convert_quarto_config(quarto_yml_path: str, output_dir: str) -> str:
    """Read _quarto.yml, convert to myst.yml, write to output_dir.

    Args:
        quarto_yml_path: Path to the input _quarto.yml file.
        output_dir: Directory to write myst.yml to.

    Returns:
        Path to the output myst.yml file.
    """
    with open(quarto_yml_path) as f:
        quarto_config = yaml.safe_load(f) or {}

    myst_config = quarto_to_myst_config(quarto_config)

    output_path = os.path.join(output_dir, "myst.yml")
    with open(output_path, "w") as f:
        yaml.dump(myst_config, f, default_flow_style=False, sort_keys=False)

    return output_path
