"""Tests for config (myst.yml <-> _quarto.yml) and frontmatter conversion."""

from __future__ import annotations

import os
import textwrap

import yaml

from mystquarto.config import (
    convert_myst_config,
    convert_quarto_config,
    myst_to_quarto_config,
    quarto_to_myst_config,
)
from mystquarto.frontmatter import (
    extract_frontmatter,
    myst_to_quarto_frontmatter,
    quarto_to_myst_frontmatter,
    replace_frontmatter,
)


# =========================================================================
# Config tests: myst.yml <-> _quarto.yml
# =========================================================================


class TestBasicArticleConfig:
    """Simple project with title, author, bibliography."""

    def test_basic_article_config(self):
        myst = {
            "project": {
                "title": "My Paper",
                "authors": [{"name": "Jane Doe"}],
                "bibliography": ["refs.bib"],
            }
        }
        result = myst_to_quarto_config(myst)
        assert result["title"] == "My Paper"
        assert result["author"] == [{"name": "Jane Doe"}]
        assert result["bibliography"] == ["refs.bib"]
        # Should NOT have project.type: book
        assert "book" not in result

    def test_single_bibliography_string(self):
        """Single bibliography entry as string rather than list."""
        myst = {
            "project": {
                "title": "My Paper",
                "bibliography": "refs.bib",
            }
        }
        result = myst_to_quarto_config(myst)
        assert result["bibliography"] == "refs.bib"


class TestBookConfig:
    """Project with toc and book-theme."""

    def test_book_config_from_template(self):
        """Detect book type from site.template: book-theme."""
        myst = {
            "project": {
                "title": "My Book",
                "authors": [{"name": "Author One"}],
                "toc": [
                    {"file": "index"},
                    {"file": "chapter1"},
                    {"file": "chapter2"},
                ],
            },
            "site": {"template": "book-theme"},
        }
        result = myst_to_quarto_config(myst)
        assert result["project"]["type"] == "book"
        assert result["book"]["title"] == "My Book"
        assert result["book"]["author"] == [{"name": "Author One"}]
        assert result["book"]["chapters"] == [
            "index.qmd",
            "chapter1.qmd",
            "chapter2.qmd",
        ]

    def test_book_config_from_toc(self):
        """Detect book type from presence of project.toc."""
        myst = {
            "project": {
                "title": "Another Book",
                "toc": [
                    {"file": "intro"},
                    {"file": "ch1"},
                ],
            },
        }
        result = myst_to_quarto_config(myst)
        assert result["project"]["type"] == "book"
        assert result["book"]["title"] == "Another Book"
        assert result["book"]["chapters"] == ["intro.qmd", "ch1.qmd"]


class TestExportsToFormat:
    """pdf/docx exports mapping."""

    def test_pdf_export(self):
        myst = {
            "project": {
                "title": "Paper",
                "exports": [
                    {
                        "format": "pdf",
                        "template": "arxiv_two_column",
                        "output": "paper.pdf",
                    }
                ],
            }
        }
        result = myst_to_quarto_config(myst)
        assert "format" in result
        assert "pdf" in result["format"]
        assert result["format"]["pdf"]["template"] == "arxiv_two_column"

    def test_docx_export(self):
        myst = {
            "project": {
                "title": "Paper",
                "exports": [
                    {
                        "format": "docx",
                        "output": "paper.docx",
                    }
                ],
            }
        }
        result = myst_to_quarto_config(myst)
        assert "format" in result
        assert "docx" in result["format"]

    def test_multiple_exports(self):
        myst = {
            "project": {
                "title": "Paper",
                "exports": [
                    {"format": "pdf", "template": "plain_latex"},
                    {"format": "docx"},
                ],
            }
        }
        result = myst_to_quarto_config(myst)
        assert "pdf" in result["format"]
        assert "docx" in result["format"]


class TestAuthorsWithAffiliations:
    """Structured author list."""

    def test_authors_with_affiliations(self):
        myst = {
            "project": {
                "title": "Paper",
                "authors": [
                    {
                        "name": "Alice Smith",
                        "affiliations": ["MIT", "Harvard"],
                    },
                    {
                        "name": "Bob Jones",
                        "affiliations": ["Stanford"],
                    },
                ],
            }
        }
        result = myst_to_quarto_config(myst)
        assert result["author"] == [
            {"name": "Alice Smith", "affiliations": ["MIT", "Harvard"]},
            {"name": "Bob Jones", "affiliations": ["Stanford"]},
        ]


