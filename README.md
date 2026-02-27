# mystquarto

Bidirectional MyST Markdown ↔ Quarto converter. Transforms directives, roles, config files, and frontmatter between the two formats.

## Installation

```bash
pip install mystquarto
```

Or run directly:

```bash
uvx myst2quarto docs/
```

## Usage

```bash
# Convert MyST → Quarto
myst2quarto docs/ -o docs-quarto/

# Convert Quarto → MyST
quarto2myst docs/ -o docs-myst/

# Unified CLI
mystquarto to-quarto docs/
mystquarto to-myst docs/
```

### Options

| Flag | Description |
|---|---|
| `-o DIR` / `--output DIR` | Output directory (default: `<input>-quarto/` or `<input>-myst/`) |
| `--in-place` | Modify files in-place |
| `--config-only` | Only convert config files (`myst.yml` ↔ `_quarto.yml`) |
| `--no-config` | Skip config file conversion |
| `--dry-run` | Show what would change without writing |
| `--strict` | Treat warnings as errors |

## What it converts

### Block directives

| MyST | Quarto |
|---|---|
| `` ```{code-cell} python `` | `` ```{python} `` |
| `:tags: [remove-input]` | `#\| echo: false` |
| `:tags: [remove-output]` | `#\| output: false` |
| `:tags: [remove-cell]` | `#\| include: false` |
| `:tags: [hide-input]` | `#\| code-fold: true` |
| `` ```{figure} path `` | `![caption](path){#fig-id width=X}` |
| `` ```{math} `` + `:label:` | `$$ ... $$ {#eq-id}` |
| `` ```{note} `` | `::: {.callout-note}` |
| `` ```{warning} `` | `::: {.callout-warning}` |
| `` ```{tip} `` | `::: {.callout-tip}` |
| `` ```{important} `` | `::: {.callout-important}` |
| `` ```{admonition} Title `` | `::: {.callout-note title="Title"}` |
| `::::{tab-set}` / `:::{tab-item}` | `::: {.panel-tabset}` / `## Label` |
| `` ```{margin} `` | `::: {.column-margin}` |
| `` ```{image} url `` | `![alt](url){width=X}` |
| `` ```{table} Caption `` | Markdown table + `: Caption {#tbl-id}` |
| `` ```{bibliography} `` | Removed (Quarto handles via config) |
| `` ```{tableofcontents} `` | Removed (Quarto handles via config) |
| `` ```{mermaid} `` | Pass through (both support it) |

### Inline roles

| MyST | Quarto |
|---|---|
| `` {eval}`expr` `` | `` `{python} expr` `` |
| `` {cite}`key` `` | `[@key]` |
| `` {cite:t}`key` `` | `@key` |
| `` {cite:p}`key` `` | `[@key]` |
| `` {cite}`a,b,c` `` | `[@a; @b; @c]` |
| `` {numref}`fig-id` `` | `@fig-id` |
| `` {ref}`label` `` | `@label` |
| `` {eq}`label` `` | `@eq-label` |
| `` {doc}`path` `` | `[path](path.qmd)` |

### Config files (`myst.yml` ↔ `_quarto.yml`)

| `myst.yml` | `_quarto.yml` |
|---|---|
| `project.title` | `title:` or `book.title:` |
| `project.authors` | `author:` |
| `project.bibliography` | `bibliography:` |
| `project.toc` | `book.chapters:` |
| `site.template: book-theme` | `project.type: book` |
| `project.exports[format: pdf]` | `format.pdf:` |

### Frontmatter (per-file YAML)

| MyST | Quarto |
|---|---|
| `kernelspec: {name: python3}` | `jupyter: python3` |
| `label:` | `id:` |
| `exports:` | `format:` |

## Architecture

No heavy dependencies — just `click` + `pyyaml`. The converter uses a regex-based line scanner with a directive stack that handles nested fences (both backtick and colon styles), parses options blocks, and dispatches to transform functions. All transforms are bidirectional.

## Development

```bash
git clone https://github.com/MaxGhenis/mystquarto
cd mystquarto
uv sync --dev
uv run pytest tests/ -v      # 225 tests
uv run ruff check src/ tests/
```

## License

MIT-0
