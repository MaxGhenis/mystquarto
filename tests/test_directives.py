"""Tests for the scanner and block directive transforms."""

from mystquarto.transforms.myst_to_quarto import (
    convert_myst_to_quarto,
)


# ---------------------------------------------------------------------------
# Scanner: fence detection
# ---------------------------------------------------------------------------


class TestScannerFenceDetection:
    """Test that the scanner correctly detects opening and closing fences."""

    def test_backtick_fence_opens_directive(self):
        text = "```{code-cell} python\nprint('hi')\n```"
        result = convert_myst_to_quarto(text)
        # Should be transformed (not left as raw fence)
        assert "{code-cell}" not in result

    def test_colon_fence_opens_directive(self):
        text = ":::{note}\nSome note text.\n:::"
        result = convert_myst_to_quarto(text)
        assert "{.callout-note}" in result

    def test_four_backtick_fence(self):
        text = "````{note}\nSome note text.\n````"
        result = convert_myst_to_quarto(text)
        assert "{.callout-note}" in result

    def test_four_colon_fence(self):
        text = "::::{note}\nSome note text.\n::::"
        result = convert_myst_to_quarto(text)
        assert "{.callout-note}" in result

    def test_close_fence_must_match_char_type(self):
        """Backtick open must be closed by backticks, not colons."""
        text = "```{note}\nSome text.\n:::\nMore text.\n```"
        result = convert_myst_to_quarto(text)
        # The ::: in the middle should NOT close the directive
        assert "{.callout-note}" in result
        assert "More text." in result

    def test_close_fence_must_match_count(self):
        """Close fence must have >= the same number of fence chars."""
        text = "````{note}\nSome text.\n```\nMore text.\n````"
        result = convert_myst_to_quarto(text)
        # ``` should NOT close a ```` directive
        assert "{.callout-note}" in result
        assert "More text." in result

    def test_indented_directive(self):
        """Directives can be indented."""
        text = "  ```{note}\n  Some text.\n  ```"
        result = convert_myst_to_quarto(text)
        assert "{.callout-note}" in result


# ---------------------------------------------------------------------------
# Scanner: options parsing
# ---------------------------------------------------------------------------


class TestScannerOptionsParsing:
    """Test that the scanner correctly parses :key: value options."""

    def test_single_option(self):
        text = "```{figure} img.png\n:width: 80%\n\nCaption text.\n```"
        result = convert_myst_to_quarto(text)
        assert 'width="80%"' in result

    def test_multiple_options(self):
        text = "```{figure} img.png\n:name: fig-test\n:width: 50%\n\nCaption.\n```"
        result = convert_myst_to_quarto(text)
        assert "#fig-test" in result
        assert 'width="50%"' in result

    def test_option_with_list_value(self):
        text = "```{code-cell} python\n:tags: [remove-input]\n\nprint('hi')\n```"
        result = convert_myst_to_quarto(text)
        assert "#| echo: false" in result

    def test_no_options(self):
        text = "```{note}\nJust body text.\n```"
        result = convert_myst_to_quarto(text)
        assert "{.callout-note}" in result
        assert "Just body text." in result


# ---------------------------------------------------------------------------
# Scanner: nested directives
# ---------------------------------------------------------------------------


class TestScannerNestedDirectives:
    """Test that nested directives are handled correctly."""

    def test_tab_set_with_tab_items(self):
        text = (
            "::::{tab-set}\n"
            ":::{tab-item} Tab A\n"
            "Content A\n"
            ":::\n"
            ":::{tab-item} Tab B\n"
            "Content B\n"
            ":::\n"
            "::::\n"
        )
        result = convert_myst_to_quarto(text)
        assert "{.panel-tabset}" in result
        assert "## Tab A" in result
        assert "## Tab B" in result
        assert "Content A" in result
        assert "Content B" in result

    def test_nested_different_fence_chars(self):
        """Outer uses colons, inner uses backticks."""
        text = (
            "::::{tab-set}\n"
            ":::{tab-item} Code\n"
            "```{code-cell} python\n"
            "x = 1\n"
            "```\n"
            ":::\n"
            "::::\n"
        )
        result = convert_myst_to_quarto(text)
        assert "{.panel-tabset}" in result
        assert "## Code" in result
        assert "x = 1" in result


