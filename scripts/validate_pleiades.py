"""Validate Pleiades IDs in provenience.csv against the downloaded Pleiades ZIP."""
import json as _json_mod

import json
import zipfile
from pathlib import Path
import pandas as pd
from oracc_parser.utils.paths import _data_file
import sys
sys.stdout.reconfigure(encoding='utf-8')

PLEIADES_ZIP = Path(__file__).parent.parent / "notebooks" / "data" / "plaides_scraped_data.zip"

# Load provenience CSV
df = pd.read_csv(_data_file("provenience.csv"), dtype=str)
df_ids = df[df["pleiades_id"].str.match(r"^\d+$", na=False)].copy()
print(f"Rows with a numeric pleiades_id: {len(df_ids)}")

# Load all Pleiades entries from ZIP
pleiades = {}
with zipfile.ZipFile(PLEIADES_ZIP) as z:
    for fname in z.namelist():
        pid = fname.replace(".json", "")
        try:
            data = json.loads(z.read(fname))
            pleiades[pid] = data.get("title", "")
        except Exception as e:
            print(f"  Could not read {fname}: {e}")

print(f"Pleiades entries in ZIP: {len(pleiades)}")
print()

# Cross-reference
ok = []
missing_from_zip = []

for _, row in df_ids.iterrows():
    pid = str(row["pleiades_id"]).strip()
    city = str(row["normalized_city"]).strip()
    raw = str(row["raw_provenience"]).strip()
    title = pleiades.get(pid)

    if title is None:
        missing_from_zip.append((pid, city, raw))
    else:
        name_match = city.lower() in title.lower() or title.lower() in city.lower()
        ok.append((pid, city, raw, title, name_match))

# Summary
print(f"{'='*70}")
print(f"OK  (ID exists in Pleiades ZIP):  {len(ok)}")
print(f"MISSING (not in Pleiades ZIP):    {len(missing_from_zip)}")
print()

if missing_from_zip:
    print("IDs not found in our Pleiades ZIP (may need re-scraping):")
    for pid, city, raw in missing_from_zip:
        print(f"  pleiades:{pid:>12s}  city={city}  raw={raw!r}")
    print()

name_mismatches = [(pid, city, raw, title) for pid, city, raw, title, ok_ in ok if not ok_]
if name_mismatches:
    print(f"Potential name mismatches ({len(name_mismatches)}) — our city name not in Pleiades title:")
    for pid, city, raw, title in name_mismatches:
        print(f"  pleiades:{pid:>12s}  our={city!r:35s}  pleiades={title!r}")
    print()

print("All matched entries (pleiades_id | our normalized_city | Pleiades title):")
for pid, city, raw, title, match in ok:
    flag = "" if match else "  *** NAME MISMATCH"
    line = f"  {pid:>12s}  {city:35s}  {title}{flag}"
    print(line.encode('ascii', errors='replace').decode('ascii'))
