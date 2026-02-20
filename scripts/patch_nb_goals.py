"""
Patch all three notebooks:
- Add a "Goals of this notebook" cell as the second cell (after the h1 title)
- Notebook 01: fix footer (remove zenodo download tip, fix notebook reference)
- Notebook 03: add goals cell
"""

import json
from pathlib import Path

NB_DIR = Path(__file__).resolve().parent.parent / "notebooks"


def load(name):
    p = NB_DIR / name
    nb = json.loads(p.read_text(encoding="utf-8"))
    return p, nb


def goals_cell(items: list[str]):
    lines = ["## 🎯 Goals of this notebook\n", "\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {item}\n")
    # strip trailing \n from last item
    lines[-1] = lines[-1].rstrip("\n")
    return {"cell_type": "markdown", "metadata": {}, "source": lines}


def insert_goals_after_title(cells, goals):
    """Insert goals cell as the second cell (after first markdown h1)."""
    for i, c in enumerate(cells):
        if c["cell_type"] == "markdown":
            src = "".join(c["source"])
            if src.startswith("# "):
                cells.insert(i + 1, goals_cell(goals))
                return
    cells.insert(0, goals_cell(goals))


# ── Notebook 01 ─────────────────────────────────────────────────────────────
p01, nb01 = load("01_quickstart.ipynb")

insert_goals_after_title(nb01["cells"], [
    "**Confirm data is available** — check that downloaded project ZIPs are present",
    "**Understand the directory layout** — data, cache, output, jsonzip directories",
    "**Browse available projects** — see what's downloaded locally vs. what exists on ORACC",
    "**Parse a project** — run the full pipeline on a real ORACC corpus",
    "**Explore tablets** — inspect transliterations, metadata, and sign-level Unicode cuneiform",
    "**See the reference data** — provenance, periods, sign list",
])

# Fix footer: remove the zenodo download tip, fix notebook reference
for c in nb01["cells"]:
    if c["cell_type"] == "markdown":
        src = c["source"]
        new_src = []
        for line in src:
            # Drop the zenodo download line
            if "Download from Zenodo" in line:
                continue
            # Fix wrong notebook reference
            if "02_configure_and_export" in line:
                line = line.replace("02_configure_and_export", "03_configure_and_export")
            new_src.append(line)
        c["source"] = new_src

p01.write_text(json.dumps(nb01, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"✅ Patched {p01.name} ({len(nb01['cells'])} cells)")


# ── Notebook 02 ─────────────────────────────────────────────────────────────
p02, nb02 = load("02_reference_data.ipynb")

# Only insert if not already there
sources = ["".join(c["source"]) for c in nb02["cells"] if c["cell_type"] == "markdown"]
if not any("Goals" in s for s in sources):
    insert_goals_after_title(nb02["cells"], [
        "**Understand what was collected** — overview of all bundled reference datasets",
        "**Browse the project catalogue** — 221 ORACC projects with metadata",
        "**Explore provenance data** — raw find-sport strings → cities → Pleiades coordinates",
        "**Explore period mappings** — historical period names → year ranges",
        "**Explore the sign list** — 8,900+ cuneiform sign readings",
        "**Explore POS tags & language codes** — ORACC annotation conventions",
    ])
    p02.write_text(json.dumps(nb02, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Patched {p02.name} ({len(nb02['cells'])} cells)")
else:
    print(f"⏭  {p02.name} already has goals cell — skipped")


# ── Notebook 03 ─────────────────────────────────────────────────────────────
p03, nb03 = load("03_configure_and_export.ipynb")

insert_goals_after_title(nb03["cells"], [
    "**Understand RunConfig options** — learn every toggle the parser exposes",
    "**Compare outputs** — see how dropping damaged signs or masking POS changes transliterations",
    "**Build a multi-project dataset** — parse several corpora and combine into one DataFrame",
    "**Export** — save combined data as JSONL and CSV for downstream use",
    "**Quick analysis** — explore the combined dataset by project, provenance, and period",
])

p03.write_text(json.dumps(nb03, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"✅ Patched {p03.name} ({len(nb03['cells'])} cells)")