# ---------------------------------------------------------------------------
# Block directive transforms: code-cell
# ---------------------------------------------------------------------------


class TestCodeCellTransform:
    """Test code-cell directive transformation."""

    def test_basic_code_cell(self):
        text = "```{code-cell} python\nprint('hello')\n```"
        result = convert_myst_to_quarto(text)
        assert "```{python}" in result
        assert "print('hello')" in result
        assert "```" in result

    def test_code_cell_remove_cell(self):
        text = "```{code-cell} python\n:tags: [remove-cell]\n\nx = 1\n```"
        result = convert_myst_to_quarto(text)
        assert "#| include: false" in result

    def test_code_cell_remove_input(self):
        text = "```{code-cell} python\n:tags: [remove-input]\n\nx = 1\n```"
        result = convert_myst_to_quarto(text)
        assert "#| echo: false" in result

    def test_code_cell_remove_output(self):
        text = "```{code-cell} python\n:tags: [remove-output]\n\nx = 1\n```"
        result = convert_myst_to_quarto(text)
        assert "#| output: false" in result

    def test_code_cell_hide_input(self):
        text = "```{code-cell} python\n:tags: [hide-input]\n\nx = 1\n```"
        result = convert_myst_to_quarto(text)
        assert "#| code-fold: true" in result

    def test_code_cell_with_caption(self):
        text = "```{code-cell} python\n:caption: My figure\n\nimport matplotlib\n```"
        result = convert_myst_to_quarto(text)
        assert '#| fig-cap: "My figure"' in result

    def test_code_cell_ipython3(self):
        """ipython3 should map to python."""
        text = "```{code-cell} ipython3\nprint('hi')\n```"
        result = convert_myst_to_quarto(text)
        assert "```{python}" in result

    def test_code_cell_r_language(self):
        text = "```{code-cell} r\nprint('hi')\n```"
        result = convert_myst_to_quarto(text)
        assert "```{r}" in result


# ---------------------------------------------------------------------------
# Block directive transforms: figure
# ---------------------------------------------------------------------------


class TestFigureTransform:
    """Test figure directive transformation."""

    def test_basic_figure(self):
        text = "```{figure} images/plot.png\n\nMy caption text.\n```"
        result = convert_myst_to_quarto(text)
        assert "![My caption text.](images/plot.png)" in result

    def test_figure_with_name(self):
        text = "```{figure} img.png\n:name: fig-myplot\n\nCaption.\n```"
        result = convert_myst_to_quarto(text)
        assert "#fig-myplot" in result
        assert "![Caption.](img.png)" in result

    def test_figure_with_width(self):
        text = "```{figure} img.png\n:width: 80%\n\nCaption.\n```"
        result = convert_myst_to_quarto(text)
        assert 'width="80%"' in result

    def test_figure_with_all_options(self):
        text = "```{figure} img.png\n:name: fig-x\n:width: 50%\n\nA caption.\n```"
        result = convert_myst_to_quarto(text)
        assert "![A caption.](img.png)" in result
        assert "#fig-x" in result
        assert 'width="50%"' in result


# ---------------------------------------------------------------------------
# Block directive transforms: math
# ---------------------------------------------------------------------------


class TestMathTransform:
    """Test math directive transformation."""

    def test_basic_math(self):
        text = "```{math}\nE = mc^2\n```"
        result = convert_myst_to_quarto(text)
        assert "$$" in result
        assert "E = mc^2" in result

    def test_math_with_label(self):
        text = "```{math}\n:label: eq-energy\n\nE = mc^2\n```"
        result = convert_myst_to_quarto(text)
        assert "$$" in result
        assert "{#eq-energy}" in result
        assert "E = mc^2" in result


