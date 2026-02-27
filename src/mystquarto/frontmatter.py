"""Frontmatter conversion: MyST <-> Quarto per-file YAML frontmatter."""

from __future__ import annotations


import yaml


# Fields that are MyST-only and should be removed when converting to Quarto
_MYST_ONLY_FIELDS = {"math", "abbreviations"}

# Fields that pass through unchanged in both directions
_PASSTHROUGH_FIELDS = {"title", "author", "date", "tags"}


def extract_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split text into (frontmatter_dict, body_text).

    Returns (None, text) if no frontmatter is found.
    Frontmatter must be between --- markers at the start of the file.
    """
    if not text:
        return None, text

    # Frontmatter must start at the very beginning
    if not text.startswith("---"):
        return None, text

    # Find the closing ---
    # Split after the first line (which is ---)
    lines = text.split("\n")
    if len(lines) < 2:
        return None, text

    # Find closing --- (must be on its own line)
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None, text

    # Parse the YAML between the markers
    yaml_text = "\n".join(lines[1:end_idx])
    try:
        fm = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None, text

    if not isinstance(fm, dict):
        return None, text

    # Body is everything after the closing ---
    body = "\n".join(lines[end_idx + 1 :])

    return fm, body


def replace_frontmatter(text: str, new_fm: dict) -> str:
    """Replace frontmatter in text with new dict. Add if none existed.

    Args:
        text: The document text (may or may not have existing frontmatter).
        new_fm: The new frontmatter dict to insert.

    Returns:
        Text with updated frontmatter.
    """
    _, body = extract_frontmatter(text)

    # Dump the new frontmatter
    fm_yaml = yaml.dump(new_fm, default_flow_style=False, sort_keys=False)

    # Build result: --- marker, yaml, --- marker, body
    result = "---\n" + fm_yaml + "---\n" + body

    return result


def myst_to_quarto_frontmatter(fm: dict) -> dict:
    """Convert MyST frontmatter dict to Quarto frontmatter dict.

    Handles:
    - kernelspec -> jupyter
    - jupytext -> removed
    - exports -> format
    - label -> id
    - math, abbreviations -> removed
    - numbering.equation.template -> crossref.eq-prefix
    - Passthrough: title, author, date, tags
    """
    if not fm:
        return {}

    result = {}

    for key, value in fm.items():
        # kernelspec -> jupyter
        if key == "kernelspec":
            kernel_name = (
                value.get("name", "python3") if isinstance(value, dict) else value
            )
            result["jupyter"] = kernel_name
            continue

        # jupytext -> remove
        if key == "jupytext":
            continue

        # MyST-only fields -> remove
        if key in _MYST_ONLY_FIELDS:
            continue

        # label -> id
        if key == "label":
            result["id"] = value
            continue

        # exports -> format
        if key == "exports":
            format_block = {}
            for export in value:
                fmt = export.get("format")
                if not fmt:
                    continue
                options = {k: v for k, v in export.items() if k != "format"}
                format_block[fmt] = options if options else {}
            result["format"] = format_block
            continue

        # numbering.equation.template -> crossref.eq-prefix
        if key == "numbering":
            eq_config = value.get("equation", {}) if isinstance(value, dict) else {}
            template = eq_config.get("template")
            if template:
                result["crossref"] = {"eq-prefix": template}
            continue

        # Everything else passes through
        result[key] = value

    return result


def quarto_to_myst_frontmatter(fm: dict) -> dict:
    """Convert Quarto frontmatter dict to MyST frontmatter dict.

    Reverse mapping of myst_to_quarto_frontmatter.
    """
    if not fm:
        return {}

    result = {}

    for key, value in fm.items():
        # jupyter -> kernelspec
        if key == "jupyter":
            kernel_name = (
                value if isinstance(value, str) else value.get("name", "python3")
            )
            result["kernelspec"] = {
                "name": kernel_name,
                "display_name": kernel_name.replace("python3", "Python 3").replace(
                    "ir", "R"
                ),
            }
            continue

        # id -> label
        if key == "id":
            result["label"] = value
            continue

        # format -> exports
        if key == "format":
            exports = []
            if isinstance(value, dict):
                for fmt, options in value.items():
                    export = {"format": fmt}
                    if isinstance(options, dict):
                        export.update(options)
                    exports.append(export)
            result["exports"] = exports
            continue

        # crossref.eq-prefix -> numbering.equation.template
        if key == "crossref":
            eq_prefix = value.get("eq-prefix") if isinstance(value, dict) else None
            if eq_prefix:
                result["numbering"] = {"equation": {"template": eq_prefix}}
            continue

        # Everything else passes through
        result[key] = value

    return result
