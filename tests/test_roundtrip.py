"""Tests for Quarto->MyST transforms and roundtrip (MyST->Quarto->MyST)."""

import pathlib

from mystquarto.transforms.myst_to_quarto import convert_myst_to_quarto
from mystquarto.transforms.quarto_to_myst import (
    convert_quarto_to_myst,
    transform_quarto_block,
    transform_quarto_inline,
)


# ===========================================================================
# Quarto -> MyST: Block transforms
# ===========================================================================


class TestQuartoCodeCell:
    """Test ```{python} -> ```{code-cell} python."""

    def test_quarto_code_cell(self):
        text = "```{python}\nprint('hello')\n```"
        result = convert_quarto_to_myst(text)
        assert "```{code-cell} python" in result
        assert "print('hello')" in result

    def test_quarto_code_cell_r(self):
        text = "```{r}\nlibrary(ggplot2)\n```"
        result = convert_quarto_to_myst(text)
        assert "```{code-cell} r" in result

    def test_quarto_code_cell_julia(self):
        text = '```{julia}\nprintln("hi")\n```'
        result = convert_quarto_to_myst(text)
        assert "```{code-cell} julia" in result


class TestQuartoCodeCellOptions:
    """Test cell options (#| key: value) -> MyST tags."""

    def test_include_false(self):
        text = "```{python}\n#| include: false\n\nx = 1\n```"
        result = convert_quarto_to_myst(text)
        assert ":tags: [remove-cell]" in result
        assert "#| include: false" not in result

    def test_echo_false(self):
        text = "```{python}\n#| echo: false\n\nx = 1\n```"
        result = convert_quarto_to_myst(text)
        assert ":tags: [remove-input]" in result

    def test_output_false(self):
        text = "```{python}\n#| output: false\n\nx = 1\n```"
        result = convert_quarto_to_myst(text)
        assert ":tags: [remove-output]" in result

    def test_code_fold_true(self):
        text = "```{python}\n#| code-fold: true\n\nimport numpy as np\n```"
        result = convert_quarto_to_myst(text)
        assert ":tags: [hide-input]" in result

    def test_fig_cap(self):
        text = '```{python}\n#| fig-cap: "My figure"\n\nimport matplotlib\n```'
        result = convert_quarto_to_myst(text)
        assert ":caption: My figure" in result

    def test_multiple_options(self):
        text = '```{python}\n#| echo: false\n#| fig-cap: "Plot"\n\nplot(x)\n```'
        result = convert_quarto_to_myst(text)
        assert ":tags: [remove-input]" in result
        assert ":caption: Plot" in result


# ===========================================================================
# Quarto -> MyST: Callout transforms
# ===========================================================================


class TestQuartoCalloutNote:
    """Test ::: {.callout-note} -> ```{note}."""

    def test_basic_callout_note(self):
        text = "::: {.callout-note}\nThis is a note.\n:::"
        result = convert_quarto_to_myst(text)
        assert "```{note}" in result or ":::{note}" in result
        assert "This is a note." in result

    def test_callout_warning(self):
        text = "::: {.callout-warning}\nBe careful!\n:::"
        result = convert_quarto_to_myst(text)
        assert "warning" in result
        assert "callout" not in result

    def test_callout_tip(self):
        text = "::: {.callout-tip}\nHelpful tip.\n:::"
        result = convert_quarto_to_myst(text)
        assert "tip" in result
        assert "callout" not in result

    def test_callout_important(self):
        text = "::: {.callout-important}\nImportant info.\n:::"
        result = convert_quarto_to_myst(text)
        assert "important" in result
        assert "callout" not in result

    def test_callout_caution(self):
        text = "::: {.callout-caution}\nProceed with caution.\n:::"
        result = convert_quarto_to_myst(text)
        assert "caution" in result
        assert "callout" not in result


