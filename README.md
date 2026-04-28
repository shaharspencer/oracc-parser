# oracc-parser

A Python tool to download and parse [ORACC](http://oracc.museum.upenn.edu/) cuneiform text projects into machine-learning-ready formats (JSONL, CSV, pandas DataFrames).

## Features

- **Download** — Fetch project ZIPs directly from ORACC or Zenodo
- **Parse** — Convert raw ORACC JSON into structured data
- **Export** — Save datasets as JSONL, CSV, or pandas DataFrames
- **Configure** — Control handling of broken signs and POS masking using `RunConfig`

## Installation


```bash
git clone https://github.com/shaharspencer/oracc-parser.git
cd oracc-parser
pip install -e ".[dev]"
```

## Getting Started — Notebooks

The easiest way to explore oracc-parser is through the interactive notebooks.
Start with notebook 01 — it downloads all the data you need from Zenodo automatically.

| Notebook | What you'll learn |
|---|---|
| [`01_quickstart.ipynb`](notebooks/01_quickstart.ipynb) | Download the dataset → parse a project from pre-processed CSVs → explore transliterations, translations, and metadata → export |
| [`02_reference_data.ipynb`](notebooks/02_reference_data.ipynb) | Browse all projects in the dataset, query catalogues, explore bundled reference data (provenance, periods, sign list, POS tags) |
| [`03_configure_and_export.ipynb`](notebooks/03_configure_and_export.ipynb) | All `RunConfig` options — word-level and sign-level break filtering, POS masking — combining multiple projects and exporting datasets |
| [`04_oracc_json_processing.ipynb`](notebooks/04_oracc_json_processing.ipynb) | Advanced: understand the raw ORACC JSON structure, the JSON → TabletRecord → CSV pipeline, and how to download and parse projects not in the dataset |

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
> are not necessarily aligned**. A word kept in the transliteration (because its
> average damage is below `max_break_fraction`) may still have individual signs
> dropped from the Unicode output if `drop_missing` / `drop_damaged` are enabled.

### Other options

| Parameter | Default | Description |
|---|---|---|
| `limit` | `None` | Only parse the first N texts (useful for testing) |
| `keep_word_segmentation` | `True` | Preserve word boundaries in Unicode cuneiform output |
| `mask_pos` | `[]` | Replace words of certain POS tags with the tag name |
| `languages` | `["Akkadian"]` | Which languages to include when downloading projects |
| `use_cache` | `True` | Use cached results if available |

All reference data is bundled with the package, so you don't need to configure external paths unless you are customizing `oracc_parser.settings`.

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