# ---------------------------------------------------------------------------
# Block directive transforms: admonitions
# ---------------------------------------------------------------------------


class TestAdmonitionTransforms:
    """Test admonition directive transformations."""

    def test_note(self):
        text = "```{note}\nThis is a note.\n```"
        result = convert_myst_to_quarto(text)
        assert "::: {.callout-note}" in result
        assert "This is a note." in result
        assert ":::" in result

    def test_warning(self):
        text = "```{warning}\nBe careful!\n```"
        result = convert_myst_to_quarto(text)
        assert "::: {.callout-warning}" in result

    def test_tip(self):
        text = "```{tip}\nHelpful tip.\n```"
        result = convert_myst_to_quarto(text)
        assert "::: {.callout-tip}" in result

    def test_important(self):
        text = "```{important}\nImportant info.\n```"
        result = convert_myst_to_quarto(text)
        assert "::: {.callout-important}" in result

    def test_caution(self):
        text = "```{caution}\nProceed with caution.\n```"
        result = convert_myst_to_quarto(text)
        assert "::: {.callout-caution}" in result

    def test_admonition_with_title(self):
        text = "```{admonition} Custom Title\nBody text here.\n```"
        result = convert_myst_to_quarto(text)
        assert '::: {.callout-note title="Custom Title"}' in result
        assert "Body text here." in result

    def test_admonition_colon_fence(self):
        text = ":::{warning}\nDanger ahead.\n:::"
        result = convert_myst_to_quarto(text)
        assert "::: {.callout-warning}" in result
        assert "Danger ahead." in result


# ---------------------------------------------------------------------------
# Block directive transforms: bibliography
# ---------------------------------------------------------------------------


class TestBibliographyTransform:
    """Test bibliography directive removal."""

    def test_bibliography_removed(self):
        text = "# References\n\n```{bibliography}\n:style: unsrt\n```\n\nAfter."
        result = convert_myst_to_quarto(text)
        assert "{bibliography}" not in result
        assert "After." in result

    def test_bibliography_with_options_removed(self):
        text = "```{bibliography}\n:filter: docname in docnames\n```"
        result = convert_myst_to_quarto(text)
        assert "{bibliography}" not in result
        assert ":filter:" not in result


# ---------------------------------------------------------------------------
# Block directive transforms: abstract
# ---------------------------------------------------------------------------


class TestAbstractTransform:
    """Test abstract directive handling."""

    def test_abstract_removed_from_body(self):
        text = "```{abstract}\nThis is the abstract content.\n```\n\n# Introduction"
        result = convert_myst_to_quarto(text)
        # The abstract body should be removed from the main body
        # (it would go into frontmatter in a full pipeline)
        assert "{abstract}" not in result
        assert "# Introduction" in result


# ---------------------------------------------------------------------------
# Block directive transforms: tab-set / tab-item
# ---------------------------------------------------------------------------


class TestTabTransforms:
    """Test tab-set and tab-item directive transforms."""

    def test_tab_set_becomes_panel_tabset(self):
        text = (
            "::::{tab-set}\n"
            ":::{tab-item} First\n"
            "First content.\n"
            ":::\n"
            ":::{tab-item} Second\n"
            "Second content.\n"
            ":::\n"
            "::::\n"
        )
        result = convert_myst_to_quarto(text)
        assert "::: {.panel-tabset}" in result
        assert "## First" in result
        assert "First content." in result
        assert "## Second" in result
        assert "Second content." in result


# ---------------------------------------------------------------------------
# Block directive transforms: margin
# ---------------------------------------------------------------------------


class TestMarginTransform:
    """Test margin directive transformation."""

    def test_margin_backtick(self):
        text = "```{margin}\nMargin note text.\n```"
        result = convert_myst_to_quarto(text)
        assert "::: {.column-margin}" in result
        assert "Margin note text." in result

    def test_margin_colon(self):
        text = ":::{margin}\nMargin note text.\n:::"
        result = convert_myst_to_quarto(text)
        assert "::: {.column-margin}" in result