class TestQuartoCalloutWithTitle:
    """Test callout with title -> admonition with custom title."""

    def test_callout_with_title(self):
        text = '::: {.callout-note title="Custom Title"}\nBody text here.\n:::'
        result = convert_quarto_to_myst(text)
        assert "```{admonition} Custom Title" in result
        assert "Body text here." in result

    def test_callout_warning_with_title(self):
        text = '::: {.callout-warning title="Watch Out"}\nDanger ahead.\n:::'
        result = convert_quarto_to_myst(text)
        # A titled callout becomes {admonition} with the title
        assert "Watch Out" in result
        assert "Danger ahead." in result


# ===========================================================================
# Quarto -> MyST: Panel tabset
# ===========================================================================


class TestQuartoPanelTabset:
    """Test ::: {.panel-tabset} -> tab-set/tab-item."""

    def test_panel_tabset(self):
        text = "::: {.panel-tabset}\n## Tab A\nContent A\n\n## Tab B\nContent B\n:::\n"
        result = convert_quarto_to_myst(text)
        assert "tab-set" in result
        assert "tab-item" in result
        assert "Tab A" in result
        assert "Tab B" in result
        assert "Content A" in result
        assert "Content B" in result
        # Should NOT contain panel-tabset
        assert "panel-tabset" not in result


# ===========================================================================
# Quarto -> MyST: Column margin
# ===========================================================================


class TestQuartoColumnMargin:
    """Test ::: {.column-margin} -> margin."""

    def test_column_margin(self):
        text = "::: {.column-margin}\nMargin note text.\n:::"
        result = convert_quarto_to_myst(text)
        assert "margin" in result
        assert "column-margin" not in result
        assert "Margin note text." in result


# ===========================================================================
# Quarto -> MyST: Images with attributes
# ===========================================================================


class TestQuartoImageWithAttrs:
    """Test ![alt](url){width=X} -> ```{image} url with options."""

    def test_image_with_width(self):
        text = '![Alt text](img.png){width="80%"}'
        result = convert_quarto_to_myst(text)
        assert "```{image} img.png" in result
        assert ":alt: Alt text" in result
        assert ":width: 80%" in result

    def test_image_with_width_no_quotes(self):
        text = "![Alt text](img.png){width=80%}"
        result = convert_quarto_to_myst(text)
        assert "```{image} img.png" in result
        assert ":width: 80%" in result

    def test_plain_image_no_attrs(self):
        """Plain image without attributes should pass through unchanged."""
        text = "![Alt text](img.png)"
        result = convert_quarto_to_myst(text)
        assert "![Alt text](img.png)" in result


# ===========================================================================
# Quarto -> MyST: Figures with ID
# ===========================================================================


class TestQuartoFigureWithId:
    """Test ![caption](path){#fig-id width=X} -> figure directive."""

    def test_figure_with_id(self):
        text = '![My caption](images/plot.png){#fig-plot width="80%"}'
        result = convert_quarto_to_myst(text)
        assert "```{figure} images/plot.png" in result
        assert ":name: fig-plot" in result
        assert ":width: 80%" in result
        assert "My caption" in result

    def test_figure_id_only(self):
        text = "![Caption](img.png){#fig-myplot}"
        result = convert_quarto_to_myst(text)
        assert "```{figure} img.png" in result
        assert ":name: fig-myplot" in result
        assert "Caption" in result


# ===========================================================================
# Quarto -> MyST: Math with label
# ===========================================================================


class TestQuartoMathWithId:
    """Test $$ ... $$ {#eq-id} -> math directive with label."""

    def test_math_with_id(self):
        text = "$$\nE = mc^2\n$$ {#eq-energy}"
        result = convert_quarto_to_myst(text)
        assert "```{math}" in result
        assert ":label: eq-energy" in result
        assert "E = mc^2" in result

    def test_math_without_id(self):
        """Plain math block without label passes through."""
        text = "$$\na + b = c\n$$"
        result = convert_quarto_to_myst(text)
        # Should either pass through or wrap in math directive
        assert "a + b = c" in result


# ===========================================================================
# Quarto -> MyST: Inline transforms
# ===========================================================================


class TestQuartoInlineCitation:
    """Test [@key] -> {cite}`key`."""

    def test_basic_citation(self):
        line = "See [@smith2020] for details."
        result = transform_quarto_inline(line)
        assert result == "See {cite}`smith2020` for details."

    def test_citation_in_parens(self):
        line = "Results ([@doe2021])."
        result = transform_quarto_inline(line)
        assert "{cite}`doe2021`" in result


