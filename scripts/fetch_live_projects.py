import requests
import json
import sys

URLS = [
    "http://oracc.museum.upenn.edu/projectlist.json",
    "http://oracc.museum.upenn.edu/projects.json"
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

for url in URLS:
    print(f"\nFetching {url}...")
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=30)
        print(f"Status: {r.status_code}")
        print(f"Content Length: {len(r.content)}")
        
        if len(r.content) == 0:
            print("Empty response body.")
            continue
            
        try:
            data = r.json()
            print("JSON Decode Success!")
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())}")
                if "projects" in data:
                    print(f"Found {len(data['projects'])} projects.")
                    print("Sample:", json.dumps(data['projects'][0], indent=2))
            elif isinstance(data, list):
                print(f"List of {len(data)} items.")
                print("Sample:", json.dumps(data[0], indent=2))
                
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print("Raw text (first 500 chars):")
            print(r.text[:500])
            
    except Exception as e:
        print(f"Request Failed: {e}")
