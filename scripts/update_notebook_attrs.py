import nbformat
from pathlib import Path

nb_path = Path("notebooks/01_quickstart.ipynb")
nb = nbformat.read(nb_path, as_version=4)

print(f"Updating {nb_path}...")

found = False
for i, cell in enumerate(nb.cells):
    if cell.cell_type == "code" and "tablet.metadata.text_id" in cell.source:
        print(f"Found target code at cell index {i}")
        new_source = cell.source.replace("tablet.metadata.text_id", "tablet.metadata.id_text")
        nb.cells[i]["source"] = new_source
        found = True
        print("Updated source code.")

if found:
    nbformat.write(nb, nb_path)
    print("✅ Notebook updated successfully.")
else:
    print("❌ target code not found.")
