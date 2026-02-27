"""Tests for CLI, orchestrator (convert.py), and warnings module."""

import os

import pytest
import yaml
from click.testing import CliRunner

from mystquarto.cli import main, myst2quarto, quarto2myst
from mystquarto.convert import (
    ConversionResult,
    Direction,
    convert_directory,
    convert_file,
    discover_files,
)
from mystquarto.warnings import WarningCollector


# ============================================================================
# Warning collector tests
# ============================================================================


class TestWarningCollector:
    """Tests for WarningCollector."""

    def test_warning_collector_basic(self):
        """Basic warn and error accumulation."""
        wc = WarningCollector()
        wc.warn("something looks off")
        wc.error("something broke")

        assert len(wc.warnings) == 1
        assert len(wc.errors) == 1
        assert "something looks off" in wc.warnings[0]
        assert "something broke" in wc.errors[0]

    def test_warning_with_file_and_line(self):
        """Warn with file and line info formats correctly."""
        wc = WarningCollector()
        wc.warn("bad syntax", file="test.md", line=42)

        assert wc.warnings[0] == "test.md:42: bad syntax"

    def test_error_with_file_and_line(self):
        """Error with file and line info formats correctly."""
        wc = WarningCollector()
        wc.error("parse error", file="doc.md", line=10)

        assert wc.errors[0] == "doc.md:10: parse error"

    def test_strict_mode_warnings_become_errors(self):
        """In strict mode, warnings are promoted to errors."""
        wc = WarningCollector(strict=True)
        wc.warn("this is a warning")

        assert len(wc.warnings) == 0
        assert len(wc.errors) == 1
        assert "this is a warning" in wc.errors[0]

    def test_has_errors(self):
        """has_errors returns True only when errors exist."""
        wc = WarningCollector()
        assert wc.has_errors() is False

        wc.warn("just a warning")
        assert wc.has_errors() is False

        wc.error("real error")
        assert wc.has_errors() is True

    def test_report_format(self):
        """Report generates a readable summary."""
        wc = WarningCollector()
        wc.warn("warn1")
        wc.warn("warn2")
        wc.error("err1")

        report = wc.report()
        assert "warn1" in report
        assert "warn2" in report
        assert "err1" in report
        # Report should mention counts or at least list items
        assert "warning" in report.lower() or "Warning" in report
        assert "error" in report.lower() or "Error" in report

    def test_report_empty(self):
        """Report with no warnings or errors is clean."""
        wc = WarningCollector()
        report = wc.report()
        # Should indicate success or be minimal
        assert report is not None

    def test_warn_no_file(self):
        """Warning without file/line has no prefix."""
        wc = WarningCollector()
        wc.warn("general warning")
        assert wc.warnings[0] == "general warning"

    def test_error_no_file(self):
        """Error without file/line has no prefix."""
        wc = WarningCollector()
        wc.error("general error")
        assert wc.errors[0] == "general error"


# ============================================================================
# Discover files tests
# ============================================================================


class TestDiscoverFiles:
    """Tests for discover_files function."""

    def test_discover_myst_files(self, myst_project):
        """Finds .md files and myst.yml in a MyST project."""
        files = discover_files(str(myst_project), Direction.MYST_TO_QUARTO)

        filenames = [os.path.basename(f) for f in files]
        assert "intro.md" in filenames
        assert "methods.md" in filenames
        # Should also find config
        assert "myst.yml" in filenames
        # Should NOT find .py files
        assert "helper.py" not in filenames

    def test_discover_quarto_files(self, quarto_project):
        """Finds .qmd files and _quarto.yml in a Quarto project."""
        files = discover_files(str(quarto_project), Direction.QUARTO_TO_MYST)

        filenames = [os.path.basename(f) for f in files]
        assert "intro.qmd" in filenames
        assert "methods.qmd" in filenames
        assert "_quarto.yml" in filenames
        assert "helper.py" not in filenames

    def test_discover_myst_no_config(self, tmp_path):
        """Works when there is no config file."""
        (tmp_path / "doc.md").write_text("# Hello\n")
        files = discover_files(str(tmp_path), Direction.MYST_TO_QUARTO)

        filenames = [os.path.basename(f) for f in files]
        assert "doc.md" in filenames
        assert "myst.yml" not in filenames

    def test_discover_empty_directory(self, tmp_path):
        """Returns empty list for directory with no relevant files."""
        files = discover_files(str(tmp_path), Direction.MYST_TO_QUARTO)
        assert files == []


# ============================================================================
# Convert file tests
# ============================================================================


