"""
Patch 03_configure_and_export.ipynb to document max_break_fraction.

Changes:
  1. Expand the RunConfig options table with max_break_fraction.
  2. Replace the old "POS masking" section header with a two-part section:
     - 2a. Word-level vs sign-level break filtering (markdown explanation)
     - 2b. Live demo code cell
     - 2c. Renumbered "POS masking reference" as section 3.
  3. Renumber "Build a multi-project dataset" from ## 3 to ## 4.
  4. Renumber "Quick analysis" from ## 4 to ## 5.
"""

import json

NB_PATH = "g:/My Drive/GitHub/oracc-parser/notebooks/03_configure_and_export.ipynb"

with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb["cells"]
new_cells = []

for cell in cells:
    src = "".join(cell.get("source", []))

    # ── 1. Expand RunConfig options table ──────────────────────────────────
    if "## 1. RunConfig options" in src:
        cell["source"] = [
            "## 1. RunConfig options\n",
            "\n",
            "| Option | Default | What it does |\n",
            "|---|---|---|\n",
            "| `limit` | `None` | Only parse first N texts (good for testing) |\n",
            "| `max_break_fraction` | `1.0` | **Word-level**: fraction of broken signs tolerated before a word is replaced with `X` in transliteration / normalization / lemmatization |\n",
            "| `drop_missing` | `False` | **Sign-level**: remove signs marked `[x]` (completely broken) from **Unicode cuneiform output only** |\n",
            "| `drop_damaged` | `False` | **Sign-level**: remove signs marked `\u2e22x\u2e23` (partially damaged) from **Unicode cuneiform output only** |\n",
            "| `mask_pos` | `[]` | Replace words of certain POS with the tag name |\n",
            "| `languages` | `[\"Akkadian\"]` | Which languages to process |\n",
            "| `use_cache` | `True` | Use cached results if available |",
        ]
        new_cells.append(cell)
        continue

    # ── 2. Replace "## 2. POS masking reference" with three new cells ──────
    if "## 2. POS masking reference" in src:
        # 2a. Explanation markdown
        explanation_md = {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. Word-level vs sign-level break filtering\n",
                "\n",
                "`RunConfig` exposes **two independent levels** of break filtering that "
                "operate on different granularities and affect different outputs.\n",
                "\n",
                "### Word-level \u2014 `max_break_fraction` (0.0 \u2013 1.0)\n",
                "\n",
                "- Each word has a `break_perc`: the **fraction of its signs** that are "
                "broken or missing (averaged across all signs in the word).\n",
                "- Words whose `break_perc` **exceeds** `max_break_fraction` are replaced "
                "wholesale with `X`.\n",
                "- Affects \u2192 **transliteration**, **normalization**, **lemmatization**.\n",
                "- `1.0` (default) \u2192 keep all words regardless of damage.\n",
                "- `0.0` \u2192 replace any word that has even one broken sign.\n",
                "\n",
                "### Sign-level \u2014 `drop_missing` / `drop_damaged`\n",
                "\n",
                "- Operates **sign-by-sign**, not word-by-word.\n",
                "- `drop_missing=True` removes signs marked `[x]` (completely lost).\n",
                "- `drop_damaged=True` removes signs marked `\u2e22x\u2e23` (partially legible).\n",
                "- Affects \u2192 **Unicode cuneiform output only**.\n",
                "\n",
                "> \u26a0\ufe0f **The two levels are independent and produce results that may not align.**\n",
                "> A word kept intact in the transliteration (because its *average* damage is\n",
                "> below `max_break_fraction`) may still have individual signs stripped from\n",
                "> the Unicode cuneiform output by `drop_missing` / `drop_damaged`, and\n",
                "> vice-versa. Do not expect the text outputs and the Unicode cuneiform to\n",
                "> be aligned token-for-token when using these parameters.",
            ],
        }

        # 2b. Demo code cell
        demo_code = {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from oracc_parser import parse_project, RunConfig, get_transliterations, get_unicode_texts\n",
                "\n",
                "PROJECT = \"saao/saa01\"\n",
                "\n",
                "# Strict word-level filtering: words with >30% broken signs \u2192 replaced with X\n",
                "rec_strict = parse_project(PROJECT, config=RunConfig(limit=2, max_break_fraction=0.3))\n",
                "\n",
                "# Liberal (default): keep all words regardless of damage\n",
                "rec_liberal = parse_project(PROJECT, config=RunConfig(limit=2, max_break_fraction=1.0))\n",
                "\n",
                "print(\"=== Transliteration with max_break_fraction=0.3 (strict) ===\")\n",
                "for _, r in get_transliterations(rec_strict).iterrows():\n",
                "    print(f\"  {r['id']}:\")\n",
                "    print(f\"    {r['transliteration'][:120]}\")\n",
                "    print(f\"    tokens_without_broken: {r['tokens_without_broken']}/{r['total_tokens']}\")\n",
                "\n",
                "print()\n",
                "print(\"=== Transliteration with max_break_fraction=1.0 (liberal, default) ===\")\n",
                "for _, r in get_transliterations(rec_liberal).iterrows():\n",
                "    print(f\"  {r['id']}:\")\n",
                "    print(f\"    {r['transliteration'][:120]}\")\n",
                "    print(f\"    tokens_without_broken: {r['tokens_without_broken']}/{r['total_tokens']}\")\n",
                "\n",
                "print()\n",
                "print(\"=== Unicode cuneiform is unaffected by max_break_fraction ===\")\n",
                "print(\"(drop_missing / drop_damaged control sign-level filtering here)\")\n",
                "for _, r in get_unicode_texts(rec_strict).iterrows():\n",
                "    print(f\"  {r['id']}: {r['unicode'][:80]}\")",
            ],
        }

        # 2c. Renumbered POS masking section
        pos_md = {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. POS masking reference\n",
                "\n",
                "| Tag | Meaning |\n",
                "|---|---|\n",
                "| `PN` | Personal Name |\n",
                "| `DN` | Divine Name |\n",
                "| `GN` | Geographical Name |\n",
                "| `RN` | Royal Name |\n",
                "| `TN` | Temple Name |",
            ],
        }

        new_cells.extend([explanation_md, demo_code, pos_md])
        continue

    # ── 3. Renumber "## 3. Build a multi-project dataset" → ## 4 ──────────
    if "## 3. Build a multi-project dataset" in src:
        cell["source"] = [
            s.replace("## 3. Build a multi-project dataset", "## 4. Build a multi-project dataset")
            for s in cell["source"]
        ]
        new_cells.append(cell)
        continue

    # ── 4. Renumber "## 4. Quick analysis" → ## 5 ─────────────────────────
    if "## 4. Quick analysis" in src:
        cell["source"] = [
            s.replace("## 4. Quick analysis", "## 5. Quick analysis")
            for s in cell["source"]
        ]
        new_cells.append(cell)
        continue

    new_cells.append(cell)

nb["cells"] = new_cells

with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("✓ Notebook 03 patched successfully.")
