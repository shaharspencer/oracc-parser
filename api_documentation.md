# oracc-parser — API Documentation

## Package Structure

```
oracc_parser/
  __init__.py              # Public re-exports (the user-facing API)
  pipeline.py              # Main entry points and convenience functions
  settings.py              # Directory paths and runtime configuration
  cli.py                   # Command-line interface
  constants.py             # Shared sentinel values
  models/
    config.py              # RunConfig
    tablet.py              # All Pydantic data models (TabletRecord, Word, Sign, …)
  download/
    fetch_data.py          # Download from Zenodo; extract archives
    oracc_download.py      # Download raw ORACC JSON ZIPs from oracc.museum.upenn.edu
    extract_jsons.py       # Extract JSON text objects from ZIPs
    pleiades.py            # Pleiades geographical ID lookup
  parsing/
    parse_content.py       # CDL tree traversal → TabletContent
    parse_words.py         # Word-node parsing; POS and language normalisation
    parse_signs.py         # Sign-level parsing; breakage tracking
    text_builder.py        # Words → transliteration/normalisation/lemmatisation strings
    translation.py         # Fetch and cache English translations from ORACC HTML
  metadata/
    populate.py            # Catalogue dict → TabletMetadata (provenance, period, …)
    archive.py             # Archive name normalisation
  io/
    word_csv.py            # Serialize/deserialize TabletRecord ↔ per-word CSV
  export/
    to_jsonl.py            # Export records to JSONL or CSV
  utils/
    paths.py               # Load bundled reference CSVs
    logger.py              # Shared logger
    unicode.py             # Sign-reading → Unicode cuneiform conversion
  enriched_data/           # Bundled reference CSVs (shipped with the package)
    provenience.csv
    period_mapping.csv
    sign_readings.csv
    pos_tags.csv
    languages.csv
    projects_metadata.csv
    raw_archive_values.csv
    state_supergroup_mapping.csv
    grouped_oracc_metadata_columns.csv
```

---

## Settings (`oracc_parser.settings`)

Controls where data is read from and written to. All paths are globals and can be overridden at runtime:

```python
import oracc_parser.settings as settings
from pathlib import Path
settings.DATA_DIR = Path("/my/data/dir")
```

Or via environment variable before importing the package:

```
ORACC_DATA_DIR=/my/data/dir python my_script.py
```

### Directory globals

| Variable | Default | Purpose |
|---|---|---|
| `DATA_DIR` | `./oracc_data/` | Root data directory |
| `OUTPUT_DIR` | `DATA_DIR/output/` | Exported CSVs and JSONL files |
| `TRANSLATIONS_DIR` | `DATA_DIR/translations/` | Cached HTML translation pages |
| `JSONZIP_DIR` | `DATA_DIR/jsonzip/` | Raw ORACC JSON ZIPs |
| `WORD_CSV_DIR` | `DATA_DIR/oracc_csvs/` | Per-word CSV files |
| `CATALOGUE_DIR` | `DATA_DIR/catalogues/` | Project catalogue CSVs |
| `ZENODO_RECORD_URL` | `https://zenodo.org/records/20625379` | Zenodo record for pre-processed data |
| `LOG_LEVEL` | `"INFO"` | Logging verbosity |

### Accessor functions

Each global has a corresponding function that always returns the current value, so runtime overrides take effect everywhere:

- `data_dir() → Path`
- `output_dir() → Path`
- `translations_dir() → Path`
- `jsonzip_dir() → Path`
- `word_csv_dir() → Path`
- `catalogue_dir() → Path`
- `zenodo_url() → str`
- `log_level() → str`
- `pleiades_zip_path() → Path | None`
- `get_settings() → dict` — returns all current settings as a plain dict

---

## Configuration (`oracc_parser.models.config`)

### `RunConfig`

Pydantic model controlling parsing behaviour. All fields are optional with sensible defaults.

