"""MyST -> Quarto transform rules: block directives and inline roles."""

from __future__ import annotations

import re

from mystquarto.scanner import DirectiveFrame, Scanner

# ---------------------------------------------------------------------------
# Inline role transform patterns
# ---------------------------------------------------------------------------

# {eval}`expr`
_EVAL_RE = re.compile(r"\{eval\}`([^`]+)`")

# {cite:t}`key`  (must come before generic {cite})
_CITE_T_RE = re.compile(r"\{cite:t\}`([^`]+)`")

# {cite:p}`key`  (must come before generic {cite})
_CITE_P_RE = re.compile(r"\{cite:p\}`([^`]+)`")

# {cite}`key` or {cite}`key1,key2,...`
_CITE_RE = re.compile(r"\{cite\}`([^`]+)`")

# {numref}`Figure %s <fig-id>` or {numref}`fig-id`
_NUMREF_RE = re.compile(r"\{numref\}`([^`]+)`")

# {ref}`label`
_REF_RE = re.compile(r"\{ref\}`([^`]+)`")

# {eq}`label`
_EQ_RE = re.compile(r"\{eq\}`([^`]+)`")

# {doc}`path`
_DOC_RE = re.compile(r"\{doc\}`([^`]+)`")

# Admonition types that map directly
_ADMONITION_TYPES = {"note", "warning", "tip", "important", "caution"}

# Tag -> Quarto cell option mapping
_TAG_MAP = {
    "remove-cell": "#| include: false",
    "remove-input": "#| echo: false",
    "remove-output": "#| output: false",
    "hide-input": "#| code-fold: true",
}


# ---------------------------------------------------------------------------
# Inline role transforms
# ---------------------------------------------------------------------------


def _replace_eval(m: re.Match) -> str:
    return f"`{{python}} {m.group(1)}`"


def _replace_cite_t(m: re.Match) -> str:
    return f"@{m.group(1).strip()}"


def _replace_cite_p(m: re.Match) -> str:
    keys = [k.strip() for k in m.group(1).split(",")]
    if len(keys) == 1:
        return f"[@{keys[0]}]"
    return "[" + "; ".join(f"@{k}" for k in keys) + "]"


def _replace_cite(m: re.Match) -> str:
    keys = [k.strip() for k in m.group(1).split(",")]
    if len(keys) == 1:
        return f"[@{keys[0]}]"
    return "[" + "; ".join(f"@{k}" for k in keys) + "]"


def _replace_numref(m: re.Match) -> str:
    content = m.group(1).strip()
    # Handle format string: {numref}`Figure %s <fig-id>`
    angle_m = re.match(r".*<(.+)>$", content)
    if angle_m:
        return f"@{angle_m.group(1).strip()}"
    return f"@{content}"


def _replace_ref(m: re.Match) -> str:
    return f"@{m.group(1).strip()}"


def _replace_eq(m: re.Match) -> str:
    label = m.group(1).strip()
    if not label.startswith("eq-"):
        label = f"eq-{label}"
    return f"@{label}"


def _replace_doc(m: re.Match) -> str:
    path = m.group(1).strip()
    return f"[{path}]({path}.qmd)"


def transform_inline(line: str) -> str:
    """Transform MyST inline roles to Quarto syntax on a single line.

    MyST roles use the syntax {role}`content`, where the backtick-delimited
    part is NOT a regular code span. We apply role transforms first (they
    match the full {role}`content` pattern), then leave actual code spans
    (backtick text without a preceding {role}) untouched.
    """
    if not line:
        return line

    # Apply all inline role transforms directly on the full line.
    # The regexes are specific enough ({role}`...`) that they will not
    # match inside regular code spans (which lack the {role} prefix).
    # cite:t and cite:p must come before generic cite
    result = _EVAL_RE.sub(_replace_eval, line)
    result = _CITE_T_RE.sub(_replace_cite_t, result)
    result = _CITE_P_RE.sub(_replace_cite_p, result)
    result = _CITE_RE.sub(_replace_cite, result)
    result = _NUMREF_RE.sub(_replace_numref, result)
    result = _REF_RE.sub(_replace_ref, result)
    result = _EQ_RE.sub(_replace_eq, result)
    result = _DOC_RE.sub(_replace_doc, result)

    return result


