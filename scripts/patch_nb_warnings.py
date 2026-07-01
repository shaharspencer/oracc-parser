"""
Patch notebooks:
1. Add project availability check to 01_quickstart.ipynb
2. Update caching tip in 01_quickstart.ipynb
3. Add project availability check to 03_configure_and_export.ipynb
"""

import json
from pathlib import Path

NB_DIR = Path(__file__).resolve().parent.parent / "notebooks"


def patch_01():
    nb_path = NB_DIR / "01_quickstart.ipynb"
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = nb["cells"]

    # Find the parse_project code cell
    for i, cell in enumerate(cells):
        if cell["cell_type"] == "code" and any("parse_project" in l and "PROJECT" in l
                                                for l in cell.get("source", [])):
            # Only replace if it's the main parse cell (with PROJECT = ...)
            src = "".join(cell.get("source", []))
            if 'PROJECT = "saao/saa01"' in src or "PROJECT = " in src:
                cell["source"] = [
                    "from oracc_parser import parse_project, RunConfig\n",
                    "from oracc_parser.settings import jsonzip_dir\n",
                    "\n",
                    "# Change this to any project you want!\n",
                    "PROJECT = \"saao/saa01\"  \n",
                    "LIMIT = 5  # Set to None to parse everything\n",
                    "\n",
                    "# Check that the project is available locally\n",
                    "zip_dir = jsonzip_dir()\n",
                    "zip_name = PROJECT.replace('/', '-') + '.zip'\n",
                    "if not (zip_dir / zip_name).exists():\n",
                    "    available = sorted(f.stem.replace('-', '/') for f in zip_dir.glob('*.zip'))\n",
                    "    print(f\"⚠️  Project '{PROJECT}' is not downloaded!\")\n",
                    "    print(f\"   Available projects ({len(available)} total): {available[:10]}...\")\n",
                    "    print(f\"   To download: oracc-parser download --project {PROJECT}\")\n",
                    "else:\n",
                    "    config = RunConfig(limit=LIMIT)\n",
                    "    records = parse_project(PROJECT, config=config)\n",
                    "    print(f\"✓ Parsed {len(records)} tablets from {PROJECT}\")",
                ]
                cell["outputs"] = []
                cell["execution_count"] = None
                break

    # Update caching tip
    for i, cell in enumerate(cells):
        if cell["cell_type"] == "markdown" and any("Caching" in l for l in cell.get("source", [])):
            cell["source"] = [
                "> **💡 Caching:** The first `parse_project()` call parses everything (slow).\n",
                "> Subsequent calls with the **same config** return instantly from cache.\n",
                "> Switching configs (e.g. `mask_pos`, `drop_missing`) reuses the cached words\n",
                "> and only rebuilds the string representations — still much faster than re-parsing.\n",
                "> See **Notebook 03** for details, or use `RunConfig(use_cache=False)` to force re-parsing."
            ]
            break

    nb_path.write_text(json.dumps(nb, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Patched {nb_path.name}")


def patch_03():
    nb_path = NB_DIR / "03_configure_and_export.ipynb"
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = nb["cells"]

    # Find multi-project parse cell (with PROJECTS = [...])
    for i, cell in enumerate(cells):
        if cell["cell_type"] != "code":
            continue
        src = "".join(cell.get("source", []))
        if "PROJECTS = [" in src and "parse_project" in src:
            cell["source"] = [
                "from oracc_parser.settings import jsonzip_dir\n",
                "\n",
                "# Parse a few projects and combine\n",
                "PROJECTS = [\"saao/saa01\", \"saao/saa05\"]  # change these to what you want\n",
                "config = RunConfig(limit=3)  # small limit for demo — remove for full parse\n",
                "\n",
                "# Check project availability first\n",
                "zip_dir = jsonzip_dir()\n",
                "for project in PROJECTS:\n",
                "    zip_name = project.replace('/', '-') + '.zip'\n",
                "    if not (zip_dir / zip_name).exists():\n",
                "        print(f\"⚠️  Project '{project}' is not downloaded!\")\n",
                "        print(f\"   Run: oracc-parser download --project {project}\")\n",
                "\n",
                "all_dfs = []\n",
                "for project in PROJECTS:\n",
                "    print(f\"Parsing {project}...\")\n",
                "    try:\n",
                "        records = parse_project(project, config=config)\n",
                "        df = get_full_flat_table(records)\n",
                "        all_dfs.append(df)\n",
                "        print(f\"  → {len(records)} tablets\")\n",
                "    except Exception as e:\n",
                "        print(f\"  → Error: {e}\")\n",
                "\n",
                "combined = pd.concat(all_dfs, ignore_index=True)\n",
                "print(f\"\\n✓ Combined: {len(combined)} tablets from {len(PROJECTS)} projects\")\n",
                "display(combined)",
            ]
            cell["outputs"] = []
            cell["execution_count"] = None
            break

    nb_path.write_text(json.dumps(nb, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Patched {nb_path.name}")


if __name__ == "__main__":
    patch_01()
    patch_03()
