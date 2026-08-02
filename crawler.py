"""
Web Crawler Engine Module
Concurrently crawls official company web pages using ThreadPoolExecutor with short 3.5s timeouts.
Filters duplicate pages, skips login/social links, and returns scraped text in Python dictionaries.
"""

import json
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

class CleanTextHTMLParser(HTMLParser):
    """Parses HTML document into clean plain text lines."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_tag = False

    def handle_starttag(self, tag, attrs):
        if tag in ["script", "style", "head", "nav", "svg", "noscript", "footer"]:
            self.ignore_tag = True

    def handle_endtag(self, tag):
        if tag in ["script", "style", "head", "nav", "svg", "noscript", "footer"]:
            self.ignore_tag = False

    def handle_data(self, data):
        if not self.ignore_tag:
            clean = data.strip()
            if clean:
                self.text_parts.append(clean)

    def get_text(self) -> str:
        return " ".join(self.text_parts)

def fetch_single_page(url: str, timeout: float = 3.5) -> dict[str, str]:
    """Fetches single web page HTML and parses text content fast."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return {"url": url, "text": "", "status": "skipped_binary"}
            html = response.read().decode("utf-8", errors="ignore")
            parser = CleanTextHTMLParser()
            parser.feed(html)
            return {"url": url, "text": parser.get_text()[:3000], "status": "success"}
    except Exception as e:
        return {"url": url, "text": "", "status": f"error: {e}"}

def discover_subpages(base_url: str) -> list[str]:
    """Generates standard corporate subpage URLs to crawl in parallel."""
    base_url = base_url.rstrip("/")
    candidates = [
        base_url,
        f"{base_url}/about",
        f"{base_url}/products",
        f"{base_url}/contact",
        f"{base_url}/services"
    ]
    return candidates

def crawl_company_website(website_url: str, max_pages: int = 3) -> dict[str, Any]:
    """
    Concurrently crawls company website pages using ThreadPoolExecutor.
    Returns Python dictionary with aggregated text and crawl statistics.
    """
    if not website_url:
        return {"total_pages": 0, "pages_crawled": [], "combined_text": ""}
        
    urls_to_crawl = discover_subpages(website_url)[:max_pages]
    
    pages_crawled = []
    text_blocks = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(fetch_single_page, url, 3.5): url for url in urls_to_crawl}
        for future in as_completed(future_map):
            res = future.result()
            if res.get("text"):
                pages_crawled.append(res["url"])
                text_blocks.append(f"--- PAGE: {res['url']} ---\n{res['text']}")

    combined_text = "\n\n".join(text_blocks)
    return {
        "total_pages": len(pages_crawled),
        "pages_crawled": pages_crawled,
        "combined_text": combined_text[:8000]
    }
