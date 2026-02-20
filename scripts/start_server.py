"""
Script: Start the localhost API server.

Usage:
    python scripts/start_server.py

Then open http://localhost:8000/docs for the interactive Swagger UI.

Workflow:
    1. POST /parse?project=saao/saa01&limit=5  → downloads and parses
    2. GET  /metadata?project=saao/saa01        → flat metadata table
    3. GET  /transliterations?project=saao/saa01 → transliteration strings
    4. GET  /full?project=saao/saa01             → everything in one flat JSON

Requires: pip install oracc-parser[server]
"""

from oracc_parser.server import run_server

if __name__ == "__main__":
    run_server()