class TestConvertFile:
    """Tests for convert_file function."""

    def test_convert_single_file_myst_to_quarto(self, tmp_path):
        """Convert a single .md file to .qmd format."""
        input_file = tmp_path / "doc.md"
        input_file.write_text(
            "# Hello\n\n"
            "See {cite}`smith2020` for details.\n"
        )
        output_file = tmp_path / "output" / "doc.qmd"
        os.makedirs(tmp_path / "output", exist_ok=True)

        result = convert_file(
            str(input_file), str(output_file), Direction.MYST_TO_QUARTO
        )

        assert not result.skipped
        assert result.output_path == str(output_file)
        assert os.path.exists(output_file)

        content = output_file.read_text()
        assert "[@smith2020]" in content

    def test_convert_single_file_quarto_to_myst(self, tmp_path):
        """Convert a single .qmd file to .md format."""
        input_file = tmp_path / "doc.qmd"
        input_file.write_text(
            "# Hello\n\n"
            "See [@smith2020] for details.\n"
        )
        output_file = tmp_path / "output" / "doc.md"
        os.makedirs(tmp_path / "output", exist_ok=True)

        result = convert_file(
            str(input_file), str(output_file), Direction.QUARTO_TO_MYST
        )

        assert not result.skipped
        assert result.output_path == str(output_file)
        assert os.path.exists(output_file)

        content = output_file.read_text()
        assert "{cite}`smith2020`" in content

    def test_convert_file_dry_run(self, tmp_path):
        """Dry run does not write output file."""
        input_file = tmp_path / "doc.md"
        input_file.write_text("# Hello\n")
        output_file = tmp_path / "output" / "doc.qmd"
        os.makedirs(tmp_path / "output", exist_ok=True)

        result = convert_file(
            str(input_file), str(output_file), Direction.MYST_TO_QUARTO, dry_run=True
        )

        assert result.dry_run is True
        assert not os.path.exists(output_file)

    def test_convert_file_with_frontmatter(self, tmp_path):
        """Frontmatter is transformed during conversion."""
        input_file = tmp_path / "doc.md"
        input_file.write_text(
            "---\n"
            "title: My Doc\n"
            "kernelspec:\n"
            "  name: python3\n"
            "---\n\n"
            "# Content\n"
        )
        output_file = tmp_path / "doc.qmd"

        result = convert_file(
            str(input_file), str(output_file), Direction.MYST_TO_QUARTO
        )

        content = output_file.read_text()
        assert "jupyter:" in content
        # kernelspec should be converted to jupyter
        assert "kernelspec" not in content

    def test_convert_file_nonexistent(self, tmp_path):
        """Converting a nonexistent file produces an error."""
        result = convert_file(
            str(tmp_path / "nonexistent.md"),
            str(tmp_path / "out.qmd"),
            Direction.MYST_TO_QUARTO,
        )
        assert len(result.errors) > 0


# ============================================================================
# Convert directory tests
# ============================================================================


