"""
Rewrite notebook 02_reference_data.ipynb with:
- New framing: "What We Collected & Preprocessed"
- Clear explanations of what each dataset is (presaved, bundled, etc.)
- Fixed search bug (fillna('') instead of astype(str) with NaN float issue)
- Removed "What's on disk" section (covered in notebook 01)
- get_provenance() shows only rows with real Pleiades IDs by default
"""

import json
from pathlib import Path

NB_PATH = Path(__file__).resolve().parent.parent / "notebooks" / "02_reference_data.ipynb"


def cell(cell_type, source, outputs=None, execution_count=None):
    c = {"cell_type": cell_type, "metadata": {}, "source": source}
    if cell_type == "code":
        c["outputs"] = outputs or []
        c["execution_count"] = execution_count
    return c


def md(source):
    return cell("markdown", source)


def code(source):
    return cell("code", source)


cells = [
    # ── Header ──────────────────────────────────────────────────────────────
    md([
        "# 📚 What We Collected & Preprocessed\n",
        "\n",
        "This notebook documents all the **reference datasets** that ship with `oracc-parser`.\n",
        "These were curated, merged, and pre-saved so you never have to re-download or reprocess them.\n",
        "\n",
        "| Dataset | Source | How it's stored |\n",
        "|---|---|---|\n",
        "| **ORACC project catalogue** | Manually curated from ORACC + live API | Bundled CSV |\n",
        "| **Provenance (cities → Pleiades)** | ORACC raw fields + Pleiades API | Bundled CSV |\n",
        "| **Historical periods → year ranges** | Scholarly literature | Bundled CSV |\n",
        "| **Cuneiform sign readings** | ORACC sign lists (8,900+ entries) | Bundled CSV |\n",
        "| **POS tag meanings** | ORACC documentation | Bundled CSV |\n",
        "| **Language codes** | ORACC documentation | Bundled CSV |\n",
        "\n",
        "All datasets load instantly from inside the installed package — no internet needed.\n",
        "To explore downloading and parsing tablet texts, see **Notebook 01** (Quickstart).",
    ]),

    # ── Imports ──────────────────────────────────────────────────────────────
    code([
        "from oracc_parser import reference_data\n",
        "\n",
        "# All reference data is accessed through reference_data.*\n",
        "# These load from bundled CSVs inside the package — no download needed.",
    ]),

    # ── 1. Project catalogue ─────────────────────────────────────────────────
    md([
        "## 1. ORACC Project Catalogue\n",
        "\n",
        "We pre-saved metadata for **all known ORACC projects** — including project names,\n",
        "languages, URLs, and whether the project has parseable text content.\n",
        "\n",
        "> **Note:** This is a *static snapshot* bundled with the package.\n",
        "> For a live count from ORACC's servers, use `reference_data.get_live_project_list()` (Notebook 01).",
    ]),

    code([
        "projects = reference_data.get_projects_metadata()\n",
        "print(f\"🌍 {len(projects)} ORACC projects in the bundled catalogue\")\n",
        "display(projects.head(10))",
    ]),

    # ── search ───────────────────────────────────────────────────────────────
    code([
        "# Search for projects by keyword (searches all columns)\n",
        "SEARCH = \"saa\"\n",
        "\n",
        "# fillna('') handles missing values safely before joining\n",
        "mask = projects.apply(\n",
        "    lambda r: SEARCH.lower() in ' '.join(r.fillna('').astype(str)).lower(),\n",
        "    axis=1,\n",
        ")\n",
        "matches = projects[mask]\n",
        "print(f\"Found {len(matches)} projects matching '{SEARCH}':\")\n",
        "display(matches)",
    ]),

    # ── 2. Provenance ────────────────────────────────────────────────────────
    md([
        "## 2. Provenance — Tablet Find Spots\n",
        "\n",
        "ORACC tablets come with a raw `provenience` string (e.g. `\"Nineveh\"`, `\"Assur\"`).\n",
        "We pre-built a mapping from these raw strings to:\n",
        "- A **normalized city name**\n",
        "- A **[Pleiades](https://pleiades.stoa.org/) ID** and coordinates (lat/lon)\n",
        "\n",
        "This was built by:\n",
        "1. Collecting all unique provenience strings from ORACC\n",
        "2. Matching them to Pleiades gazeteer entries via API\n",
        "3. Hand-verifying ambiguous cases\n",
        "\n",
        "By default `get_provenance()` returns **only rows with a confirmed Pleiades ID**.\n",
        "This is also what the pipeline uses to attach coordinates to parsed tablets.",
    ]),

    code([
        "# By default: only rows with a confirmed numeric Pleiades ID\n",
        "prov = reference_data.get_provenance()\n",
        "print(f\"✅ {len(prov)} provenance mappings with confirmed Pleiades IDs\")\n",
        "display(prov.head(20))",
    ]),

    code([
        "# To see ALL mappings (including uncertain/unmatched):\n",
        "from oracc_parser.utils.paths import get_provenience\n",
        "prov_all = get_provenience(pleiades_only=False)\n",
        "print(f\"🗺️  Total provenance mappings: {len(prov_all)}\")\n",
        "print(f\"   With Pleiades ID:           {len(prov)} ({len(prov)/len(prov_all):.0%})\")\n",
        "print(f\"   Without Pleiades ID:        {len(prov_all) - len(prov)} (uncertain / unidentified)\")",
    ]),

    code([
        "# Cities with confirmed Pleiades IDs\n",
        "cities = prov['normalized_city'].dropna().unique()\n",
        "print(f\"{len(cities)} unique cities with Pleiades coordinates:\")\n",
        "for c in sorted(cities)[:30]:\n",
        "    print(f\"  {c}\")",
    ]),

    # ── 3. Historical periods ─────────────────────────────────────────────────
    md([
        "## 3. Historical Periods → Year Ranges\n",
        "\n",
        "ORACC text metadata includes period names like `\"Neo-Assyrian\"`, `\"Old Babylonian\"`, etc.\n",
        "We pre-saved a mapping from these period names to approximate year ranges.\n",
        "The pipeline uses this to add `start_year` / `end_year` to every parsed tablet.",
    ]),

    code([
        "periods = reference_data.get_period_mapping()\n",
        "print(f\"{len(periods)} historical periods\")\n",
        "display(periods)",
    ]),

    # ── 4. Sign list ──────────────────────────────────────────────────────────
    md([
        "## 4. Cuneiform Sign List (8,900+ readings)\n",
        "\n",
        "This table maps cuneiform sign names to their Unicode code points.\n",
        "The parser uses it to render transliterated text as actual cuneiform characters (𒀸, 𒈾, etc.).\n",
        "It was compiled from the ORACC sign list and merged with Unicode cuneiform block data.",
    ]),

    code([
        "signs = reference_data.get_sign_list()\n",
        "print(f\"{len(signs)} sign readings\")\n",
        "display(signs.head(20))",
    ]),

    code([
        "# Search for a sign reading\n",
        "SIGN_QUERY = \"lugal\"  # Try: \"an\", \"dingir\", \"sar\", \"gal\", \"ki\"\n",
        "\n",
        "mask = signs.apply(\n",
        "    lambda r: SIGN_QUERY.lower() in ' '.join(r.fillna('').astype(str)).lower(),\n",
        "    axis=1,\n",
        ")\n",
        "matches = signs[mask]\n",
        "print(f\"Found {len(matches)} readings for '{SIGN_QUERY}':\")\n",
        "display(matches)",
    ]),

    # ── 5. POS tags & languages ────────────────────────────────────────────────
    md([
        "## 5. POS Tags & Language Codes\n",
        "\n",
        "**POS tags** — ORACC uses a custom tagset (e.g. `PN` = Personal Name, `GN` = Geographical Name).\n",
        "We presaved a table linking each tag to its human-readable meaning.\n",
        "\n",
        "**Language codes** — ORACC texts are tagged with BCP-47-style language codes\n",
        "(e.g. `akk-x-neoass` = Neo-Assyrian Akkadian). This table documents what each code means.",
    ]),

    code([
        "pos = reference_data.get_pos_tags()\n",
        "print(f\"POS tags ({len(pos)}):\")\n",
        "display(pos)",
    ]),

    code([
        "langs = reference_data.get_languages()\n",
        "print(f\"Language codes ({len(langs)}):\")\n",
        "display(langs)",
    ]),

    # ── Footer ─────────────────────────────────────────────────────────────────
    md([
        "## What's next?\n",
        "\n",
        "- **Notebook 01 — Quickstart:** Parse a project, explore individual tablets\n",
        "- **Notebook 03 — Configure & Export:** Use `RunConfig` to mask POS tags, control output format, batch-export",
    ]),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.12.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4,
}

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"✅ Written {NB_PATH}")
print(f"   {len(cells)} cells")
