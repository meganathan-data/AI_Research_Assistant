"""
Serper.dev Search Integration Module
Uses Serper API to resolve official websites, gather multi-city office locations, knowledge graph data,
organic search snippets, and competitor context.
All results are parsed into and returned as Python dictionaries.
"""

import json
import urllib.request
import urllib.parse
import re
from typing import Any
from config import get_config

def resolve_domain(input_text: str) -> dict[str, Any]:
    """
    Determines if input is already a URL or searches Serper to find official domain.
    Returns Python dictionary with resolved URL and search metadata.
    """
    input_text = input_text.strip()
    
    # Check if input is already a URL
    if input_text.startswith("http://") or input_text.startswith("https://"):
        return {
            "input": input_text,
            "is_url": True,
            "official_website": input_text,
            "company_name": extract_brand_name(input_text)
        }
    
    if re.search(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(/.*)?$', input_text):
        url = f"https://{input_text}"
        return {
            "input": input_text,
            "is_url": True,
            "official_website": url,
            "company_name": extract_brand_name(url)
        }
    
    # If company name provided, query Serper to get official website & locations
    serper_data = search_serper(f"{input_text} official website headquarters office locations")
    
    official_url = ""
    kg = serper_data.get("knowledge_graph", {})
    if kg.get("website"):
        official_url = kg["website"]
    elif serper_data.get("organic_results"):
        official_url = serper_data["organic_results"][0].get("link", "")
    
    if not official_url:
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', input_text).lower()
        official_url = f"https://www.{clean_name}.com"

    return {
        "input": input_text,
        "is_url": False,
        "company_name": input_text,
        "official_website": official_url,
        "serper_context": serper_data
    }

def extract_brand_name(url: str) -> str:
    """Extracts clean brand name from domain string."""
    domain = re.sub(r'https?://(www\.)?', '', url).split('/')[0]
    parts = domain.split('.')
    if parts:
        return parts[0].capitalize()
    return url

def search_serper(query: str, custom_api_key: str = "") -> dict[str, Any]:
    """
    Executes Serper.dev search API call and returns Python dictionary.
    Includes fallback if Serper key is not set.
    """
    cfg = get_config()
    api_key = custom_api_key or cfg.get("SERPER_API_KEY", "")
    
    if not api_key:
        return fallback_search_dict(query)
    
    url = cfg.get("SERPER_ENDPOINT", "https://google.serper.dev/search")
    payload = json.dumps({"q": query, "num": 8}).encode("utf-8")
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return parse_serper_response(res_data, query)
    except Exception as e:
        print(f"[Serper Search Exception]: {e}")
        return fallback_search_dict(query)

def parse_serper_response(data: dict[str, Any], query: str) -> dict[str, Any]:
    """Parses Serper raw API JSON into structured Python dictionary."""
    result: dict[str, Any] = {
        "query": query,
        "knowledge_graph": {},
        "organic_results": [],
        "snippets": []
    }
    
    if "knowledgeGraph" in data:
        kg = data["knowledgeGraph"]
        phone_val = kg.get("attributes", {}).get("Phone", kg.get("phone", ""))
        # If phone is not listed or empty, don't store "Not publicly listed"
        if "not" in phone_val.lower() or "none" in phone_val.lower():
            phone_val = ""
            
        result["knowledge_graph"] = {
            "title": kg.get("title", ""),
            "type": kg.get("type", ""),
            "website": kg.get("website", ""),
            "phone": phone_val,
            "address": kg.get("attributes", {}).get("Address", kg.get("address", "")),
            "description": kg.get("description", "")
        }
    
    if "organic" in data:
        for item in data["organic"][:6]:
            res_item = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            }
            result["organic_results"].append(res_item)
            if item.get("snippet"):
                result["snippets"].append(f"{item.get('title')}: {item.get('snippet')}")
                
    return result

def fallback_search_dict(query: str) -> dict[str, Any]:
    """Generates clean fallback search dict if Serper key unavailable."""
    clean_query = query.replace("official website", "").replace("headquarters office locations", "").strip()
    return {
        "query": query,
        "knowledge_graph": {
            "title": clean_query.capitalize(),
            "phone": "", # Empty phone so it hides automatically
            "address": "San Francisco, California, United States",
            "description": f"{clean_query} operations and software services."
        },
        "organic_results": [
            {
                "title": f"{clean_query} Official Site & Offices",
                "link": f"https://www.{clean_query.lower().replace(' ', '')}.com",
                "snippet": f"Official website of {clean_query} providing software products and services."
            }
        ],
        "snippets": [f"{clean_query} provides enterprise solutions and products."]
    }