class TestConvertDirectory:
    """Tests for convert_directory function."""

    def test_convert_directory_creates_output(self, myst_project, tmp_path):
        """Output directory is created and files are written."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(myst_project),
            str(output_dir),
            Direction.MYST_TO_QUARTO,
        )

        assert os.path.isdir(output_dir)
        # Should have results for the markdown files
        md_results = [r for r in results if not r.skipped and r.output_path and r.output_path.endswith(".qmd")]
        assert len(md_results) >= 2  # intro.qmd, methods.qmd

    def test_config_file_conversion(self, myst_project, tmp_path):
        """myst.yml is converted to _quarto.yml during directory conversion."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(myst_project),
            str(output_dir),
            Direction.MYST_TO_QUARTO,
        )

        quarto_config = output_dir / "_quarto.yml"
        assert quarto_config.exists()
        with open(quarto_config) as f:
            config = yaml.safe_load(f)
        # Should have book structure
        assert "book" in config

    def test_quarto_config_file_conversion(self, quarto_project, tmp_path):
        """_quarto.yml is converted to myst.yml during directory conversion."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(quarto_project),
            str(output_dir),
            Direction.QUARTO_TO_MYST,
        )

        myst_config = output_dir / "myst.yml"
        assert myst_config.exists()
        with open(myst_config) as f:
            config = yaml.safe_load(f)
        assert "project" in config

    def test_non_markdown_copied_as_assets(self, myst_project, tmp_path):
        """Non-markdown files like .py are copied as assets, not converted."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(myst_project),
            str(output_dir),
            Direction.MYST_TO_QUARTO,
        )

        # helper.py should be copied as an asset
        assert (output_dir / "helper.py").exists()
        # But not listed in conversion results
        output_paths = [r.output_path for r in results if r.output_path]
        assert not any("helper.py" in p for p in output_paths)

    def test_file_extension_renaming_myst_to_quarto(self, myst_project, tmp_path):
        """MyST .md files become .qmd in output."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(myst_project),
            str(output_dir),
            Direction.MYST_TO_QUARTO,
        )

        # Check that output files have .qmd extension
        md_results = [r for r in results if r.output_path and r.output_path.endswith(".qmd")]
        assert len(md_results) >= 2

        # No .md files should exist in the output (except possibly config-related)
        for r in results:
            if r.output_path and not r.skipped:
                if r.output_path.endswith(".md"):
                    pytest.fail(f"Found .md file in output: {r.output_path}")

    def test_file_extension_renaming_quarto_to_myst(self, quarto_project, tmp_path):
        """Quarto .qmd files become .md in output."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(quarto_project),
            str(output_dir),
            Direction.QUARTO_TO_MYST,
        )

        md_results = [r for r in results if r.output_path and r.output_path.endswith(".md")]
        assert len(md_results) >= 2

    def test_in_place_modifies_source(self, myst_project):
        """--in-place overwrites source files."""
        intro_path = myst_project / "intro.md"
        original_content = intro_path.read_text()

        results = convert_directory(
            str(myst_project),
            None,
            Direction.MYST_TO_QUARTO,
            in_place=True,
        )

        # intro.md should now be intro.qmd
        assert (myst_project / "intro.qmd").exists()
        content = (myst_project / "intro.qmd").read_text()
        # Content should be transformed
        assert "[@smith2020]" in content

    def test_config_only(self, myst_project, tmp_path):
        """--config-only only converts config files, not markdown."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(myst_project),
            str(output_dir),
            Direction.MYST_TO_QUARTO,
            config_only=True,
        )

        # Should have config result
        assert (output_dir / "_quarto.yml").exists()
        # Should NOT have converted markdown files
        assert not (output_dir / "intro.qmd").exists()
        assert not (output_dir / "methods.qmd").exists()

    def test_no_config(self, myst_project, tmp_path):
        """--no-config skips config conversion."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(myst_project),
            str(output_dir),
            Direction.MYST_TO_QUARTO,
            no_config=True,
        )

        # Should NOT have config file
        assert not (output_dir / "_quarto.yml").exists()
        # But should have converted markdown files
        assert (output_dir / "intro.qmd").exists()

    def test_dry_run_no_writes(self, myst_project, tmp_path):
        """--dry-run does not write any files."""
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(myst_project),
            str(output_dir),
            Direction.MYST_TO_QUARTO,
            dry_run=True,
        )

        # Output directory may or may not be created,
        # but no converted files should exist
        if output_dir.exists():
            assert not (output_dir / "intro.qmd").exists()
            assert not (output_dir / "methods.qmd").exists()

    def test_default_output_dir(self, myst_project):
        """When no output or in-place, default output dir is created."""
        results = convert_directory(
            str(myst_project),
            None,  # no output dir specified
            Direction.MYST_TO_QUARTO,
            in_place=False,
        )

        # Should have created a default output directory
        expected_dir = str(myst_project) + "-quarto"
        assert os.path.isdir(expected_dir)

    def test_single_file_path(self, tmp_path):
        """When path is a single file, convert just that file."""
        input_file = tmp_path / "doc.md"
        input_file.write_text("# Hello\n\nSee {cite}`ref1`.\n")
        output_dir = tmp_path / "output"

        results = convert_directory(
            str(input_file),
            str(output_dir),
            Direction.MYST_TO_QUARTO,
        )

        assert len(results) == 1
        assert results[0].output_path.endswith(".qmd")
        output_file = output_dir / "doc.qmd"
        assert output_file.exists()


# ============================================================================
# CLI tests
# ============================================================================