```python
from oracc_parser import RunConfig
config = RunConfig(drop_missing=True, mask_pos=["PN", "DN"], limit=10)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `drop_missing` | `bool` | `False` | Drop signs marked `[x]` (completely lost) from **Unicode cuneiform output only**. Does not affect transliteration/normalisation/lemmatisation. |
| `drop_damaged` | `bool` | `False` | Drop signs marked `⸢x⸣` (partially damaged) from **Unicode cuneiform output only**. |
| `keep_word_segmentation` | `bool` | `True` | Preserve word boundaries in **Unicode cuneiform output**. |
| `max_break_fraction` | `float` | `1.0` | **Word-level** filter. Words whose fraction of broken signs exceeds this threshold are replaced with `X` in transliteration/normalisation/lemmatisation. `0.0` = exclude any word with even one broken sign; `1.0` = keep all words. |
| `mask_pos` | `list[str]` | `[]` | POS tags whose lemma forms are replaced with the tag name. Valid values: `PN`, `DN`, `GN`, `MN`, `RN`, `SN`, `N`, `V`, `AJ`, and others from the bundled POS table. |
| `fetch_translations` | `bool` | `False` | Fetch English translations from ORACC (or read from `TRANSLATIONS_DIR` if cached). Requires network access or a pre-downloaded translation cache. |
| `limit` | `int \| None` | `None` | Parse only the first N texts. `None` = parse all. |

---

## Data Models (`oracc_parser.models.tablet`)

All models are Pydantic v2 `BaseModel` subclasses. Fields default to empty/`None` when absent from the source data.

### `TabletRecord`

Top-level container. Every parsed tablet is one `TabletRecord`.

| Field | Type | Description |
|---|---|---|
| `metadata` | `TabletMetadata` | Information from the ORACC catalogues: ID number, where it was found, when, what genre, etc. |
| `content` | `TabletContent` | Words, string representations, translation. |

---

### `TabletMetadata`

| Field | Type | Description |
|---|---|---|
| `identifier` | `str` | Globally unique ID, e.g. `"saao/saa01_P334189"` |
| `project` | `str \| None` | ORACC project path, e.g. `"saao/saa01"` |
| `id_text` | `str \| None` | P-number or text ID, e.g. `"P334189"` |
| `metadata_raw_dict` | `dict \| None` | Raw catalogue fields as downloaded from ORACC |
| `geographical_information` | `TabletGeographicalInformation` | Provenance |
| `chronological_information` | `TabletChronologicalInformation` | Period and year range |
| `archive` | `str \| None` | Archive name (e.g. `"Šamaš-šumu-ukīn Archive"`) |
| `copyright_information` | `str` | Raw copyright statement from ORACC |
| `genre` | `str \| None` | Text genre (e.g. `"Administrative Letter"`) |
| `accession_museum_publication_numbers` | `str` | Accession numbers, museum numbers, and primary publication references merged from catalogue |
| `secondary_literature` | `str` | Secondary literature references, including journal title/volume |
| `credits` | `str` | Credits and acknowledgements for ORACC project |
| `cite_as` | `str` | Recommended citation string (falls back to ORACC URL if not in catalogue) |

### `TabletGeographicalInformation`

| Field | Type | Description |
|---|---|---|
| `state_supergroup` | `str` | Empire/state grouping (e.g. `"Neo-Assyrian Empire"`) |
| `city` | `City` | Findspot with optional Pleiades ID |
| `sender_city` | `str \| None` | Sender's city for letters |

### `City`

| Field | Type | Description |
|---|---|---|
| `city_name` | `str` | Normalised city name (e.g. `"Nineveh"`) |
| `city_plaides_id` | `str` | Pleiades URI for the city |

### `TabletChronologicalInformation`

| Field | Type | Description |
|---|---|---|
| `tablet_period` | `TabletPeriod` | Named period with approximate year range |
| `start_year` | `int \| None` | Start year (negative = BCE) |
| `end_year` | `int \| None` | End year (negative = BCE) |
| `years_source` | `str \| None` | How the dates were derived |

### `TabletPeriod`

| Field | Type | Description |
|---|---|---|
| `period_name` | `str \| None` | e.g. `"Neo-Assyrian"` |
| `period_start_year` | `int \| None` | Period start year |
| `period_end_year` | `int \| None` | Period end year |

---

### `TabletContent`

| Field | Type | Description |
|---|---|---|
| `words` | `list[Word]` | All parsed words in reading order |
| `english_translation` | `str` | Full (English) translation (empty string if not fetched) |
| `transliterated_str_representation` | `TextStringRepresentation \| None` | Transliteration string + token counts |
| `normalized_str_representation` | `TextStringRepresentation \| None` | Normalisation string + token counts |
| `lemmatized_str_representation` | `TextStringRepresentation \| None` | Lemmatisation string + token counts |
| `unicode_str_representation` | `UnicodeStringRepresentation \| None` | Unicode cuneiform + character counts |

### `TextStringRepresentation`

| Field | Type | Description |
|---|---|---|
| `text` | `str \| None` | The full text string |
| `total_tokens` | `int` | Number of words |
| `tokens_without_broken` | `int` | Words with no breakage |
| `max_break_fraction_used` | `float` | The `max_break_fraction` applied |

### `UnicodeStringRepresentation`

| Field | Type | Description |
|---|---|---|
| `text` | `str` | Unicode cuneiform string |
| `total_chars` | `int` | Total signs |
| `included_chars` | `int` | Signs not dropped by `drop_missing`/`drop_damaged` |
| `dropped_missing_signs` | `bool \| None` | Whether `drop_missing` was applied |
| `dropped_damaged_signs` | `bool \| None` | Whether `drop_damaged` was applied |

---

### `Word`

Represents one word token parsed from the CDL tree.

| Field | Type | Description |
|---|---|---|
| `frag` | `str \| None` | Transliteration fragment, e.g. `"{m}da-ri-ia-muš"` |
| `ref` | `str \| None` | Reference ID, e.g. `"P527140.2.1"` |
| `inst` | `str \| None` | Combined `norm`, `sense`, and `raw_pos`, e.g. `"kunuk[seal]N"` |
| `form` | `str \| None` | Form without broken signs |
| `lemma_form` | `str \| None` | Dictionary lemma, e.g. `"kunukku"` |
| `sense` | `str \| None` | Sense/meaning, e.g. `"seal"` |
| `norm` | `str \| None` | Normalised form, e.g. `"kunuk"` |
| `raw_pos` | `str \| None` | Raw POS tag from ORACC, e.g. `"N"` |
| `lang` | `str \| None` | Language code, e.g. `"akk-x-neoass"` |
| `line` | `int \| None` | Line number in the text |
| `sign_dictionaries` | `WordSigns \| None` | Sign-level data |
| `normalized_pos` | `WordPOSInfo \| None` | Normalised POS information |
| `normalized_language` | `Language \| None` | Normalised language tag |

### `WordSigns`

| Field | Type | Description |
|---|---|---|
| `reading` | `str` | The word's transliteration |
| `break_percentage` | `float` | Fraction of broken signs (`-1` = not computed) |
| `signs` | `list[Sign]` | Individual signs |

### `Sign`

| Field | Type | Description |
|---|---|---|
| `role` | `str` | `"logographic"`, `"phonetic"`, or `"determinative"` |
| `meaning` | `str` | Sign meaning |
| `breakage` | `str` | `"complete"`, `"missing"`, or `"damaged"` |
| `unicode_version` | `str` | Unicode cuneiform character(s) for this sign |
| `optional_delim` | `str \| None` | Delimiter after this sign |

### `WordPOSInfo`

| Field | Type | Description |
|---|---|---|
| `normalized_pos` | `str` | Normalised POS label |
| `meaning` | `str` | Human-readable meaning |
| `to_mask` | `bool` | Whether this POS is masked in the current config |
| `mask_as` | `str` | The mask token used if `to_mask` is True |

### `Language`

| Field | Type | Description |
|---|---|---|
| `is_cuneiform` | `bool` | Whether written in cuneiform |
| `normalized_language` | `str \| None` | One of: `Sumerian`, `Akkadian`, `Hittite`, `Elamite`, `Hurrian`, `Urartian`, `Persian`, `Ugaritic`, `Aramaic`, `Canaanite`, `Greek`, `Egyptian`, `Proto-cuneiform`, `Proto-Elamite`, `Numbers`, `Unclear`, `Assyrian Hieroglyphs` |
| `dialect` | `str` | Dialect string, e.g. `"Neo-Assyrian"` |

---

## Pipeline (`oracc_parser.pipeline`)

The main user-facing module. All functions below are also importable directly from `oracc_parser`.

---

### Parsing

#### `parse_project(project, config=None, download_from_oracc_server=False) → list[TabletRecord]`

Parse tablets of an ORACC project.

**Priority order:**
1. If word CSVs are already on disk in `WORD_CSV_DIR` → reads from disk (fast, no network)
2. If not on disk and `download_from_oracc_server=False` (default) → downloads word CSVs from Zenodo and saves to disk
3. If not on disk and `download_from_oracc_server=True` → downloads raw JSON ZIP from ORACC live servers, parses, and saves word CSVs to disk

Run `fetch_data()` first to download catalogues from Zenodo, which are required for metadata fields (provenance, period, genre, etc.).

Use `download_from_oracc_server=True` only for projects not included in the Zenodo dataset.

**Parameters:**
- `project` (`str`) — ORACC project path, e.g. `"saao/saa01"` or `"babcity"`.
- `config` (`RunConfig | None`) — Parsing options. Uses defaults if `None`.
- `download_from_oracc_server` (`bool`) — If `True`, download from ORACC live servers instead of Zenodo when word CSVs are not on disk. Default `False`.

**Returns:** `list[TabletRecord]`

---

### Flat DataFrame extractors

All functions below take `list[TabletRecord]` and return a flat `pd.DataFrame` with one row per tablet.

#### `get_metadata_table(records) → pd.DataFrame`

Columns: `id`, `project`, `text_id`, `genre`, `archive`, `provenance`, `pleiades_id`, `state_supergroup`, `period`, `start_year`, `end_year`, `accession_museum_publication_numbers`, `secondary_literature`, `credits`, `cite_as`.

#### `get_transliterations(records) → pd.DataFrame`

Columns: `id`, `project`, `transliteration`, `total_tokens`, `tokens_without_broken`.

#### `get_normalizations(records) → pd.DataFrame`

Columns: `id`, `project`, `normalization`, `total_tokens`, `tokens_without_broken`.

#### `get_lemmatizations(records) → pd.DataFrame`

Columns: `id`, `project`, `lemmatization`, `total_tokens`, `tokens_without_broken`.

#### `get_unicode_texts(records) → pd.DataFrame`

Columns: `id`, `project`, `unicode`, `total_chars`, `included_chars`.

#### `get_translations(records) → pd.DataFrame`

Columns: `id`, `project`, `translation`.

#### `get_full_flat_table(records) → pd.DataFrame`

All columns from `get_metadata_table` plus: `transliteration`, `normalization`, `lemmatization`, `unicode`, `translation`, `total_tokens`, `tokens_without_broken`. Ideal for releasing as a dataset.

---

### Export

#### `export_to_jsonl(records, output_path) → Path`

Export records to a JSONL file (one JSON object per line). Returns the output `Path`.

#### `export_to_csv(records, output_path) → Path`

Export records to a flat CSV file. Returns the output `Path`.

---

### Word CSV helpers

#### `records_to_word_dataframes(records) → dict[str, pd.DataFrame]`

Convert a list of `TabletRecord` objects to per-word DataFrames keyed by `text_id`. Use this to prepare data for saving with `save_word_csv`.

---

### Catalogue helpers

#### `save_project_catalogue(project, path=None) → Path`

Extract the ORACC catalogue for a project from its ZIP and save it as a CSV. Saved to `CATALOGUE_DIR/{project_slug}.csv` by default.

**Parameters:**
- `project` (`str`) — ORACC project path.
- `path` (`Path | None`) — Override output path.

#### `load_project_catalogue(path) → pd.DataFrame`

Load a catalogue CSV previously saved by `save_project_catalogue`.

---

### Reference data (`reference_data`)

A namespace class providing access to all bundled reference CSVs. No download required — these ship with the package.

```python
from oracc_parser import reference_data
df = reference_data.get_provenance()
```

| Method | Returns | Description |
|---|---|---|
| `get_provenance()` | `pd.DataFrame` | City names → Pleiades IDs and normalised city names |
| `get_period_mapping()` | `pd.DataFrame` | Historical period names → approximate year ranges |
| `get_sign_list()` | `pd.DataFrame` | 8,900+ cuneiform sign readings and Unicode values |
| `get_pos_tags()` | `pd.DataFrame` | All POS tags with descriptions |
| `get_languages()` | `pd.DataFrame` | All language codes with normalised names |
| `get_projects_metadata()` | `pd.DataFrame` | ORACC project list with umbrella groupings and text counts |
| `get_state_supergroup_mapping()` | `pd.DataFrame` | Project → state/empire supergroup mapping |
| `get_archive_mapping()` | `pd.DataFrame` | Raw archive strings → normalised archive names |
| `get_catalogue_columns()` | `pd.DataFrame` | Grouped ORACC metadata column reference table |
| `get_live_project_list()` | `pd.DataFrame` | Live list of all public ORACC projects (fetches from ORACC servers) |

---

## Word CSV I/O (`oracc_parser.io.word_csv`)

Functions for serialising and deserialising `TabletRecord` objects as per-word CSVs.

### CSV schema

Each CSV stores one row per word with columns:

`text_id`, `project`, `word_index`, `frag`, `ref`, `inst`, `form`, `lemma_form`, `sense`, `norm`, `raw_pos`, `lang`, `line`, `signs_reading`, `signs_break_pct`, `unicode`, `break_info`

Normalised fields (POS, language) and string representations are not stored — they are re-derived from the raw fields at load time.

---

#### `save_word_csv(df, path=None) → Path`

Write a per-word DataFrame to disk. If `path` is omitted, saves to `WORD_CSV_DIR/{project_slug}/{text_id}.csv`.

#### `load_word_csv(path) → pd.DataFrame`

Load a single per-word CSV from disk.

#### `record_to_word_dataframe(record) → pd.DataFrame`

Serialise a `TabletRecord` into a per-word DataFrame.

#### `word_dataframe_to_record(df, config, catalogue_row=None) → TabletRecord`

Reconstruct a `TabletRecord` from a per-word DataFrame, applying `config`. Normalised POS and language fields are re-derived from the raw values. String representations are rebuilt according to `config`.

---

## Download (`oracc_parser.download`)

### `fetch_data` (`oracc_parser.download.fetch_data`)

#### `fetch_data(url=None, dest=None, include_translations=False, include_json_zips=False)`

Download pre-processed ORACC data from Zenodo and extract it.

Downloads `catalogues.zip` from Zenodo (required for metadata fields such as provenance, period, and genre). Must be run before `parse_project()` if you want populated metadata. Word CSVs are **not** downloaded by `fetch_data` — they are fetched lazily by `parse_project()` on first access per project.

**Parameters:**
- `url` (`str | None`) — Zenodo record URL. Defaults to `ZENODO_RECORD_URL`.
- `dest` (`Path | None`) — Directory for temporary download files. Defaults to `DATA_DIR`.
- `include_translations` (`bool`) — Also download `oracc_html_translations.zip` (~130 MB). Required for offline translation access.
- `include_json_zips` (`bool`) — Also download `oracc_jsonzip_all.zip`. Not normally needed — `parse_project(download_from_oracc_server=True)` downloads individual project ZIPs on demand.

### `oracc_download` (`oracc_parser.download.oracc_download`)

#### `download_zip(project, output_dir=None) → Path | None`

Download a single project's JSON ZIP from `oracc.museum.upenn.edu`. Skips if already downloaded. Returns the ZIP path, or `None` on failure.


#### `get_live_projects_dataframe() → pd.DataFrame`

Fetch the live list of all public ORACC projects from the ORACC servers. Requires network access.

---

## Metadata (`oracc_parser.metadata.populate`)

### `enrich_catalogue_df(df) → pd.DataFrame`

Take a raw catalogue DataFrame (as loaded from a catalogue CSV) and add normalised provenance, period, state supergroup, archive, and year columns. Useful for analysing metadata without doing a full parse.

**Parameters:**
- `df` (`pd.DataFrame`) — Raw catalogue DataFrame with an ORACC `project` column.

**Returns:** DataFrame with added columns: `provenance`, `pleiades_id`, `state_supergroup`, `period`, `start_year`, `end_year`, `archive`.

---

## CLI

```
oracc-parser <command> [options]
```

| Command | Description |
|---|---|
| `fetch-data` | Download catalogues (and optionally translations/ZIPs) from Zenodo |
| `download --project <path>` | Download a single project ZIP from the ORACC servers |
| `parse --project <path>` | Parse a project and export results |
| `info` | Show a summary of all bundled reference data |

### `parse` options

| Flag | Description |
|---|---|
| `--format jsonl\|csv` | Output format (default: `jsonl`) |
| `--output <path>` | Output file path (default: `output.jsonl`) |
| `--limit <n>` | Parse only first N texts |
| `--drop-missing` | Drop `[x]` signs from Unicode output |
| `--drop-damaged` | Drop `⸢x⸣` signs from Unicode output |
| `--max-break-fraction <float>` | Word-level break filter (default: `1.0` = keep all words) |
| `--mask-pos <tags>` | Space-separated POS tags to mask (e.g. `PN DN`) |
| `--fetch-translations` | Fetch (English) translations (from cache or ORACC live) |
| `--from-oracc` | Download from ORACC live servers instead of Zenodo when word CSVs are not on disk |

---

## Translations (`oracc_parser.parsing.translation`)

### `get_translation(project, text_id) → str`

Fetch the (English) translation for a tablet. Reads from `TRANSLATIONS_DIR/{project}/{text_id}.html` if cached; otherwise downloads from `oracc.museum.upenn.edu` and caches the result.

**Parameters:**
- `project` (`str`) — ORACC project path.
- `text_id` (`str`) — P-number or other text ID.

**Returns:** Multi-line translation string, or empty string on failure.

To use translations in the parsing pipeline, set `fetch_translations=True` in `RunConfig`. To pre-download the full translation cache (~130 MB, ~23,000 pages), use `fetch_data(include_translations=True)`.
