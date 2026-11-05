from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .url_safety import safe_fetch

HEADERS = {"User-Agent": "WebsiteSEOCompetitorAnalyzer/1.0"}
PAGE_MAX_BYTES = 2 * 1024 * 1024


def audit_url(url):
    checks = []

    try:
        response = safe_fetch(
            url,
            headers=HEADERS,
            timeout=(5, 18),
            max_bytes=PAGE_MAX_BYTES,
            max_redirects=5,
        )
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = description_tag.get("content", "").strip() if description_tag else ""
        h1 = soup.find_all("h1")
        canonical = soup.find("link", rel="canonical")
        robots = soup.find("meta", attrs={"name": "robots"})
        images = soup.find_all("img")
        missing_alt = sum(1 for image in images if image.get("alt") is None)
        links = soup.find_all("a", href=True)
        internal = sum(
            1 for link in links
            if urlparse(link["href"] if link["href"].startswith(("http://", "https://")) else response.url).netloc
            == urlparse(response.url).netloc
            and not link["href"].startswith(("mailto:", "tel:", "javascript:", "#"))
        )

        checks.extend([
            {"check": "HTTP response", "status": "PASS" if response.status_code == 200 else "REVIEW",
             "details": f"HTTP {response.status_code}", "weight": 2},
            {"check": "HTTPS", "status": "PASS" if response.url.startswith("https://") else "REVIEW",
             "details": response.url, "weight": 2},
            {"check": "Title tag", "status": "PASS" if 15 <= len(title) <= 60 else "REVIEW",
             "details": f"{len(title)} characters: {title or 'Missing'}", "weight": 2},
            {"check": "Meta description", "status": "PASS" if 70 <= len(description) <= 160 else "REVIEW",
             "details": f"{len(description)} characters: {description or 'Missing'}", "weight": 2},
            {"check": "H1 heading", "status": "PASS" if len(h1) == 1 else "REVIEW",
             "details": f"Found {len(h1)} H1 tags", "weight": 2},
            {"check": "Canonical URL", "status": "PASS" if canonical and canonical.get("href") else "REVIEW",
             "details": canonical.get("href", "Missing") if canonical else "Missing", "weight": 1},
            {"check": "Robots meta",
             "status": "REVIEW" if robots and "noindex" in robots.get("content", "").lower() else "PASS",
             "details": robots.get("content", "No robots meta tag; inspect HTTP headers too") if robots
             else "No robots meta tag; inspect HTTP headers too", "weight": 2},
            {"check": "Image alt attributes", "status": "PASS" if missing_alt == 0 else "REVIEW",
             "details": f"{missing_alt} of {len(images)} images lack an alt attribute", "weight": 1},
            {"check": "Internal links", "status": "PASS" if internal > 0 else "REVIEW",
             "details": f"{internal} internal links found", "weight": 1},
            {"check": "Mobile viewport", "status": "PASS" if soup.find("meta", attrs={"name": "viewport"})
             else "REVIEW",
             "details": "Viewport tag present" if soup.find("meta", attrs={"name": "viewport"})
             else "Viewport tag missing", "weight": 1},
        ])
        total = sum(item["weight"] for item in checks)
        score = round(100 * sum(item["weight"] for item in checks if item["status"] == "PASS") / total)
        return {
            "score": score,
            "checks": checks,
            "summary": {
                "url": response.url,
                "http_status": response.status_code,
                "title": title,
                "description": description,
                "images": len(images),
                "missing_alt": missing_alt,
                "internal_links": internal,
            },
        }
    except Exception as exc:
        return {
            "score": 0,
            "checks": [{"check": "Fetch page", "status": "FAIL", "details": str(exc), "weight": 1}],
            "summary": {"url": url, "error": str(exc)},
        }