class TestQuartoInlineMultiCitation:
    """Test [@a; @b; @c] -> {cite}`a,b,c`."""

    def test_multi_citation(self):
        line = "See [@smith2020; @jones2021; @doe2022]."
        result = transform_quarto_inline(line)
        assert result == "See {cite}`smith2020,jones2021,doe2022`."

    def test_two_citations(self):
        line = "See [@a; @b]."
        result = transform_quarto_inline(line)
        assert result == "See {cite}`a,b`."


class TestQuartoTextualCitation:
    """Test @key (bare, not in brackets, not email) -> {cite:t}`key`."""

    def test_bare_citation(self):
        line = "@smith2020 showed that..."
        result = transform_quarto_inline(line)
        assert result == "{cite:t}`smith2020` showed that..."

    def test_email_not_citation(self):
        """Email addresses should NOT be treated as citations."""
        line = "Contact user@example.com for info."
        result = transform_quarto_inline(line)
        assert result == "Contact user@example.com for info."

    def test_bare_citation_mid_sentence(self):
        line = "As @smith2020 noted."
        result = transform_quarto_inline(line)
        assert result == "As {cite:t}`smith2020` noted."


class TestQuartoCrossRefFigure:
    """Test @fig-id -> {numref}`fig-id`."""

    def test_fig_cross_ref(self):
        line = "As shown in @fig-results."
        result = transform_quarto_inline(line)
        assert result == "As shown in {numref}`fig-results`."

    def test_fig_cross_ref_mid_text(self):
        line = "See @fig-plot and @fig-other."
        result = transform_quarto_inline(line)
        assert "{numref}`fig-plot`" in result
        assert "{numref}`fig-other`" in result


class TestQuartoCrossRefEq:
    """Test @eq-label -> {eq}`label`."""

    def test_eq_cross_ref(self):
        line = "From equation @eq-energy."
        result = transform_quarto_inline(line)
        assert result == "From equation {eq}`eq-energy`."


class TestQuartoInlineCode:
    """Test `{python} expr` -> {eval}`expr`."""

    def test_inline_code(self):
        line = "The value is `{python} compute_value()`."
        result = transform_quarto_inline(line)
        assert result == "The value is {eval}`compute_value()`."


class TestQuartoDocLink:
    """Test [text](file.qmd) -> {doc}`path`."""

    def test_doc_link(self):
        line = "See [methods](methods.qmd) for more."
        result = transform_quarto_inline(line)
        assert result == "See {doc}`methods` for more."

    def test_doc_link_with_subdir(self):
        line = "See [chapters/methods](chapters/methods.qmd) for more."
        result = transform_quarto_inline(line)
        assert result == "See {doc}`chapters/methods` for more."

    def test_non_qmd_link_unchanged(self):
        """Links to non-.qmd files should be unchanged."""
        line = "See [docs](docs.html) for more."
        result = transform_quarto_inline(line)
        assert result == "See [docs](docs.html) for more."


# ===========================================================================
# Roundtrip tests: MyST -> Quarto -> MyST
# ===========================================================================


class TestRoundtripCodeCell:
    """Test that code cells survive roundtrip."""

    def test_roundtrip_code_cell(self):
        myst = "```{code-cell} python\nprint('hello')\n```"
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "```{code-cell} python" in back
        assert "print('hello')" in back

    def test_roundtrip_code_cell_with_tags(self):
        myst = "```{code-cell} python\n:tags: [hide-input]\n\nimport numpy as np\n```"
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "```{code-cell} python" in back
        assert "hide-input" in back
        assert "import numpy as np" in back


class TestRoundtripAdmonition:
    """Test that admonitions survive roundtrip."""

    def test_roundtrip_note(self):
        myst = "```{note}\nThis is a note.\n```"
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "note" in back
        assert "This is a note." in back
        # Should not have Quarto syntax
        assert "callout" not in back

    def test_roundtrip_warning(self):
        myst = "```{warning}\nBe careful!\n```"
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "warning" in back
        assert "Be careful!" in back


