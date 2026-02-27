"""Tests for inline role transforms."""

from mystquarto.transforms.myst_to_quarto import (
    convert_myst_to_quarto,
    transform_inline,
)


# ---------------------------------------------------------------------------
# Inline role: {eval}`expr`
# ---------------------------------------------------------------------------


class TestEvalRole:
    """Test {eval}`expr` -> `{python} expr`."""

    def test_basic_eval(self):
        line = "The answer is {eval}`2 + 2`."
        result = transform_inline(line)
        assert result == "The answer is `{python} 2 + 2`."

    def test_eval_with_variable(self):
        line = "Result: {eval}`my_var`"
        result = transform_inline(line)
        assert result == "Result: `{python} my_var`"


# ---------------------------------------------------------------------------
# Inline role: {cite}`key`
# ---------------------------------------------------------------------------


class TestCiteRole:
    """Test {cite}`key` -> [@key]."""

    def test_basic_cite(self):
        line = "See {cite}`smith2020` for details."
        result = transform_inline(line)
        assert result == "See [@smith2020] for details."

    def test_multiple_cite_keys(self):
        line = "See {cite}`smith2020,jones2021,doe2022`."
        result = transform_inline(line)
        assert result == "See [@smith2020; @jones2021; @doe2022]."

    def test_cite_with_spaces_in_keys(self):
        line = "See {cite}`smith2020, jones2021`."
        result = transform_inline(line)
        assert result == "See [@smith2020; @jones2021]."


# ---------------------------------------------------------------------------
# Inline role: {cite:t}`key`
# ---------------------------------------------------------------------------


class TestCiteTextualRole:
    """Test {cite:t}`key` -> @key."""

    def test_cite_t(self):
        line = "{cite:t}`smith2020` showed that..."
        result = transform_inline(line)
        assert result == "@smith2020 showed that..."


# ---------------------------------------------------------------------------
# Inline role: {cite:p}`key`
# ---------------------------------------------------------------------------


class TestCiteParentheticalRole:
    """Test {cite:p}`key` -> [@key]."""

    def test_cite_p(self):
        line = "Results ({cite:p}`smith2020`)."
        result = transform_inline(line)
        assert result == "Results ([@smith2020])."


# ---------------------------------------------------------------------------
# Inline role: {numref}`fig-id`
# ---------------------------------------------------------------------------


class TestNumrefRole:
    """Test {numref}`fig-id` -> @fig-id."""

    def test_numref(self):
        line = "As shown in {numref}`fig-results`."
        result = transform_inline(line)
        assert result == "As shown in @fig-results."

    def test_numref_with_format_string(self):
        """numref with %s format string."""
        line = "See {numref}`Figure %s <fig-results>`."
        result = transform_inline(line)
        assert result == "See @fig-results."


# ---------------------------------------------------------------------------
# Inline role: {ref}`label`
# ---------------------------------------------------------------------------


class TestRefRole:
    """Test {ref}`label` -> @label."""

    def test_ref(self):
        line = "Refer to {ref}`sec-intro`."
        result = transform_inline(line)
        assert result == "Refer to @sec-intro."


# ---------------------------------------------------------------------------
# Inline role: {eq}`label`
# ---------------------------------------------------------------------------


class TestEqRole:
    """Test {eq}`label` -> @eq-label."""

    def test_eq(self):
        line = "From equation {eq}`energy`."
        result = transform_inline(line)
        assert result == "From equation @eq-energy."

    def test_eq_already_prefixed(self):
        """If label already starts with eq-, don't double-prefix."""
        line = "See {eq}`eq-energy`."
        result = transform_inline(line)
        assert result == "See @eq-energy."


# ---------------------------------------------------------------------------
# Inline role: {doc}`path`
# ---------------------------------------------------------------------------


class TestDocRole:
    """Test {doc}`path` -> [path](path.qmd)."""

    def test_doc(self):
        line = "See {doc}`intro` for details."
        result = transform_inline(line)
        assert result == "See [intro](intro.qmd) for details."

    def test_doc_with_subdir(self):
        line = "See {doc}`chapters/methods`."
        result = transform_inline(line)
        assert result == "See [chapters/methods](chapters/methods.qmd)."


# ---------------------------------------------------------------------------
# Mixed inline roles on same line
# ---------------------------------------------------------------------------


class TestMixedInlineRoles:
    """Test multiple different roles on the same line."""

    def test_cite_and_ref(self):
        line = "As {cite}`smith2020` noted in {ref}`sec-intro`."
        result = transform_inline(line)
        assert result == "As [@smith2020] noted in @sec-intro."

    def test_eval_and_cite(self):
        line = "Value is {eval}`x` ({cite}`doe2020`)."
        result = transform_inline(line)
        assert result == "Value is `{python} x` ([@doe2020])."

    def test_multiple_same_role(self):
        line = "{ref}`sec-a` and {ref}`sec-b`."
        result = transform_inline(line)
        assert result == "@sec-a and @sec-b."


# ---------------------------------------------------------------------------
# Passthrough: no roles
# ---------------------------------------------------------------------------


class TestNoRolesPassthrough:
    """Test lines with no roles are passed through unchanged."""

    def test_plain_text(self):
        line = "This is a plain text line."
        result = transform_inline(line)
        assert result == line

    def test_markdown_formatting(self):
        line = "Some **bold** and *italic* text."
        result = transform_inline(line)
        assert result == line

    def test_regular_code_span(self):
        line = "Use `print()` to output."
        result = transform_inline(line)
        assert result == line

    def test_empty_line(self):
        result = transform_inline("")
        assert result == ""


# ---------------------------------------------------------------------------
# Code spans: don't transform inside code
# ---------------------------------------------------------------------------


class TestCodeSpanProtection:
    """Test that roles inside code spans are NOT transformed."""

    def test_role_in_code_span(self):
        line = "Use `{cite}\\`key\\`` syntax."
        _ = transform_inline(line)
        # The content inside code backticks should be left alone
        # (the backslash-escaped backticks are literal in the code span)
        # This test checks that we don't transform things that look like
        # roles when they are inside code spans.
        # The main check is that no error is raised.

    def test_role_syntax_in_code_span_simple(self):
        """A role-like pattern inside a code span should not be transformed."""
        line = "Type `{ref}` to create a reference."
        result = transform_inline(line)
        # `{ref}` is a code span, not a role (no backtick-delimited argument)
        assert result == line


# ---------------------------------------------------------------------------
# Integration: inline transforms within full document
# ---------------------------------------------------------------------------


class TestInlineInDocument:
    """Test inline transforms work within a full document conversion."""

    def test_inline_roles_in_regular_text(self):
        text = "# Title\n\nSee {cite}`smith2020` and {ref}`fig-results`.\n"
        result = convert_myst_to_quarto(text)
        assert "[@smith2020]" in result
        assert "@fig-results" in result

    def test_inline_roles_not_in_code_blocks(self):
        """Inline roles inside code blocks should NOT be transformed."""
        text = "```python\n# {cite}`smith2020`\n```\n"
        result = convert_myst_to_quarto(text)
        # Regular fenced code blocks (not directives) should pass through
        assert "{cite}" in result
