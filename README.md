# mystquarto

Bidirectional MyST ↔ Quarto converter.

## Installation

```bash
pip install mystquarto
# or
uvx mystquarto
```

## Usage

```bash
# Convert MyST → Quarto
myst2quarto docs/
mystquarto to-quarto docs/

# Convert Quarto → MyST
quarto2myst docs/
mystquarto to-myst docs/
```

### Options

- `--output DIR` / `-o DIR`: Output directory (default: converts in-place)
- `--in-place`: Modify files in-place
- `--config-only`: Only convert config files (myst.yml ↔ _quarto.yml)
- `--no-config`: Skip config file conversion
- `--dry-run`: Show what would be changed without writing
- `--strict`: Treat warnings as errors
