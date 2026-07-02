# oracc-parser

A Python tool to download and parse [ORACC](http://oracc.museum.upenn.edu/) cuneiform text projects into machine-learning-ready formats (JSONL, CSV, pandas DataFrames).

## Features

- **Download** — Fetch project ZIPs from preprocessed files on Zenodo or directly from ORACC
- **Parse** — Convert raw ORACC JSON / preprocessed CSVs into structured data and create machine-learning-ready text representations (in transliteration, normalization, lemmatization, or Unicode cuneiform) 
- **Configure** — Control handling of broken signs and POS masking
- **Export** — Save datasets as JSONL, CSV, or pandas DataFrames

## How to Cite

If you use oracc-parser in your research, please cite:

```bibtex
@software{romach_oracc_parser_2026,
  author       = {Romach, Avital and Spencer, Shahar and Gordin, Shai},
  title        = {oracc-parser: A Python toolkit for downloading and parsing ORACC cuneiform text projects},
  year         = {2026},
  publisher    = {Zenodo},
  version      = {0.1.4},
  doi          = {10.5281/zenodo.18643122},
  url          = {https://doi.org/10.5281/zenodo.18643122}
}
```

## Installation

```bash
pip install oracc-parser
```

Or for development:

```bash
git clone https://github.com/shaharspencer/oracc-parser.git
cd oracc-parser
pip install -e ".[dev]"
```

## Getting Started — Notebooks

The easiest way to explore oracc-parser is through the interactive notebooks, that go through the main functions.

| Notebook | What you'll learn | Open in Colab |
|---|---|---|
| [`01_quickstart.ipynb`](notebooks/01_quickstart.ipynb) | Download the dataset → parse a project → explore transliterations, translations, and metadata → export | <a href="https://colab.research.google.com/github/shaharspencer/oracc-parser/blob/main/notebooks/01_quickstart.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a> |
| [`02_configurations.ipynb`](notebooks/02_configurations.ipynb) | `RunConfig` options — word-level and sign-level break filtering, POS masking, combining multiple projects and exporting datasets | <a href="https://colab.research.google.com/github/shaharspencer/oracc-parser/blob/main/notebooks/02_configurations.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a> |
| [`03_translations.ipynb`](notebooks/03_translations.ipynb) | Where translations come from, how to download the translation cache from Zenodo, and how to enable translations in the parsing pipeline | <a href="https://colab.research.google.com/github/shaharspencer/oracc-parser/blob/main/notebooks/03_translations.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a> |
| [`04_reference_data.ipynb`](notebooks/04_reference_data.ipynb) | Browse all projects in the dataset, query catalogues, explore bundled reference data (provenance, periods, sign list, POS tags) | <a href="https://colab.research.google.com/github/shaharspencer/oracc-parser/blob/main/notebooks/04_reference_data.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a> |
| [`05_oracc_json_processing.ipynb`](notebooks/05_oracc_json_processing.ipynb) | Advanced: understand the raw ORACC JSON structure, the JSON → TabletRecord → CSV pipeline, and how to download and parse projects not in the dataset | <a href="https://colab.research.google.com/github/shaharspencer/oracc-parser/blob/main/notebooks/05_oracc_json_processing.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a> |

```bash
pip install oracc-parser[notebooks]
jupyter notebook notebooks/
```

## Quick Example

```python
from oracc_parser.download.fetch_data import fetch_data
from oracc_parser import parse_project, RunConfig, get_full_flat_table

# Step 1: download catalogues from Zenodo (run once)
fetch_data()

# Step 2: parse a project — word CSVs fetched from Zenodo on first call,
# read from disk on subsequent calls
records = parse_project("saao/saa01", config=RunConfig(limit=5))

# Get a flat DataFrame — no nesting, ready for analysis
df = get_full_flat_table(records)
df.to_json("dataset.jsonl", orient="records", lines=True)

# For a project not on Zenodo, download directly from ORACC servers:
records = parse_project("my/project", download_from_oracc_server=True)
```

## Configuration

You can customize the parsing process using `RunConfig`:

```python
from oracc_parser import parse_project, RunConfig

records = parse_project("saao/saa01", config=RunConfig(
    limit=10,
    max_break_fraction=0.5,   # word-level: drop words that are >50% broken
    drop_missing=True,        # sign-level: drop [x] signs from Unicode output
    drop_damaged=False,       # sign-level: keep ⸢x⸣ signs in Unicode output
    mask_pos=["PN", "DN"],    # replace personal/divine names with tag
))
```

### Two independent levels of break filtering

`RunConfig` provides two distinct ways to handle damaged or missing text,
operating at different granularities and affecting different outputs:

| Parameter | Level | Affects | How it works |
|---|---|---|---|
| `max_break_fraction` | **Word** | Transliteration, normalization, lemmatization | Each word has a `break_perc` (fraction of its signs that are broken). Words exceeding this threshold are replaced with `X`. Default `1.0` keeps all words. |
| `drop_missing` | **Sign** | Unicode cuneiform only | Drops individual signs marked `[x]` (completely lost). |
| `drop_damaged` | **Sign** | Unicode cuneiform only | Drops individual signs marked `⸢x⸣` (partially legible). |

> **Note:** Because word-level and sign-level filtering use different thresholds
> and different granularities, **the text outputs and the Unicode cuneiform output
> are not aligned**. A word kept in the transliteration (because its
> average damage is below `max_break_fraction`) may still have individual signs
> dropped from the Unicode output if `drop_missing` / `drop_damaged` are enabled.
> None of these filters affect the translations.

### Other options

| Parameter | Default | Description |
|---|---|---|
| `limit` | `None` | Only parse the first N texts (useful for testing) |
| `keep_word_segmentation` | `True` | Preserve word boundaries in Unicode cuneiform output |
| `mask_pos` | `[]` | Replace words of certain POS tags with the tag name |

All reference data is bundled with the package, so you don't need to configure external paths unless you are customizing `oracc_parser.settings`.

## CLI

```bash
oracc-parser download --project saao/saa01
oracc-parser parse --project saao/saa01 --limit 5 --format jsonl --output saa01.jsonl
```

## Heavy Data (Zenodo)

Large data files (ORACC ZIPs, word-level CSVs, cached translations, Pleiades data) are on Zenodo:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18643122.svg)](https://doi.org/10.5281/zenodo.18643122)

```bash
python scripts/download_zenodo_data.py
```

## Running Tests

```bash
pytest tests/ -v     # 98 tests
```

## License

MIT — see [LICENSE](LICENSE).

## Credits

Based on code by Niek Veldhuis ([Compass](https://github.com/niekveldhuis/compass)) and adapted for the BEn Project.