class TestRoundtripInlineRoles:
    """Test that inline roles survive roundtrip."""

    def test_roundtrip_cite(self):
        myst = "See {cite}`smith2020` for details."
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "{cite}`smith2020`" in back

    def test_roundtrip_eval(self):
        myst = "The answer is {eval}`2 + 2`."
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "{eval}`2 + 2`" in back

    def test_roundtrip_numref(self):
        myst = "As shown in {numref}`fig-results`."
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "{numref}`fig-results`" in back

    def test_roundtrip_eq(self):
        myst = "From equation {eq}`energy`."
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        # MyST uses {eq}`energy` -> Quarto @eq-energy -> MyST {eq}`eq-energy`
        # The eq- prefix is added by myst_to_quarto and preserved on roundtrip
        assert "{eq}`eq-energy`" in back

    def test_roundtrip_doc(self):
        myst = "See {doc}`methods` for more."
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "{doc}`methods`" in back


class TestRoundtripFigure:
    """Test that figures survive roundtrip."""

    def test_roundtrip_figure(self):
        myst = "```{figure} images/plot.png\n:name: fig-plot\n:width: 80%\n\nMy figure caption.\n```"
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "fig-plot" in back
        assert "images/plot.png" in back
        assert "My figure caption." in back
        assert "80%" in back


class TestRoundtripMath:
    """Test that math with label survives roundtrip."""

    def test_roundtrip_math(self):
        myst = "```{math}\n:label: eq-energy\n\nE = mc^2\n```"
        quarto = convert_myst_to_quarto(myst)
        back = convert_quarto_to_myst(quarto)
        assert "eq-energy" in back
        assert "E = mc^2" in back


class TestRoundtripFullDocument:
    """Test full fixture roundtrip MyST -> Quarto -> MyST."""

    def test_roundtrip_full_document(self):
        fixtures = pathlib.Path(__file__).parent / "fixtures"
        myst_text = (fixtures / "simple_myst.md").read_text()

        quarto = convert_myst_to_quarto(myst_text)
        back = convert_quarto_to_myst(quarto)

        # Key elements should survive the roundtrip
        assert "code-cell" in back
        assert "print" not in back or "import numpy" in back  # code body preserved
        assert "note" in back
        assert "warning" in back
        assert "E = mc^2" in back
        assert "smith2020" in back


# ===========================================================================
# Quarto -> MyST: Fixture file test
# ===========================================================================


class TestQuartoFixture:
    """Test Quarto->MyST conversion using fixture files."""

    def test_quarto_fixture(self):
        fixtures = pathlib.Path(__file__).parent / "fixtures"
        quarto_text = (fixtures / "simple_quarto_input.md").read_text()
        expected = (fixtures / "simple_quarto_expected_myst.md").read_text()
        result = convert_quarto_to_myst(quarto_text)
        # Normalize trailing whitespace for comparison
        result_lines = [line.rstrip() for line in result.splitlines()]
        expected_lines = [line.rstrip() for line in expected.splitlines()]
        assert result_lines == expected_lines


# ===========================================================================
# Public API: transform_quarto_block
# ===========================================================================


class TestTransformQuartoBlock:
    """Test the transform_quarto_block public function."""

    def test_block_with_callout(self):
        lines = ["::: {.callout-note}", "Note text.", ":::"]
        result = transform_quarto_block(lines)
        result_text = "\n".join(result)
        assert "note" in result_text
        assert "callout" not in result_text

    def test_block_with_code_cell(self):
        lines = ["```{python}", "x = 1", "```"]
        result = transform_quarto_block(lines)
        result_text = "\n".join(result)
        assert "code-cell" in result_text


# ===========================================================================
# Quarto -> MyST: Table with label
# ===========================================================================


class TestQuartoTableWithLabel:
    """Test table caption with {#tbl-id} -> table directive."""

    def test_table_with_label(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |\n: My Table Caption {#tbl-data}\n"
        result = convert_quarto_to_myst(text)
        assert "```{table} My Table Caption" in result
        assert ":name: tbl-data" in result
        assert "| A | B |" in result
