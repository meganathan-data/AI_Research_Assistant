"""
AI Reasoning Engine Module
Communicates with OpenRouter API supporting any user-selected OpenRouter AI model.
Allows choosing models such as google/gemini-2.0-flash-001, meta-llama/llama-3.3-70b-instruct,
openai/gpt-4o-mini, deepseek/deepseek-chat, and custom model slugs.
"""

import json
import urllib.request
import urllib.error
import re
from typing import Any
from config import get_config

SYSTEM_PROMPT = """
You are an expert AI Corporate Intelligence Analyst for Relu Consultancy.
Analyze the provided company website text and search snippets.
Generate a structured report in STRICT JSON format with NO markdown formatting, NO backticks.

CRITICAL INSTRUCTIONS FOR LOCATIONS, PRODUCTS, AND CITY RESEARCH:
1. LOCATIONS MUST BE AN ARRAY OF COUNTRIES, where each country contains a list of CITIES, and each city contains an array of ADDRESSES.
   Format:
   "locations": [
     {
       "country_name": "Country Name",
       "cities": [
         {
           "city_name": "City Name",
           "addresses": ["Full physical address string"]
         }
       ]
     }
   ]
2. Include ALL major countries and cities where the company operates worldwide (e.g., India, United States, United Kingdom, Canada, Australia, Japan, Germany). Include exact physical street addresses for each city.
3. If the user asked about a specific city (e.g. "TCS Chennai" or "Tesla Austin"), include a specific SUMMARY bullet detailing EXACTLY WHAT THE COMPANY DOES IN THAT PARTICULAR CITY BRANCH.
4. PRODUCTS AND SERVICES MUST BE EXHAUSTIVE. Collect and list ALL key software products, enterprise platforms, cloud tools, and core services offered by the company (at least 8-12 items).
5. If phone is unavailable, set phone to "".

The JSON MUST follow this exact schema:
{
  "company_name": "Company Name",
  "website": "https://officialwebsite.com",
  "phone": "",
  "target_city_focus": "",
  "locations": [
    {
      "country_name": "India",
      "cities": [
        {
          "city_name": "Mumbai (Global Headquarters)",
          "addresses": ["TCS House, Raveline Street, Fort, Mumbai 400001, Maharashtra, India"]
        }
      ]
    }
  ],
  "executive_summary": "Detailed overview of core mission and market position.",
  "products_and_services": [
    "Product / Platform 1",
    "Product / Platform 2"
  ],
  "summary": [
    "Paragraph 1 regarding operational focus.",
    "Paragraph 2 regarding market competition."
  ],
  "competitors": [
    {"name": "Competitor 1", "website": "https://competitor1.com"}
  ]
}
"""

DEFAULT_MODELS = [
    "google/gemini-2.0-flash-001",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3.3-70b-instruct",
    "openai/gpt-4o-mini",
    "deepseek/deepseek-chat"
]

def generate_company_research(
    company_name: str,
    website_url: str,
    crawl_data: dict[str, Any],
    serper_data: dict[str, Any],
    selected_model: str = "",
    custom_openrouter_key: str = "",
    custom_google_key: str = ""
) -> dict[str, Any]:
    """
    Coordinates AI processing using user-selected OpenRouter AI model and user API key.
    Returns parsed Python research report dictionary or detailed error if key fails.
    """
    cfg = get_config()
    openrouter_key = custom_openrouter_key or cfg.get("OPENROUTER_API_KEY", "")

    if not openrouter_key:
        return {
            "error": "Missing OpenRouter API Key. Please enter your OpenRouter API Key under the API tab on the left sidebar to run AI research."
        }

    prompt_user_content = f"""
    COMPANY TO RESEARCH: {company_name}
    OFFICIAL WEBSITE: {website_url}

    KNOWLEDGE GRAPH DATA:
    {json.dumps(serper_data.get('knowledge_graph', {}), indent=2)}

    SEARCH SNIPPETS:
    {json.dumps(serper_data.get('snippets', []), indent=2)}

    WEBSITE CRAWLED CONTENT:
    {crawl_data.get('combined_text', '')[:10000]}
    """

    last_error_detail = ""

    # Primary choice: User's selected model, followed by fallbacks
    user_choice = selected_model.strip() if selected_model else "google/gemini-2.0-flash-001"
    models_to_try = [user_choice] + [m for m in DEFAULT_MODELS if m != user_choice]

    for model in models_to_try:
        if not model:
            continue
        try:
            res_dict, err_msg = query_openrouter(prompt_user_content, model, openrouter_key)
            if res_dict:
                return sanitize_report_dict(res_dict, company_name, website_url, serper_data)
            if err_msg:
                last_error_detail = err_msg
                if "401" in err_msg or "402" in err_msg or "Unauthorized" in err_msg or "credit" in err_msg.lower() or "key" in err_msg.lower():
                    return {"error": err_msg}
        except Exception as e:
            last_error_detail = f"Exception with model '{model}': {e}"

    return {
        "error": last_error_detail or "OpenRouter API execution failed. Please verify your OpenRouter API key and selected model."
    }

def query_openrouter(prompt: str, model: str, api_key: str) -> tuple[dict[str, Any] | None, str]:
    """
    Calls OpenRouter Chat Completions API with the requested model slug.
    Returns (dict_result, error_message_string).
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Relu AI Research Assistant"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=14) as response:
            data = json.loads(response.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                text_resp = choices[0].get("message", {}).get("content", "")
                parsed = parse_json_to_dict(text_resp)
                if parsed:
                    return parsed, ""
            return None, f"OpenRouter model '{model}' returned empty completion."
            
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message") or err_json.get("message") or err_body
        except Exception:
            msg = err_body
        full_err = f"OpenRouter API Error ({model} - HTTP {e.code}): {msg}"
        print(f"[OpenRouter HTTP Error]: {full_err}")
        return None, full_err
        
    except Exception as e:
        full_err = f"OpenRouter Connection Error ({model}): {e}"
        print(f"[OpenRouter Exception]: {full_err}")
        return None, full_err

def parse_json_to_dict(text: str) -> dict[str, Any] | None:
    """Cleans JSON string and returns Python dictionary."""
    cleaned = text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print(f"[JSON Parse Error]: {e}")
        return None

def sanitize_report_dict(
    report: dict[str, Any],
    fallback_name: str,
    fallback_url: str,
    serper_data: dict[str, Any]
) -> dict[str, Any]:
    """Sanitizes report dictionary and formats 3-tier locations."""
    kg = serper_data.get("knowledge_graph", {})
    phone_val = report.get("phone") or kg.get("phone") or ""
    if "not" in phone_val.lower() or "none" in phone_val.lower():
        phone_val = ""

    locs_input = report.get("locations")
    if isinstance(locs_input, list) and locs_input:
        locs_array = locs_input
    else:
        locs_array = [
            {
                "country_name": "Global Headquarters",
                "cities": [
                    {
                        "city_name": "Main Office",
                        "addresses": [kg.get("address") or f"{fallback_name} Main Campus"]
                    }
                ]
            }
        ]

    return {
        "company_name": report.get("company_name") or fallback_name,
        "website": report.get("website") or fallback_url,
        "phone": phone_val,
        "locations": locs_array,
        "executive_summary": report.get("executive_summary") or f"{fallback_name} is an enterprise digital provider.",
        "products_and_services": report.get("products_and_services") or ["Enterprise Platforms", "Cloud & AI Solutions"],
        "summary": report.get("summary") or ["Enterprise operational transformation and digital consulting."],
        "competitors": report.get("competitors") or []
    }
