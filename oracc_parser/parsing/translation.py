"""
Fetch English translations of ORACC tablets from the ORACC web interface.

Downloads and caches HTML pages, then extracts translation text
using BeautifulSoup selectors.
"""

from pathlib import Path

import requests
from bs4 import BeautifulSoup

from oracc_parser.utils.logger import get_logger
from oracc_parser.settings import CACHE_DIR as _settings_CACHE_DIR

logger = get_logger()

ORACC_HTML_URL = "https://oracc.museum.upenn.edu"


def get_translation(project: str, text_id: str, cache_dir: str | None = None) -> str:
    """Fetch the English translation for a specific tablet.

    Tries to read from a cached HTML file first. If not found,
    downloads from ORACC and caches the result.

    Args:
        project: Project path, e.g. ``"saao/saa01"``.
        text_id: The P-number or text ID, e.g. ``"P313511"``.
        cache_dir: Custom cache directory. Default: ``oracc_cache/html/``.

    Returns:
        Multi-line translation string, or empty string on failure.
    """
    cache = Path(cache_dir) if CACHE_DIR else _settings_CACHE_DIR / "html"
    cache.mkdir(parents=True, exist_ok=True)

    project_path = project.replace("-", "/")
    html_path = cache / project_path / f"{text_id}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)

    # Try cached version
    if html_path.exists():
        content = html_path.read_text(encoding="utf-8", errors="replace")
        if _is_valid_html(content):
            return _extract_translation(content)
        else:
            html_path.unlink()  # Remove invalid cached file

    # Download
    url = f"{ORACC_HTML_URL}/{project_path}/{text_id}/html"
    content = _download_html(url)
    if content:
        html_path.write_text(content, encoding="utf-8")
        return _extract_translation(content)

    return ""


def _download_html(url: str) -> str | None:
    """Download HTML content from a URL."""
    try:
        resp = requests.get(url, verify=False, timeout=30)
        if resp.status_code == 200 and resp.text.strip() != "404":
            return resp.content.decode(resp.encoding or "utf-8", errors="replace")
        logger.warning(f"Failed to fetch {url}: HTTP {resp.status_code}")
    except requests.RequestException as e:
        logger.warning(f"Error downloading {url}: {e}")
    return None


def _extract_translation(html_content: str) -> str:
    """Extract translation lines from ORACC HTML page."""
    soup = BeautifulSoup(html_content, "html.parser")
    spans = soup.select("td.t1 p.tr span.cell")
    lines = []
    for span in spans:
        text = span.get_text()
        for punct in [".", ",", ":", ";", "?", "!"]:
            text = text.replace(f" {punct}", punct)
        lines.append(text.strip())
    return "\n".join(lines)


def _is_valid_html(content: str) -> bool:
    """Check if cached HTML content is valid."""
    if not content:
        return False
    soup = BeautifulSoup(content, "html.parser")
    return bool(soup.find("html") and soup.find("body"))
