import requests
import json

URL = "http://oracc.museum.upenn.edu/projectlist.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

print(f"Fetching {URL}...")
r = requests.get(URL, headers=HEADERS, verify=False, timeout=30)
data = r.json()

if "public" in data:
    projects = data["public"]
    print(f"Found {len(projects)} projects.")
    first = projects[0]
    print("Sample project keys:", list(first.keys()))
    print(json.dumps(first, indent=2))
else:
    print("No 'public' key found.")