class TestConfigRoundtrip:
    """myst -> quarto -> myst preserves data."""

    def test_article_roundtrip(self):
        myst = {
            "project": {
                "title": "Roundtrip Paper",
                "authors": [{"name": "Author A"}],
                "bibliography": ["refs.bib"],
                "keywords": ["test", "roundtrip"],
                "date": "2024-01-15",
                "github": "https://github.com/user/repo",
                "license": "MIT",
                "subject": "A paper about roundtrips",
            }
        }
        quarto = myst_to_quarto_config(myst)
        restored = quarto_to_myst_config(quarto)
        assert restored["project"]["title"] == myst["project"]["title"]
        assert restored["project"]["authors"] == myst["project"]["authors"]
        assert restored["project"]["bibliography"] == myst["project"]["bibliography"]
        assert restored["project"]["keywords"] == myst["project"]["keywords"]
        assert restored["project"]["date"] == myst["project"]["date"]
        assert restored["project"]["github"] == myst["project"]["github"]
        assert restored["project"]["license"] == myst["project"]["license"]
        assert restored["project"]["subject"] == myst["project"]["subject"]

    def test_book_roundtrip(self):
        myst = {
            "project": {
                "title": "Roundtrip Book",
                "authors": [{"name": "Author B"}],
                "toc": [
                    {"file": "index"},
                    {"file": "chapter1"},
                ],
            },
            "site": {"template": "book-theme"},
        }
        quarto = myst_to_quarto_config(myst)
        restored = quarto_to_myst_config(quarto)
        assert restored["project"]["title"] == myst["project"]["title"]
        assert restored["project"]["authors"] == myst["project"]["authors"]
        assert restored["project"]["toc"] == myst["project"]["toc"]
        assert restored["site"]["template"] == "book-theme"


class TestEmptyConfig:
    """Empty dict -> empty dict."""

    def test_empty_myst_to_quarto(self):
        assert myst_to_quarto_config({}) == {}

    def test_empty_quarto_to_myst(self):
        assert quarto_to_myst_config({}) == {}


class TestConfigFileIO:
    """Write/read myst.yml -> _quarto.yml using tmp_path."""

    def test_myst_to_quarto_file(self, tmp_path):
        myst_data = {
            "project": {
                "title": "File IO Test",
                "authors": [{"name": "Test Author"}],
                "bibliography": ["refs.bib"],
            }
        }
        myst_path = tmp_path / "myst.yml"
        with open(myst_path, "w") as f:
            yaml.dump(myst_data, f)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result_path = convert_myst_config(str(myst_path), str(output_dir))
        assert os.path.exists(result_path)
        assert result_path.endswith("_quarto.yml")

        with open(result_path) as f:
            quarto_data = yaml.safe_load(f)
        assert quarto_data["title"] == "File IO Test"

    def test_quarto_to_myst_file(self, tmp_path):
        quarto_data = {
            "title": "Quarto to MyST",
            "author": [{"name": "Test Author"}],
            "bibliography": ["refs.bib"],
        }
        quarto_path = tmp_path / "_quarto.yml"
        with open(quarto_path, "w") as f:
            yaml.dump(quarto_data, f)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result_path = convert_quarto_config(str(quarto_path), str(output_dir))
        assert os.path.exists(result_path)
        assert result_path.endswith("myst.yml")

        with open(result_path) as f:
            myst_data = yaml.safe_load(f)
        assert myst_data["project"]["title"] == "Quarto to MyST"


