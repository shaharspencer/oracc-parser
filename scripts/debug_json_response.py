import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from oracc_parser.download.oracc_download import get_live_projects_dataframe

print("Testing get_live_projects_dataframe()...")
df = get_live_projects_dataframe()

if not df.empty:
    print(f"✅ Success! Fetched {len(df)} projects.")
    print("Columns:", list(df.columns))
    print("First project:", df.iloc[0].to_dict())
else:
    print("❌ Failed to fetch projects.")
