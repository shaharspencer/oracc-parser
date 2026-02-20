import nbformat
from pathlib import Path

nb_path = Path("notebooks/01_quickstart.ipynb")
nb = nbformat.read(nb_path, as_version=4)

print(f"Updating {nb_path}...")

# Cell 5: Check if data exists (uses data_dir / "jsonzip")
cell5_source = """import os
from pathlib import Path
from oracc_parser.settings import jsonzip_dir

# Check if data exists
zip_dir = jsonzip_dir()
if not zip_dir.exists() or len(list(zip_dir.glob("*.zip"))) == 0:
    print("⬇️  Data missing. Downloading from Zenodo... (this may take a minute)")
    # Run the download script (works in Jupyter)
    %run ../scripts/download_zenodo_data.py
else:
    print(f"✅ Data found in {zip_dir} ({len(list(zip_dir.glob('*.zip')))} projects)")"""

nb.cells[2]["source"] = cell5_source
print("Updated Cell 5 (Check data existence).")

# Cell 6: Directory layout info
cell6_source = """from pathlib import Path
from oracc_parser import reference_data
from oracc_parser.settings import data_dir, output_dir, cache_dir, jsonzip_dir

# What directories does oracc-parser use?
print("📁 Directory layout:")
print(f"   Data dir:    {data_dir()}")
print(f"   JSON ZIPs:   {jsonzip_dir()}")
print(f"   Output dir:  {output_dir()}")
print(f"   Cache dir:   {cache_dir()}")
print()
print("   (These are configurable in .env — see .env.example)")"""

nb.cells[4]["source"] = cell6_source
print("Updated Cell 6 (Directory layout info).")

# Cell 8: Which ones have we already downloaded?
cell8_source = """# Which ones have we already downloaded?
import os
from oracc_parser.settings import jsonzip_dir

# Check for downloaded ZIPs using configured path
zip_dir = jsonzip_dir()

if zip_dir.exists():
    downloaded = sorted([f.stem for f in zip_dir.glob("*.zip")])
    total_size_mb = sum(f.stat().st_size for f in zip_dir.glob("*.zip")) / (1024*1024)
    print(f"📦 {len(downloaded)} projects downloaded ({total_size_mb:.0f} MB total)")
    print()
    # Show first 20
    for i, name in enumerate(downloaded[:20]):
        size_mb = (zip_dir / f"{name}.zip").stat().st_size / (1024*1024)
        print(f"   {name:40s}  {size_mb:6.1f} MB")
    if len(downloaded) > 20:
        print(f"   ... and {len(downloaded)-20} more")
else:
    print("No downloaded projects found yet.")
    print("Run: oracc-parser download --project saao/saa01")"""

nb.cells[7]["source"] = cell8_source
print("Updated Cell 8 (Downloaded projects list).")

nbformat.write(nb, nb_path)
print("✅ Notebook updated successfully.")