# ---------------------------------------------------------------------------
# Block directive transforms: image
# ---------------------------------------------------------------------------


class TestImageTransform:
    """Test image directive transformation."""

    def test_basic_image(self):
        text = "```{image} https://example.com/img.png\n```"
        result = convert_myst_to_quarto(text)
        assert "![](https://example.com/img.png)" in result

    def test_image_with_alt(self):
        text = "```{image} img.png\n:alt: My alt text\n```"
        result = convert_myst_to_quarto(text)
        assert "![My alt text](img.png)" in result

    def test_image_with_width(self):
        text = "```{image} img.png\n:width: 60%\n```"
        result = convert_myst_to_quarto(text)
        assert 'width="60%"' in result

    def test_image_with_alt_and_width(self):
        text = "```{image} img.png\n:alt: Alt\n:width: 40%\n```"
        result = convert_myst_to_quarto(text)
        assert "![Alt](img.png)" in result
        assert 'width="40%"' in result


# ---------------------------------------------------------------------------
# Block directive transforms: table
# ---------------------------------------------------------------------------


class TestTableTransform:
    """Test table directive transformation."""

    def test_table_with_name(self):
        text = (
            "```{table} My Table Caption\n"
            ":name: tbl-data\n"
            "\n"
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n"
            "```"
        )
        result = convert_myst_to_quarto(text)
        assert "| A | B |" in result
        assert ": My Table Caption {#tbl-data}" in result

    def test_table_without_name(self):
        text = (
            "```{table} Caption Only\n"
            "\n"
            "| X |\n"
            "|---|\n"
            "| 1 |\n"
            "```"
        )
        result = convert_myst_to_quarto(text)
        assert "| X |" in result
        assert ": Caption Only" in result


# ---------------------------------------------------------------------------
# Block directive transforms: tableofcontents
# ---------------------------------------------------------------------------


class TestTocTransform:
    """Test tableofcontents directive removal."""

    def test_toc_removed(self):
        text = "# Title\n\n```{tableofcontents}\n```\n\n# Chapter 1"
        result = convert_myst_to_quarto(text)
        assert "{tableofcontents}" not in result
        assert "# Chapter 1" in result


# ---------------------------------------------------------------------------
# Block directive transforms: mermaid
# ---------------------------------------------------------------------------


class TestMermaidTransform:
    """Test mermaid directive passthrough."""

    def test_mermaid_passthrough(self):
        text = "```{mermaid}\ngraph LR\n  A --> B\n```"
        result = convert_myst_to_quarto(text)
        assert "```{mermaid}" in result
        assert "graph LR" in result
        assert "A --> B" in result


# ---------------------------------------------------------------------------
# Block directive transforms: unknown directives
# ---------------------------------------------------------------------------


class TestUnknownDirectiveTransform:
    """Test unknown directive passthrough with warning."""

    def test_unknown_directive_passthrough(self):
        text = "```{unknown-thing}\nSome content.\n```"
        result = convert_myst_to_quarto(text)
        # Should include a warning comment
        assert "<!-- WARNING" in result or "<!-- mystquarto" in result.lower() or "unknown" in result.lower()
        assert "Some content." in result


# ---------------------------------------------------------------------------
# Full round-trip with fixture files
# ---------------------------------------------------------------------------


class TestFixtureRoundTrip:
    """Test conversion using fixture files."""

    def test_simple_fixture(self):
        import pathlib

        fixtures = pathlib.Path(__file__).parent / "fixtures"
        myst_text = (fixtures / "simple_myst.md").read_text()
        expected = (fixtures / "simple_quarto.md").read_text()
        result = convert_myst_to_quarto(myst_text)
        # Normalize trailing whitespace for comparison
        result_lines = [line.rstrip() for line in result.splitlines()]
        expected_lines = [line.rstrip() for line in expected.splitlines()]
        assert result_lines == expected_lines
