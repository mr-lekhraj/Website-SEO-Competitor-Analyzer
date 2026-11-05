from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .seo import HEADERS
from .url_safety import safe_fetch


def normalize_url(value):
    value = str(value or "").strip()
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    return value.rstrip("/")


def page_snapshot(url):
    normalized = normalize_url(url)
    try:
        response = safe_fetch(
            normalized,
            headers=HEADERS,
            timeout=(5, 12),
            max_bytes=2 * 1024 * 1024,
            max_redirects=5,
        )
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description = soup.find("meta", attrs={"name": "description"})
        return {
            "domain": urlparse(response.url).netloc,
            "status": response.status_code,
            "title": title,
            "description": description.get("content", "") if description else "",
            "h1": " | ".join(tag.get_text(" ", strip=True) for tag in soup.find_all("h1")[:3]),
            "page_bytes": len(response.content),
        }
    except Exception as exc:
        return {
            "domain": urlparse(normalized).netloc,
            "status": "ERROR",
            "title": "",
            "description": str(exc),
            "h1": "",
            "page_bytes": 0,
        }


def compare_domains(own_url, competitors):
    urls = [normalize_url(own_url)] + [normalize_url(item) for item in competitors]
    return [page_snapshot(url) for url in urls]


def content_gap(own_text, competitor_text):
    own = {item.strip().lower() for item in own_text.splitlines() if item.strip()}
    theirs = {item.strip().lower() for item in competitor_text.splitlines() if item.strip()}
    return sorted(theirs - own)