class TestAdditionalConfigFields:
    """Test github, license, keywords, date, subject mappings."""

    def test_github_to_repo_url(self):
        myst = {
            "project": {
                "title": "Paper",
                "github": "https://github.com/user/repo",
            }
        }
        result = myst_to_quarto_config(myst)
        assert result["repo-url"] == "https://github.com/user/repo"

    def test_license_passthrough(self):
        myst = {
            "project": {
                "title": "Paper",
                "license": "MIT",
            }
        }
        result = myst_to_quarto_config(myst)
        assert result["license"] == "MIT"

    def test_keywords_passthrough(self):
        myst = {
            "project": {
                "title": "Paper",
                "keywords": ["machine learning", "AI"],
            }
        }
        result = myst_to_quarto_config(myst)
        assert result["keywords"] == ["machine learning", "AI"]

    def test_date_passthrough(self):
        myst = {
            "project": {
                "title": "Paper",
                "date": "2024-06-15",
            }
        }
        result = myst_to_quarto_config(myst)
        assert result["date"] == "2024-06-15"

    def test_subject_to_description(self):
        myst = {
            "project": {
                "title": "Paper",
                "subject": "A study about something",
            }
        }
        result = myst_to_quarto_config(myst)
        assert result["description"] == "A study about something"


class TestQuartoToMystConfig:
    """Test reverse mapping: _quarto.yml -> myst.yml."""

    def test_basic_article(self):
        quarto = {
            "title": "My Paper",
            "author": [{"name": "Jane Doe"}],
            "bibliography": ["refs.bib"],
        }
        result = quarto_to_myst_config(quarto)
        assert result["project"]["title"] == "My Paper"
        assert result["project"]["authors"] == [{"name": "Jane Doe"}]
        assert result["project"]["bibliography"] == ["refs.bib"]

    def test_book_type(self):
        quarto = {
            "project": {"type": "book"},
            "book": {
                "title": "My Book",
                "author": [{"name": "Author One"}],
                "chapters": ["index.qmd", "chapter1.qmd"],
            },
        }
        result = quarto_to_myst_config(quarto)
        assert result["project"]["title"] == "My Book"
        assert result["project"]["authors"] == [{"name": "Author One"}]
        assert result["project"]["toc"] == [
            {"file": "index"},
            {"file": "chapter1"},
        ]
        assert result["site"]["template"] == "book-theme"

    def test_repo_url_to_github(self):
        quarto = {
            "title": "Paper",
            "repo-url": "https://github.com/user/repo",
        }
        result = quarto_to_myst_config(quarto)
        assert result["project"]["github"] == "https://github.com/user/repo"

    def test_description_to_subject(self):
        quarto = {
            "title": "Paper",
            "description": "A study about something",
        }
        result = quarto_to_myst_config(quarto)
        assert result["project"]["subject"] == "A study about something"

    def test_format_to_exports(self):
        quarto = {
            "title": "Paper",
            "format": {
                "pdf": {"template": "arxiv_two_column"},
                "docx": {},
            },
        }
        result = quarto_to_myst_config(quarto)
        exports = result["project"]["exports"]
        pdf_exports = [e for e in exports if e["format"] == "pdf"]
        docx_exports = [e for e in exports if e["format"] == "docx"]
        assert len(pdf_exports) == 1
        assert pdf_exports[0]["template"] == "arxiv_two_column"
        assert len(docx_exports) == 1


# =========================================================================
# Frontmatter tests: per-file YAML frontmatter transforms
# =========================================================================


class TestKernelspecToJupyter:
    """kernelspec mapping."""

    def test_basic_kernelspec(self):
        fm = {
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
            }
        }
        result = myst_to_quarto_frontmatter(fm)
        assert result["jupyter"] == "python3"
        assert "kernelspec" not in result

    def test_kernelspec_with_jupytext(self):
        """kernelspec + jupytext combo -> just jupyter: python3."""
        fm = {
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
            },
            "jupytext": {
                "formats": "md:myst",
                "text_representation": {
                    "extension": ".md",
                    "format_name": "myst",
                },
            },
        }
        result = myst_to_quarto_frontmatter(fm)
        assert result["jupyter"] == "python3"
        assert "kernelspec" not in result
        assert "jupytext" not in result

    def test_r_kernelspec(self):
        fm = {
            "kernelspec": {
                "name": "ir",
                "display_name": "R",
            }
        }
        result = myst_to_quarto_frontmatter(fm)
        assert result["jupyter"] == "ir"


