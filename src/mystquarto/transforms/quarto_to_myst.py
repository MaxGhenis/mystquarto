"""Quarto -> MyST transform rules: block constructs and inline syntax."""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Inline transform patterns (Quarto -> MyST)
# ---------------------------------------------------------------------------

# `{python} expr` -> {eval}`expr`
_INLINE_CODE_RE = re.compile(r"`\{python\}\s+([^`]+)`")

# [@key1; @key2; ...] -> {cite}`key1,key2,...`  (multi-citation, must come first)
_MULTI_CITE_RE = re.compile(r"\[(@[\w-]+(?:;\s*@[\w-]+)+)\]")

# [@key] -> {cite}`key`  (single bracketed citation)
_SINGLE_CITE_RE = re.compile(r"\[@([\w-]+)\]")

# @fig-id -> {numref}`fig-id`  (figure cross-ref, must come before bare @)
_FIG_REF_RE = re.compile(r"(?<!\w)@(fig-[\w-]+)(?!\w)")

# @eq-label -> {eq}`label`  (equation cross-ref, must come before bare @)
_EQ_REF_RE = re.compile(r"(?<!\w)@(eq-[\w-]+)(?!\w)")

# @tbl-id -> {ref}`tbl-id`  (table cross-ref, must come before bare @)
_TBL_REF_RE = re.compile(r"(?<!\w)@(tbl-[\w-]+)(?!\w)")

# @sec-id -> {ref}`sec-id`  (section cross-ref, must come before bare @)
_SEC_REF_RE = re.compile(r"(?<!\w)@(sec-[\w-]+)(?!\w)")

# @key (bare citation, not email, not @fig/@eq/@tbl/@sec) -> {cite:t}`key`
# Must NOT be preceded by a word character (to exclude emails).
# Must NOT match @fig-*, @eq-*, @tbl-*, @sec-* (those are handled above).
_BARE_CITE_RE = re.compile(r"(?<!\w)@((?!fig-|eq-|tbl-|sec-)[\w][\w-]*)(?!\w)")

# [text](path.qmd) where link text matches the path stem -> {doc}`path`
_DOC_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^\)]+\.qmd)\)")

# Quarto cell option pattern: #| key: value
_CELL_OPTION_RE = re.compile(r"^#\|\s+([\w-]+):\s+(.+)$")

# Quarto callout pattern: ::: {.callout-TYPE} or ::: {.callout-TYPE title="..."}
_CALLOUT_RE = re.compile(
    r"^(:{3,})\s*\{\.callout-(note|warning|tip|important|caution)"
    r'(?:\s+title="([^"]*)")?\s*\}'
)

# Quarto panel-tabset pattern
_TABSET_RE = re.compile(r"^(:{3,})\s*\{\.panel-tabset\}")

# Quarto column-margin pattern
_MARGIN_RE = re.compile(r"^(:{3,})\s*\{\.column-margin\}")

# Quarto executable code block: ```{python}, ```{r}, ```{julia}, etc.
_EXEC_CODE_RE = re.compile(r"^(`{3,})\{(\w+)\}\s*$")

# Closing fence for colon blocks
_COLON_CLOSE_RE = re.compile(r"^(:{3,})\s*$")

# Closing fence for backtick blocks
_BACKTICK_CLOSE_RE = re.compile(r"^(`{3,})\s*$")

# Image/figure with attributes: ![alt](url){attrs}
_IMG_ATTRS_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\{([^}]+)\}\s*$")

# Math block closing with label: $$ {#eq-id}
_MATH_CLOSE_LABEL_RE = re.compile(r"^\$\$\s*\{#([\w-]+)\}\s*$")

# Math block opening: $$
_MATH_OPEN_RE = re.compile(r"^\$\$\s*$")

# Table caption line: : Caption {#tbl-id}
_TABLE_CAPTION_RE = re.compile(r"^:\s+(.+?)\s*\{#(tbl-[\w-]+)\}\s*$")

# Table row pattern (to detect table blocks for caption association)
_TABLE_ROW_RE = re.compile(r"^\|.*\|\s*$")