class TestMyst2QuartoCLI:
    """Tests for the myst2quarto CLI command."""

    def test_myst2quarto_single_file(self, tmp_path):
        """myst2quarto converts a single .md file."""
        input_file = tmp_path / "doc.md"
        input_file.write_text("# Hello\n\nSee {cite}`ref1`.\n")
        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(myst2quarto, [str(input_file), "-o", str(output_dir)])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (output_dir / "doc.qmd").exists()

    def test_myst2quarto_directory(self, myst_project):
        """myst2quarto converts a directory of .md files."""
        output_dir = str(myst_project) + "-out"

        runner = CliRunner()
        result = runner.invoke(myst2quarto, [str(myst_project), "-o", output_dir])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert os.path.isdir(output_dir)
        assert os.path.exists(os.path.join(output_dir, "intro.qmd"))

    def test_nonexistent_path(self, tmp_path):
        """Error for nonexistent input path."""
        runner = CliRunner()
        result = runner.invoke(myst2quarto, [str(tmp_path / "nope")])

        assert result.exit_code != 0


class TestQuarto2MystCLI:
    """Tests for the quarto2myst CLI command."""

    def test_quarto2myst_single_file(self, tmp_path):
        """quarto2myst converts a single .qmd file."""
        input_file = tmp_path / "doc.qmd"
        input_file.write_text("# Hello\n\nSee [@ref1].\n")
        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(quarto2myst, [str(input_file), "-o", str(output_dir)])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (output_dir / "doc.md").exists()

    def test_quarto2myst_directory(self, quarto_project):
        """quarto2myst converts a directory of .qmd files."""
        output_dir = str(quarto_project) + "-out"

        runner = CliRunner()
        result = runner.invoke(quarto2myst, [str(quarto_project), "-o", output_dir])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert os.path.isdir(output_dir)
        assert os.path.exists(os.path.join(output_dir, "intro.md"))


class TestCLIOptions:
    """Tests for CLI option flags."""

    def test_output_option(self, myst_project, tmp_path):
        """--output writes to specified directory."""
        output_dir = tmp_path / "custom_output"

        runner = CliRunner()
        result = runner.invoke(
            myst2quarto, [str(myst_project), "-o", str(output_dir)]
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert output_dir.exists()
        assert (output_dir / "intro.qmd").exists()

    def test_in_place_option(self, myst_project):
        """--in-place modifies source files."""
        runner = CliRunner()
        result = runner.invoke(myst2quarto, [str(myst_project), "--in-place"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (myst_project / "intro.qmd").exists()

    def test_dry_run(self, myst_project, tmp_path):
        """--dry-run shows changes without writing."""
        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            myst2quarto, [str(myst_project), "-o", str(output_dir), "--dry-run"]
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should not write files
        if output_dir.exists():
            assert not (output_dir / "intro.qmd").exists()

    def test_config_only(self, myst_project, tmp_path):
        """--config-only only converts config files."""
        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            myst2quarto, [str(myst_project), "-o", str(output_dir), "--config-only"]
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (output_dir / "_quarto.yml").exists()
        assert not (output_dir / "intro.qmd").exists()

    def test_no_config(self, myst_project, tmp_path):
        """--no-config skips config conversion."""
        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            myst2quarto, [str(myst_project), "-o", str(output_dir), "--no-config"]
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert not (output_dir / "_quarto.yml").exists()
        assert (output_dir / "intro.qmd").exists()

    def test_strict_mode(self, tmp_path):
        """--strict treats warnings as errors and exits nonzero."""
        # Create a file with content that might generate warnings
        input_file = tmp_path / "doc.md"
        input_file.write_text("# Hello\n")
        output_dir = tmp_path / "output"

        runner = CliRunner()
        # With strict mode, the command should still succeed if no warnings
        result = runner.invoke(
            myst2quarto, [str(input_file), "-o", str(output_dir), "--strict"]
        )
        # Should succeed if there are no warnings
        assert result.exit_code == 0, f"CLI failed: {result.output}"


class TestMainSubcommands:
    """Tests for the main mystquarto group command."""

    def test_main_to_quarto_subcommand(self, tmp_path):
        """mystquarto to-quarto works."""
        input_file = tmp_path / "doc.md"
        input_file.write_text("# Hello\n\nSee {cite}`ref1`.\n")
        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            main, ["to-quarto", str(input_file), "-o", str(output_dir)]
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (output_dir / "doc.qmd").exists()

    def test_main_to_myst_subcommand(self, tmp_path):
        """mystquarto to-myst works."""
        input_file = tmp_path / "doc.qmd"
        input_file.write_text("# Hello\n\nSee [@ref1].\n")
        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            main, ["to-myst", str(input_file), "-o", str(output_dir)]
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (output_dir / "doc.md").exists()

    def test_main_no_subcommand(self):
        """Running mystquarto without subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(main, [])

        # Should show help, not error
        assert result.exit_code == 0
        assert "to-quarto" in result.output
        assert "to-myst" in result.output