class TestFrontmatterExportsToFormat:
    """Per-file exports."""

    def test_pdf_export(self):
        fm = {
            "exports": [
                {
                    "format": "pdf",
                    "template": "plain_latex",
                }
            ]
        }
        result = myst_to_quarto_frontmatter(fm)
        assert "format" in result
        assert "pdf" in result["format"]
        assert result["format"]["pdf"]["template"] == "plain_latex"
        assert "exports" not in result

    def test_multiple_exports(self):
        fm = {
            "exports": [
                {"format": "pdf"},
                {"format": "docx"},
            ]
        }
        result = myst_to_quarto_frontmatter(fm)
        assert "pdf" in result["format"]
        assert "docx" in result["format"]


class TestLabelToId:
    """label -> id mapping."""

    def test_label_to_id(self):
        fm = {"label": "my-section"}
        result = myst_to_quarto_frontmatter(fm)
        assert result["id"] == "my-section"
        assert "label" not in result

    def test_label_with_other_fields(self):
        fm = {"label": "sec-intro", "title": "Introduction"}
        result = myst_to_quarto_frontmatter(fm)
        assert result["id"] == "sec-intro"
        assert result["title"] == "Introduction"


class TestPassthroughFields:
    """title, author, date kept."""

    def test_passthrough_fields(self):
        fm = {
            "title": "My Document",
            "author": "Jane Doe",
            "date": "2024-01-15",
            "tags": ["python", "data"],
        }
        result = myst_to_quarto_frontmatter(fm)
        assert result["title"] == "My Document"
        assert result["author"] == "Jane Doe"
        assert result["date"] == "2024-01-15"
        assert result["tags"] == ["python", "data"]


class TestRemoveMystOnlyFields:
    """math, abbreviations removed."""

    def test_math_removed(self):
        fm = {
            "title": "Paper",
            "math": {"equationNumbers": "AMS"},
        }
        result = myst_to_quarto_frontmatter(fm)
        assert "math" not in result
        assert result["title"] == "Paper"

    def test_abbreviations_removed(self):
        fm = {
            "title": "Paper",
            "abbreviations": {
                "ML": "Machine Learning",
                "AI": "Artificial Intelligence",
            },
        }
        result = myst_to_quarto_frontmatter(fm)
        assert "abbreviations" not in result
        assert result["title"] == "Paper"

    def test_both_removed(self):
        fm = {
            "title": "Paper",
            "math": {"equationNumbers": "AMS"},
            "abbreviations": {"ML": "Machine Learning"},
        }
        result = myst_to_quarto_frontmatter(fm)
        assert "math" not in result
        assert "abbreviations" not in result


class TestNumberingToEquationPrefix:
    """numbering.equation.template -> crossref.eq-prefix."""

    def test_equation_numbering(self):
        fm = {
            "numbering": {
                "equation": {
                    "template": "Eq. %s",
                }
            }
        }
        result = myst_to_quarto_frontmatter(fm)
        assert result["crossref"]["eq-prefix"] == "Eq. %s"
        assert "numbering" not in result


class TestFrontmatterRoundtrip:
    """Both directions."""

    def test_roundtrip(self):
        myst_fm = {
            "title": "Test Doc",
            "author": "Author A",
            "date": "2024-01-15",
            "label": "my-doc",
            "tags": ["test"],
        }
        quarto_fm = myst_to_quarto_frontmatter(myst_fm)
        restored = quarto_to_myst_frontmatter(quarto_fm)
        assert restored["title"] == myst_fm["title"]
        assert restored["author"] == myst_fm["author"]
        assert restored["date"] == myst_fm["date"]
        assert restored["label"] == myst_fm["label"]
        assert restored["tags"] == myst_fm["tags"]

    def test_kernelspec_roundtrip(self):
        myst_fm = {
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
            }
        }
        quarto_fm = myst_to_quarto_frontmatter(myst_fm)
        restored = quarto_to_myst_frontmatter(quarto_fm)
        assert restored["kernelspec"]["name"] == "python3"