# Quarto cell option -> MyST tag mapping (reverse of myst_to_quarto._TAG_MAP)
_OPTION_TO_TAG = {
    "include": {"false": "remove-cell"},
    "echo": {"false": "remove-input"},
    "output": {"false": "remove-output"},
    "code-fold": {"true": "hide-input"},
}

# Admonition types that map directly
_ADMONITION_TYPES = {"note", "warning", "tip", "important", "caution"}

# Known executable code languages
_EXEC_LANGUAGES = {"python", "r", "julia", "bash", "sh", "sql", "ojs", "dot", "mermaid"}


# ---------------------------------------------------------------------------
# Inline transforms
# ---------------------------------------------------------------------------


def _replace_inline_code(m: re.Match) -> str:
    return f"{{eval}}`{m.group(1)}`"


def _replace_multi_cite(m: re.Match) -> str:
    # Extract keys from "@key1; @key2; @key3"
    raw = m.group(1)
    keys = [k.strip().lstrip("@") for k in raw.split(";")]
    return "{cite}`" + ",".join(keys) + "`"


def _replace_single_cite(m: re.Match) -> str:
    return "{cite}`" + m.group(1) + "`"


def _replace_fig_ref(m: re.Match) -> str:
    return "{numref}`" + m.group(1) + "`"


def _replace_eq_ref(m: re.Match) -> str:
    return "{eq}`" + m.group(1) + "`"


def _replace_tbl_ref(m: re.Match) -> str:
    return "{ref}`" + m.group(1) + "`"


def _replace_sec_ref(m: re.Match) -> str:
    return "{ref}`" + m.group(1) + "`"


def _replace_bare_cite(m: re.Match) -> str:
    return "{cite:t}`" + m.group(1) + "`"


def _replace_doc_link(m: re.Match) -> str:
    text = m.group(1)
    url = m.group(2)
    # Remove .qmd extension to get the path
    path = url[:-4]  # strip .qmd
    # Only convert if the link text matches the path (or its basename)
    if text == path or text == path.split("/")[-1]:
        return "{doc}`" + path + "`"
    # If link text differs from path, keep as-is
    return m.group(0)


def transform_quarto_inline(line: str) -> str:
    """Transform Quarto inline syntax to MyST roles on a single line.

    Quarto uses @key for citations, `{python} expr` for inline code,
    and [text](file.qmd) for cross-document links.
    """
    if not line:
        return line

    # Order matters: more specific patterns must come before less specific ones.

    # 1. Inline executable code: `{python} expr` -> {eval}`expr`
    result = _INLINE_CODE_RE.sub(_replace_inline_code, line)

    # 2. Multi-citation: [@a; @b; @c] -> {cite}`a,b,c`
    result = _MULTI_CITE_RE.sub(_replace_multi_cite, result)

    # 3. Single bracketed citation: [@key] -> {cite}`key`
    result = _SINGLE_CITE_RE.sub(_replace_single_cite, result)

    # 4. Cross-refs (before bare citation, since @fig-* etc. start with @)
    result = _FIG_REF_RE.sub(_replace_fig_ref, result)
    result = _EQ_REF_RE.sub(_replace_eq_ref, result)
    result = _TBL_REF_RE.sub(_replace_tbl_ref, result)
    result = _SEC_REF_RE.sub(_replace_sec_ref, result)

    # 5. Bare citation: @key -> {cite:t}`key`
    result = _BARE_CITE_RE.sub(_replace_bare_cite, result)

    # 6. Doc links: [text](file.qmd) -> {doc}`path`
    result = _DOC_LINK_RE.sub(_replace_doc_link, result)

    return result


# ---------------------------------------------------------------------------
# Block transforms
# ---------------------------------------------------------------------------


def _parse_cell_options(
    body_lines: list[str],
) -> tuple[dict[str, str], list[str]]:
    """Parse #| cell options from the beginning of code body lines.

    Returns:
        Tuple of (options_dict, remaining_body_lines).
    """
    options: dict[str, str] = {}
    i = 0
    for i, line in enumerate(body_lines):
        m = _CELL_OPTION_RE.match(line.strip())
        if m:
            options[m.group(1)] = m.group(2).strip()
        else:
            break
    else:
        # All lines were options
        i = len(body_lines)

    remaining = body_lines[i:]
    # Strip leading blank line after options
    if remaining and remaining[0].strip() == "":
        remaining = remaining[1:]

    return options, remaining


