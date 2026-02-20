# oracc-parser

A Python tool to download and parse [ORACC](http://oracc.museum.upenn.edu/) cuneiform text projects into machine-learning-ready formats (JSONL, CSV, pandas DataFrames).

## Features

- **Download** — Fetch project ZIPs directly from ORACC or Zenodo
- **Parse** — Convert raw ORACC JSON into structured data
- **Export** — Save datasets as JSONL, CSV, or pandas DataFrames
- **Configure** — Control handling of broken signs and POS masking via `.env`
- **Reference Data** — Bundled provenance, sign lists, period mappings, and more

## Installation

```bash
pip install oracc-parser
```

Or install from source:

```bash
git clone https://github.com/shaharspencer/oracc-parser.git
cd oracc-parser
pip install -e ".[dev]"
```

## Getting Started — Notebooks

The easiest way to explore oracc-parser is through the interactive notebooks:

| Notebook | What you'll learn |
|---|---|
| [`01_quickstart.ipynb`](notebooks/01_quickstart.ipynb) | Parse a project → explore transliterations, translations, metadata → export |
| [`02_reference_data.ipynb`](notebooks/02_reference_data.ipynb) | Browse 221+ ORACC projects, provenance data, sign list, period mappings |
| [`03_configure_and_export.ipynb`](notebooks/03_configure_and_export.ipynb) | RunConfig options, POS masking, combining projects, exporting datasets |

```bash
pip install oracc-parser[notebooks]
jupyter notebook notebooks/
```

## Quick Example

```python
from oracc_parser import parse_project, RunConfig, get_full_flat_table

# Parse 5 tablets from SAA 01 (Neo-Assyrian royal letters)
records = parse_project("saao/saa01", config=RunConfig(limit=5))

# Get a flat DataFrame — no nesting, ready for analysis
df = get_full_flat_table(records)
df.to_json("dataset.jsonl", orient="records", lines=True)
```

## Setup (.env)

Copy the example file and set your preferences:

```bash
cp .env.example .env
```

Key settings:
- `ORACC_ZENODO_RECORD_URL` — Zenodo record for pre-downloaded data
- `ORACC_DATA_DIR` — where downloaded data lives
- `ORACC_LOG_LEVEL` — `DEBUG`, `INFO`, `WARNING`, or `ERROR`

## CLI

```bash
oracc-parser download --project saao/saa01
oracc-parser parse --project saao/saa01 --limit 5 --format jsonl --output saa01.jsonl
```

## Heavy Data (Zenodo)

Large data files (ORACC ZIPs, cached translations, Pleiades data) are on Zenodo:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18643122.svg)](https://doi.org/10.5281/zenodo.18643122)

```bash
python scripts/download_zenodo_data.py
```

## Running Tests

```bash
pytest tests/ -v     # 98 tests
```

## Known Limitations

- **Chronology**: Period-to-year normalization is optimized for the **1st Millennium BCE**.
- **Language**: Parsing is primarily validated on **Akkadian** projects.

## License

MIT — see [LICENSE](LICENSE).

## Credits

Based on code by Niek Veldhuis ([Compass](https://github.com/niekveldhuis/compass)) and adapted for the BEn Project.