# ---------------------------------------------------------------------------
# Block directive transforms
# ---------------------------------------------------------------------------


def _parse_tags(tags_str: str) -> list[str]:
    """Parse a tags option value like '[remove-input]' or 'remove-input'."""
    # Remove brackets and quotes
    cleaned = tags_str.strip().strip("[]")
    return [t.strip().strip("'\"") for t in cleaned.split(",") if t.strip()]


def transform_directive(frame: DirectiveFrame) -> list[str]:
    """Transform a single MyST directive to Quarto output lines.

    Args:
        frame: The parsed directive frame.

    Returns:
        A list of output lines (without trailing newlines).
    """
    name = frame.name

    # ------------------------------------------------------------------
    # code-cell
    # ------------------------------------------------------------------
    if name == "code-cell":
        return _transform_code_cell(frame)

    # ------------------------------------------------------------------
    # figure
    # ------------------------------------------------------------------
    if name == "figure":
        return _transform_figure(frame)

    # ------------------------------------------------------------------
    # math
    # ------------------------------------------------------------------
    if name == "math":
        return _transform_math(frame)

    # ------------------------------------------------------------------
    # Admonitions: note, warning, tip, important, caution
    # ------------------------------------------------------------------
    if name in _ADMONITION_TYPES:
        return _transform_admonition(frame, name)

    # ------------------------------------------------------------------
    # admonition (generic with custom title)
    # ------------------------------------------------------------------
    if name == "admonition":
        return _transform_admonition(frame, "note", title=frame.argument)

    # ------------------------------------------------------------------
    # bibliography -> remove entirely
    # ------------------------------------------------------------------
    if name == "bibliography":
        return []

    # ------------------------------------------------------------------
    # abstract -> remove from body (would go in frontmatter)
    # ------------------------------------------------------------------
    if name == "abstract":
        return []

    # ------------------------------------------------------------------
    # tab-set
    # ------------------------------------------------------------------
    if name == "tab-set":
        return _transform_tab_set(frame)

    # ------------------------------------------------------------------
    # tab-item
    # ------------------------------------------------------------------
    if name == "tab-item":
        return _transform_tab_item(frame)

    # ------------------------------------------------------------------
    # margin
    # ------------------------------------------------------------------
    if name == "margin":
        return _transform_margin(frame)

    # ------------------------------------------------------------------
    # image
    # ------------------------------------------------------------------
    if name == "image":
        return _transform_image(frame)

    # ------------------------------------------------------------------
    # table
    # ------------------------------------------------------------------
    if name == "table":
        return _transform_table(frame)

    # ------------------------------------------------------------------
    # tableofcontents -> remove entirely
    # ------------------------------------------------------------------
    if name == "tableofcontents":
        return []

    # ------------------------------------------------------------------
    # mermaid -> pass through unchanged
    # ------------------------------------------------------------------
    if name == "mermaid":
        return _transform_mermaid(frame)

    # ------------------------------------------------------------------
    # Unknown directive -> pass through with warning
    # ------------------------------------------------------------------
    return _transform_unknown(frame)


def _transform_code_cell(frame: DirectiveFrame) -> list[str]:
    """Transform code-cell directive to Quarto executable code block."""
    lang = frame.argument.strip() if frame.argument else "python"
    # Map common aliases
    if lang == "ipython3":
        lang = "python"

    lines: list[str] = []
    lines.append(f"```{{{lang}}}")

    # Process tags
    tags = _parse_tags(frame.options.get("tags", ""))
    for tag in tags:
        quarto_opt = _TAG_MAP.get(tag)
        if quarto_opt:
            lines.append(quarto_opt)

    # Process caption
    caption = frame.options.get("caption", "")
    if caption:
        lines.append(f'#| fig-cap: "{caption}"')

    # Add blank line after options if we had any cell options
    if len(lines) > 1:
        lines.append("")

    # Body
    lines.extend(frame.body_lines)
    lines.append("```")
    return lines