def _build_code_cell(
    lang: str, options: dict[str, str], body_lines: list[str]
) -> list[str]:
    """Build a MyST code-cell directive from parsed Quarto code block."""
    lines: list[str] = [f"```{{code-cell}} {lang}"]

    # Convert cell options to MyST options
    tags: list[str] = []
    caption = ""

    for key, value in options.items():
        if key in _OPTION_TO_TAG and value in _OPTION_TO_TAG[key]:
            tags.append(_OPTION_TO_TAG[key][value])
        elif key == "fig-cap":
            # Remove surrounding quotes if present
            caption = value.strip('"').strip("'")

    if tags:
        tags_str = "[" + ", ".join(tags) + "]"
        lines.append(f":tags: {tags_str}")

    if caption:
        lines.append(f":caption: {caption}")

    # Add blank line between options and body if we had options
    if len(lines) > 1:
        lines.append("")

    lines.extend(body_lines)
    lines.append("```")
    return lines


def _build_admonition(adm_type: str, title: str, body_lines: list[str]) -> list[str]:
    """Build a MyST admonition directive."""
    if title:
        lines = [f"```{{admonition}} {title}"]
    else:
        lines = [f"```{{{adm_type}}}"]
    lines.extend(body_lines)
    lines.append("```")
    return lines


def _build_margin(body_lines: list[str]) -> list[str]:
    """Build a MyST margin directive."""
    lines = ["```{margin}"]
    lines.extend(body_lines)
    lines.append("```")
    return lines


def _build_tab_set(body_lines: list[str]) -> list[str]:
    """Build a MyST tab-set from Quarto panel-tabset body.

    Inside a panel-tabset, ## headings become tab-item directives.
    """
    result: list[str] = ["::::{tab-set}"]

    # Split body into tab items based on ## headings
    current_label = None
    current_body: list[str] = []

    for line in body_lines:
        heading_m = re.match(r"^##\s+(.+)$", line)
        if heading_m:
            # Flush previous tab item
            if current_label is not None:
                # Remove trailing blank lines from previous tab body
                while current_body and current_body[-1].strip() == "":
                    current_body.pop()
                result.append(f":::{{tab-item}} {current_label}")
                result.extend(current_body)
                result.append(":::")
            current_label = heading_m.group(1).strip()
            current_body = []
        else:
            current_body.append(line)

    # Flush last tab item
    if current_label is not None:
        while current_body and current_body[-1].strip() == "":
            current_body.pop()
        result.append(f":::{{tab-item}} {current_label}")
        result.extend(current_body)
        result.append(":::")

    result.append("::::")
    return result


def _parse_image_attrs(attr_str: str) -> dict[str, str]:
    """Parse image attribute string like '#fig-id width="80%"'."""
    attrs: dict[str, str] = {}

    # Find #id
    id_m = re.search(r"#([\w-]+)", attr_str)
    if id_m:
        attrs["id"] = id_m.group(1)

    # Find width="value" or width=value
    width_m = re.search(r'width="?([^"\s}]+)"?', attr_str)
    if width_m:
        attrs["width"] = width_m.group(1)

    return attrs


def _build_figure_directive(alt: str, url: str, attrs: dict[str, str]) -> list[str]:
    """Build a MyST figure directive from Quarto image with #id."""
    lines = [f"```{{figure}} {url}"]
    if "id" in attrs:
        lines.append(f":name: {attrs['id']}")
    if "width" in attrs:
        lines.append(f":width: {attrs['width']}")
    lines.append("")
    if alt:
        lines.append(alt)
    lines.append("```")
    return lines


def _build_image_directive(alt: str, url: str, attrs: dict[str, str]) -> list[str]:
    """Build a MyST image directive from Quarto image with width but no #id."""
    lines = [f"```{{image}} {url}"]
    if alt:
        lines.append(f":alt: {alt}")
    if "width" in attrs:
        lines.append(f":width: {attrs['width']}")
    lines.append("```")
    return lines


