import json

notebook_path = "g:/My Drive/GitHub/oracc-parser/notebooks/01_quickstart.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell['cell_type'] == 'code':
        source = "".join(cell.get('source', []))
        if "# Which ones have we already downloaded?" in source:
            new_source = [
                "# Which ones have we already downloaded?\n",
                "import os\n",
                "import csv\n",
                "from oracc_parser.settings import jsonzip_dir\n",
                "from oracc_parser.utils.paths import get_projects_metadata\n",
                "\n",
                "# Load projects with empty text folders so we can exclude them\n",
                "_meta = get_projects_metadata()\n",
                "_empty_projects = set(\n",
                "    _meta.loc[_meta['Is_Text_Folder_Empty'].str.lower() == 'yes', 'Project_Name']\n",
                ")\n",
                "\n",
                "# Check for downloaded ZIPs using configured path\n",
                "zip_dir = jsonzip_dir()\n",
                "print(zip_dir)\n",
                "if zip_dir.exists():\n",
                "    # Exclude the large Zenodo bundle ZIPs and projects with no texts\n",
                "    _zenodo_zips = {'oracc_jsonzip_all.zip', 'oracc_html_translations.zip', 'plaides_scraped_data.zip'}\n",
                "    project_zips = [\n",
                "        f for f in zip_dir.glob('*.zip')\n",
                "        if f.name not in _zenodo_zips\n",
                "        and f.stem.replace('-', '/') not in _empty_projects\n",
                "    ]\n",
                "    downloaded = sorted([f.stem for f in project_zips])\n",
                "    total_size_mb = sum(f.stat().st_size for f in project_zips) / (1024*1024)\n",
                "    print(f\"📦 {len(downloaded)} projects downloaded ({total_size_mb:.0f} MB total)\")\n",
                "    print()\n",
                "    # Show first 20\n",
                "    for i, name in enumerate(downloaded[:20]):\n",
                "        size_mb = (zip_dir / f\"{name}.zip\").stat().st_size / (1024*1024)\n",
                "        print(f\"   {name:40s}  {size_mb:6.1f} MB\")\n",
                "    if len(downloaded) > 20:\n",
                "        print(f\"   ... and {len(downloaded)-20} more\")\n",
                "else:\n",
                "    print(\"No downloaded projects found yet.\")\n",
                "    print(\"Run: python scripts/download_zenodo_data.py\")\n"
            ]
            cell['source'] = new_source
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook patched successfully.")
