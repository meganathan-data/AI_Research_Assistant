"""
Web Crawler Engine Module
Crawls company websites to discover key pages (Home, About, Products, Services, Contact, Pricing),
ignores login/duplicate/asset pages, extracts clean text, and returns structured Python dictionaries.
"""

import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# Ignored path keywords (Login, Signup, Cart, Assets)
IGNORE_KEYWORDS = [
    "login", "signin", "sign-in", "signup", "sign-up", "auth", "oauth",
    "cart", "checkout", "account", "privacy", "terms", "legal", "cookie",
    "wp-admin", "cdn-cgi", "css", "js", "png", "jpg", "jpeg", "svg", "pdf"
]

# Important page path keywords to discover
TARGET_KEYWORDS = [
    "about", "product", "service", "solution", "pricing", "contact",
    "features", "company", "team", "platform", "overview"
]

class CleanTextParser(HTMLParser):
    """Custom HTML Parser to extract visible text and internal links from web pages."""
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.text_chunks: list[str] = []
        self.discovered_links: set[str] = set()
        self.in_ignored_tag = False
        self.ignored_tags = {"script", "style", "nav", "footer", "noscript", "svg", "head", "header"}
        
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag.lower() in self.ignored_tags:
            self.in_ignored_tag = True
            
        if tag.lower() == "a":
            for attr, val in attrs:
                if attr == "href" and val:
                    full_url = urllib.parse.urljoin(self.base_url, val)
                    self.discovered_links.add(full_url)
                    
    def handle_endtag(self, tag: str):
        if tag.lower() in self.ignored_tags:
            self.in_ignored_tag = False
            
    def handle_data(self, data: str):
        if not self.in_ignored_tag:
            cleaned = data.strip()
            if len(cleaned) > 2:
                self.text_chunks.append(cleaned)

def fetch_page_dict(url: str, timeout: int = 5) -> dict[str, Any]:
    """
    Fetches a single URL and extracts clean text + internal links.
    Returns Python dictionary.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ReluBot/1.0 AI Research Assistant"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return {"url": url, "text": "", "links": [], "error": "Not HTML"}
            
            raw_html = response.read().decode("utf-8", errors="ignore")
            parser = CleanTextParser(url)
            parser.feed(raw_html)
            
            combined_text = " ".join(parser.text_chunks)
            # Normalize whitespace
            clean_text = re.sub(r'\s+', ' ', combined_text).strip()
            
            return {
                "url": url,
                "text": clean_text[:4000], # Cap text per page
                "links": list(parser.discovered_links),
                "error": None
            }
    except Exception as e:
        return {"url": url, "text": "", "links": [], "error": str(e)}

def is_valid_internal_link(link: str, base_domain: str) -> bool:
    """Checks if link is valid, internal, not login/duplicate/asset."""
    try:
        parsed = urllib.parse.urlparse(link)
        link_domain = parsed.netloc.lower().replace("www.", "")
        clean_base = base_domain.lower().replace("www.", "")
        
        if link_domain and link_domain != clean_base:
            return False
        
        path = parsed.path.lower()
        if any(keyword in path for keyword in IGNORE_KEYWORDS):
            return False
            
        if parsed.fragment and not path:
            return False
            
        return True
    except Exception:
        return False

def crawl_company_website(start_url: str, max_pages: int = 6) -> dict[str, Any]:
    """
    Crawls website starting from root URL.
    Discovers high-value pages, deduplicates, fetches text, and compiles a master Python dictionary.
    """
    if not start_url.startswith("http"):
        start_url = f"https://{start_url}"
        
    parsed_base = urllib.parse.urlparse(start_url)
    base_domain = parsed_base.netloc
    
    # 1. Fetch homepage first
    homepage_data = fetch_page_dict(start_url, timeout=5)
    
    pages_dict: dict[str, str] = {}
    visited_urls: set[str] = {start_url}
    
    if homepage_data["text"]:
        pages_dict[start_url] = homepage_data["text"]
        
    # 2. Extract candidate links matching high-value keywords
    candidate_urls: list[str] = []
    for link in homepage_data.get("links", []):
        if is_valid_internal_link(link, base_domain) and link not in visited_urls:
            path_lower = urllib.parse.urlparse(link).path.lower()
            if any(k in path_lower for k in TARGET_KEYWORDS):
                if link not in candidate_urls:
                    candidate_urls.append(link)
                    
    # Cap candidate URLs to discover
    to_crawl = candidate_urls[:max_pages - 1]
    
    # 3. Concurrently fetch selected subpages
    if to_crawl:
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {executor.submit(fetch_page_dict, url, 4): url for url in to_crawl}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                visited_urls.add(url)
                try:
                    res = future.result()
                    if res["text"]:
                        pages_dict[url] = res["text"]
                except Exception as e:
                    print(f"[Crawl Subpage Error {url}]: {e}")
                    
    # Compile unified dictionary
    all_texts = [f"--- PAGE: {url} ---\n{text}" for url, text in pages_dict.items()]
    combined_crawl_text = "\n\n".join(all_texts)
    
    crawl_result_dict: dict[str, Any] = {
        "base_url": start_url,
        "total_pages": len(pages_dict),
        "pages_crawled": list(pages_dict.keys()),
        "page_contents": pages_dict,
        "combined_text": combined_crawl_text[:16000], # Cap text for AI context
        "status": "success" if pages_dict else "partial"
    }
    
    return crawl_result_dict
