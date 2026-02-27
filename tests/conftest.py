"""Shared test fixtures for mystquarto tests."""

import pytest
import yaml


@pytest.fixture
def myst_project(tmp_path):
    """Create a temporary MyST project with .md files and myst.yml."""
    # Create myst.yml config
    myst_config = {
        "project": {
            "title": "Test Project",
            "authors": [{"name": "Test Author"}],
            "toc": [{"file": "intro"}, {"file": "methods"}],
        },
        "site": {"template": "book-theme"},
    }
    config_path = tmp_path / "myst.yml"
    config_path.write_text(yaml.dump(myst_config, default_flow_style=False))

    # Create some .md files
    intro = tmp_path / "intro.md"
    intro.write_text(
        "---\ntitle: Introduction\n---\n\n"
        "# Introduction\n\n"
        "This is a MyST doc with {cite}`smith2020`.\n\n"
        "```{code-cell} python\n"
        "x = 1\n"
        "```\n"
    )

    methods = tmp_path / "methods.md"
    methods.write_text(
        "---\ntitle: Methods\n---\n\n"
        "# Methods\n\n"
        "See {eq}`energy` for details.\n\n"
        "```{math}\n"
        ":label: eq-energy\n\n"
        "E = mc^2\n"
        "```\n"
    )

    # Create a non-markdown file that should be skipped
    script = tmp_path / "helper.py"
    script.write_text("# Python helper\nprint('hello')\n")

    # Create a subdirectory with another .md file
    subdir = tmp_path / "chapters"
    subdir.mkdir()
    chapter = subdir / "chapter1.md"
    chapter.write_text("# Chapter 1\n\nContent of chapter 1.\n")

    return tmp_path


@pytest.fixture
def quarto_project(tmp_path):
    """Create a temporary Quarto project with .qmd files and _quarto.yml."""
    # Create _quarto.yml config
    quarto_config = {
        "project": {"type": "book"},
        "book": {
            "title": "Test Project",
            "author": [{"name": "Test Author"}],
            "chapters": ["intro.qmd", "methods.qmd"],
        },
    }
    config_path = tmp_path / "_quarto.yml"
    config_path.write_text(yaml.dump(quarto_config, default_flow_style=False))

    # Create some .qmd files
    intro = tmp_path / "intro.qmd"
    intro.write_text(
        "---\ntitle: Introduction\n---\n\n"
        "# Introduction\n\n"
        "This is a Quarto doc with [@smith2020].\n\n"
        "```{python}\n"
        "x = 1\n"
        "```\n"
    )

    methods = tmp_path / "methods.qmd"
    methods.write_text(
        "---\ntitle: Methods\n---\n\n"
        "# Methods\n\n"
        "See @eq-energy for details.\n\n"
        "$$\n"
        "E = mc^2\n"
        "$$ {#eq-energy}\n"
    )

    # Create a non-qmd file that should be skipped
    script = tmp_path / "helper.py"
    script.write_text("# Python helper\nprint('hello')\n")

    return tmp_path