class TestExtractFrontmatter:
    """Parsing frontmatter from text."""

    def test_extract_frontmatter(self):
        text = textwrap.dedent("""\
            ---
            title: My Document
            author: Jane Doe
            ---

            # Content here
            Some text.
        """)
        fm, body = extract_frontmatter(text)
        assert fm is not None
        assert fm["title"] == "My Document"
        assert fm["author"] == "Jane Doe"
        assert "# Content here" in body
        assert "Some text." in body

    def test_complex_frontmatter(self):
        text = textwrap.dedent("""\
            ---
            title: My Document
            kernelspec:
              name: python3
              display_name: Python 3
            tags:
              - python
              - data
            ---

            Body text.
        """)
        fm, body = extract_frontmatter(text)
        assert fm["title"] == "My Document"
        assert fm["kernelspec"]["name"] == "python3"
        assert fm["tags"] == ["python", "data"]
        assert "Body text." in body


class TestNoFrontmatter:
    """Text without frontmatter."""

    def test_no_frontmatter(self):
        text = "# Just a heading\n\nSome content.\n"
        fm, body = extract_frontmatter(text)
        assert fm is None
        assert body == text

    def test_empty_text(self):
        fm, body = extract_frontmatter("")
        assert fm is None
        assert body == ""


class TestReplaceFrontmatter:
    """Replacing frontmatter in text."""

    def test_replace_existing(self):
        text = textwrap.dedent("""\
            ---
            title: Old Title
            ---

            Body content.
        """)
        new_fm = {"title": "New Title", "author": "New Author"}
        result = replace_frontmatter(text, new_fm)
        fm, body = extract_frontmatter(result)
        assert fm["title"] == "New Title"
        assert fm["author"] == "New Author"
        assert "Body content." in body

    def test_add_frontmatter_to_plain_text(self):
        text = "# Heading\n\nBody content.\n"
        new_fm = {"title": "Added Title"}
        result = replace_frontmatter(text, new_fm)
        fm, body = extract_frontmatter(result)
        assert fm["title"] == "Added Title"
        assert "# Heading" in body
        assert "Body content." in body


class TestFileExtensionUpdate:
    """.md -> .qmd in references."""

    def test_toc_file_extensions(self):
        """File references in toc should get .qmd extension."""
        myst = {
            "project": {
                "title": "Book",
                "toc": [
                    {"file": "index"},
                    {"file": "chapter1"},
                ],
            },
            "site": {"template": "book-theme"},
        }
        result = myst_to_quarto_config(myst)
        for chapter in result["book"]["chapters"]:
            assert chapter.endswith(".qmd")

    def test_frontmatter_md_to_qmd(self):
        """File extension references in frontmatter should be updated."""
        fm = {
            "title": "Doc",
            "exports": [
                {
                    "format": "pdf",
                    "output": "paper.md",
                }
            ],
        }
        result = myst_to_quarto_frontmatter(fm)
        # The output filename should not be transformed (it's a PDF output)
        # but any .md references to source files should become .qmd
        assert "format" in result


class TestQuartoToMystFrontmatter:
    """Reverse frontmatter mapping."""

    def test_jupyter_to_kernelspec(self):
        fm = {"jupyter": "python3"}
        result = quarto_to_myst_frontmatter(fm)
        assert result["kernelspec"]["name"] == "python3"
        assert "jupyter" not in result

    def test_id_to_label(self):
        fm = {"id": "my-section"}
        result = quarto_to_myst_frontmatter(fm)
        assert result["label"] == "my-section"
        assert "id" not in result

    def test_format_to_exports(self):
        fm = {
            "format": {
                "pdf": {"template": "plain_latex"},
            }
        }
        result = quarto_to_myst_frontmatter(fm)
        assert "exports" in result
        assert result["exports"][0]["format"] == "pdf"
        assert result["exports"][0]["template"] == "plain_latex"
        assert "format" not in result

    def test_crossref_to_numbering(self):
        fm = {
            "crossref": {
                "eq-prefix": "Eq. %s",
            }
        }
        result = quarto_to_myst_frontmatter(fm)
        assert result["numbering"]["equation"]["template"] == "Eq. %s"
        assert "crossref" not in result

    def test_passthrough_fields(self):
        fm = {
            "title": "My Doc",
            "author": "Author A",
            "date": "2024-01-15",
            "tags": ["a", "b"],
        }
        result = quarto_to_myst_frontmatter(fm)
        assert result["title"] == "My Doc"
        assert result["author"] == "Author A"
        assert result["date"] == "2024-01-15"
        assert result["tags"] == ["a", "b"]