def _build_math_directive(label: str, body_lines: list[str]) -> list[str]:
    """Build a MyST math directive from labeled $$ block."""
    lines = ["```{math}"]
    if label:
        lines.append(f":label: {label}")
    lines.append("")
    lines.extend(body_lines)
    lines.append("```")
    return lines


def _build_table_directive(
    caption: str, name: str, table_lines: list[str]
) -> list[str]:
    """Build a MyST table directive."""
    lines = [f"```{{table}} {caption}"]
    if name:
        lines.append(f":name: {name}")
    lines.append("")
    lines.extend(table_lines)
    lines.append("```")
    return lines


# ---------------------------------------------------------------------------
# Main block processing
# ---------------------------------------------------------------------------


def transform_quarto_block(lines: list[str]) -> list[str]:
    """Process a block of Quarto lines, detecting callouts, tabsets, etc.

    Args:
        lines: List of input lines (without trailing newlines).

    Returns:
        List of transformed output lines.
    """
    text = "\n".join(lines)
    result = convert_quarto_to_myst(text)
    return result.split("\n")


def convert_quarto_to_myst(text: str) -> str:
    """Convert Quarto markdown text to MyST markdown.

    This processes the text line by line, detecting:
    - Executable code fences (```{python}, etc.)
    - Callout blocks (::: {.callout-*})
    - Panel tabsets (::: {.panel-tabset})
    - Column margins (::: {.column-margin})
    - Images with attributes (![alt](url){attrs})
    - Math blocks with labels ($$ ... $$ {#eq-id})
    - Table captions with labels (: Caption {#tbl-id})
    - Inline Quarto syntax (citations, cross-refs, etc.)

    Args:
        text: Full Quarto markdown document text.

    Returns:
        MyST markdown text.
    """
    input_lines = text.split("\n")
    output_lines: list[str] = []

    i = 0
    # Track accumulated table lines for caption association
    table_lines_buffer: list[str] = []
    in_table = False

    while i < len(input_lines):
        line = input_lines[i]
        stripped = line.strip()

        # ----------------------------------------------------------
        # Check for executable code block: ```{python}, ```{r}, etc.
        # ----------------------------------------------------------
        exec_m = _EXEC_CODE_RE.match(stripped)
        if exec_m:
            fence_str = exec_m.group(1)
            lang = exec_m.group(2)
            fence_count = len(fence_str)

            if lang.lower() in _EXEC_LANGUAGES:
                # Collect body until closing fence
                body_lines: list[str] = []
                i += 1
                while i < len(input_lines):
                    close_m = _BACKTICK_CLOSE_RE.match(input_lines[i].strip())
                    if close_m and len(close_m.group(1)) >= fence_count:
                        break
                    body_lines.append(input_lines[i])
                    i += 1

                # Parse cell options from body
                options, remaining_body = _parse_cell_options(body_lines)
                cell_lines = _build_code_cell(lang, options, remaining_body)
                output_lines.extend(cell_lines)
                i += 1  # skip closing fence
                continue

        # ----------------------------------------------------------
        # Check for callout: ::: {.callout-*}
        # ----------------------------------------------------------
        callout_m = _CALLOUT_RE.match(stripped)
        if callout_m:
            fence_str = callout_m.group(1)
            adm_type = callout_m.group(2)
            title = callout_m.group(3) or ""
            fence_count = len(fence_str)

            # Collect body until closing :::
            body_lines = []
            i += 1
            while i < len(input_lines):
                close_m = _COLON_CLOSE_RE.match(input_lines[i].strip())
                if close_m and len(close_m.group(1)) >= fence_count:
                    break
                body_lines.append(input_lines[i])
                i += 1

            adm_lines = _build_admonition(adm_type, title, body_lines)
            output_lines.extend(adm_lines)
            i += 1  # skip closing fence
            continue

        # ----------------------------------------------------------
        # Check for panel-tabset: ::: {.panel-tabset}
        # ----------------------------------------------------------
        tabset_m = _TABSET_RE.match(stripped)
        if tabset_m:
            fence_str = tabset_m.group(1)
            fence_count = len(fence_str)

            # Collect body until closing :::
            body_lines = []
            i += 1
            while i < len(input_lines):
                close_m = _COLON_CLOSE_RE.match(input_lines[i].strip())
                if close_m and len(close_m.group(1)) >= fence_count:
                    break
                body_lines.append(input_lines[i])
                i += 1

            tab_lines = _build_tab_set(body_lines)
            output_lines.extend(tab_lines)
            i += 1  # skip closing fence
            continue

        # ----------------------------------------------------------
        # Check for column-margin: ::: {.column-margin}
        # ----------------------------------------------------------
        margin_m = _MARGIN_RE.match(stripped)
        if margin_m:
            fence_str = margin_m.group(1)
            fence_count = len(fence_str)

            # Collect body until closing :::
            body_lines = []
            i += 1
            while i < len(input_lines):
                close_m = _COLON_CLOSE_RE.match(input_lines[i].strip())
                if close_m and len(close_m.group(1)) >= fence_count:
                    break
                body_lines.append(input_lines[i])
                i += 1

            margin_lines = _build_margin(body_lines)
            output_lines.extend(margin_lines)
            i += 1  # skip closing fence
            continue

        # ----------------------------------------------------------
        # Check for image/figure with attributes: ![alt](url){attrs}
        # ----------------------------------------------------------
        img_m = _IMG_ATTRS_RE.match(stripped)
        if img_m:
            alt = img_m.group(1)
            url = img_m.group(2)
            attr_str = img_m.group(3)
            attrs = _parse_image_attrs(attr_str)

            if "id" in attrs and attrs["id"].startswith("fig-"):
                # This is a figure (has #fig-* id)
                fig_lines = _build_figure_directive(alt, url, attrs)
                output_lines.extend(fig_lines)
            elif attrs:
                # Image with attributes but no figure id
                img_lines = _build_image_directive(alt, url, attrs)
                output_lines.extend(img_lines)
            else:
                # No meaningful attributes, pass through
                output_lines.append(transform_quarto_inline(line))

            i += 1
            continue

        # ----------------------------------------------------------
        # Check for math block: $$
        # ----------------------------------------------------------
        if _MATH_OPEN_RE.match(stripped):
            # Collect lines until $$ or $$ {#eq-id}
            math_body: list[str] = []
            label = ""
            i += 1
            while i < len(input_lines):
                math_line = input_lines[i]
                label_m = _MATH_CLOSE_LABEL_RE.match(math_line.strip())
                if label_m:
                    label = label_m.group(1)
                    break
                if _MATH_OPEN_RE.match(math_line.strip()):
                    # Plain $$ close
                    break
                math_body.append(math_line)
                i += 1

            if label:
                # Build math directive with label
                math_lines = _build_math_directive(label, math_body)
                output_lines.extend(math_lines)
            else:
                # No label, pass through as-is
                output_lines.append("$$")
                output_lines.extend(math_body)
                output_lines.append("$$")

            i += 1
            continue

        # ----------------------------------------------------------
        # Check for table caption: : Caption {#tbl-id}
        # ----------------------------------------------------------
        table_caption_m = _TABLE_CAPTION_RE.match(stripped)
        if table_caption_m and in_table:
            caption = table_caption_m.group(1).strip()
            name = table_caption_m.group(2)

            # Wrap the buffered table lines in a table directive
            tbl_lines = _build_table_directive(caption, name, table_lines_buffer)

            # Replace the table lines in output with the directive
            # Remove the raw table lines we already added
            for _ in range(len(table_lines_buffer)):
                output_lines.pop()
            output_lines.extend(tbl_lines)

            table_lines_buffer = []
            in_table = False
            i += 1
            continue

        # ----------------------------------------------------------
        # Track table rows for caption association
        # ----------------------------------------------------------
        if _TABLE_ROW_RE.match(stripped):
            if not in_table:
                in_table = True
                table_lines_buffer = []
            table_lines_buffer.append(line)
            output_lines.append(line)
            i += 1
            continue
        else:
            if in_table and stripped != "":
                # Non-table, non-blank line -> end of table
                in_table = False
                table_lines_buffer = []

        # ----------------------------------------------------------
        # Regular line: apply inline transforms
        # ----------------------------------------------------------
        output_lines.append(transform_quarto_inline(line))
        i += 1

    return "\n".join(output_lines)