def _transform_figure(frame: DirectiveFrame) -> list[str]:
    """Transform figure directive to Quarto image syntax."""
    path = frame.argument.strip()
    caption = " ".join(line.strip() for line in frame.body_lines if line.strip())
    name = frame.options.get("name", "")
    width = frame.options.get("width", "")

    attrs = []
    if name:
        attrs.append(f"#{name}")
    if width:
        attrs.append(f'width="{width}"')

    attr_str = ""
    if attrs:
        attr_str = "{" + " ".join(attrs) + "}"

    img_line = f"![{caption}]({path})"
    if attr_str:
        img_line += attr_str

    return [img_line]


def _transform_math(frame: DirectiveFrame) -> list[str]:
    """Transform math directive to Quarto $$ block."""
    label = frame.options.get("label", "")

    lines = ["$$"]
    lines.extend(frame.body_lines)

    if label:
        lines.append(f"$$ {{#{label}}}")
    else:
        lines.append("$$")

    return lines


def _transform_admonition(
    frame: DirectiveFrame, adm_type: str, title: str = ""
) -> list[str]:
    """Transform admonition directives to Quarto callouts."""
    if title:
        header = f'::: {{.callout-{adm_type} title="{title}"}}'
    else:
        header = f"::: {{.callout-{adm_type}}}"

    lines = [header]
    lines.extend(frame.body_lines)
    lines.append(":::")
    return lines


def _transform_tab_set(frame: DirectiveFrame) -> list[str]:
    """Transform tab-set to Quarto panel-tabset."""
    lines = ["::: {.panel-tabset}"]
    lines.extend(frame.body_lines)
    lines.append(":::")
    return lines


def _transform_tab_item(frame: DirectiveFrame) -> list[str]:
    """Transform tab-item to Quarto heading inside panel-tabset."""
    label = frame.argument.strip()
    lines = [f"## {label}"]
    lines.extend(frame.body_lines)
    return lines


def _transform_margin(frame: DirectiveFrame) -> list[str]:
    """Transform margin directive to Quarto column-margin."""
    lines = ["::: {.column-margin}"]
    lines.extend(frame.body_lines)
    lines.append(":::")
    return lines


def _transform_image(frame: DirectiveFrame) -> list[str]:
    """Transform image directive to Quarto inline image."""
    url = frame.argument.strip()
    alt = frame.options.get("alt", "")
    width = frame.options.get("width", "")

    attrs = []
    if width:
        attrs.append(f'width="{width}"')

    attr_str = ""
    if attrs:
        attr_str = "{" + " ".join(attrs) + "}"

    img_line = f"![{alt}]({url})"
    if attr_str:
        img_line += attr_str

    return [img_line]


def _transform_table(frame: DirectiveFrame) -> list[str]:
    """Transform table directive, keeping content and adding caption."""
    caption = frame.argument.strip()
    name = frame.options.get("name", "")

    lines = list(frame.body_lines)

    # Add caption line after table content
    if name:
        lines.append(f": {caption} {{#{name}}}")
    elif caption:
        lines.append(f": {caption}")

    return lines


def _transform_mermaid(frame: DirectiveFrame) -> list[str]:
    """Pass mermaid directive through unchanged."""
    lines = ["```{mermaid}"]
    lines.extend(frame.body_lines)
    lines.append("```")
    return lines


def _transform_unknown(frame: DirectiveFrame) -> list[str]:
    """Pass unknown directive through with a warning comment."""
    lines = [f"<!-- WARNING: unknown MyST directive '{frame.name}' -->"]
    # Reconstruct original-ish fence
    fence = frame.fence_char * frame.fence_count
    lines.append(
        f"{fence}{{{frame.name}}}" + (f" {frame.argument}" if frame.argument else "")
    )
    for key, val in frame.options.items():
        lines.append(f":{key}: {val}")
    if frame.body_lines:
        lines.append("")
        lines.extend(frame.body_lines)
    lines.append(fence)
    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def convert_myst_to_quarto(text: str) -> str:
    """Convert MyST markdown text to Quarto markdown.

    Args:
        text: Full MyST markdown document text.

    Returns:
        Quarto markdown text.
    """
    scanner = Scanner(
        transform_fn=transform_directive,
        inline_fn=transform_inline,
    )
    return scanner.scan(text)
