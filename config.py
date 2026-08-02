"""
Configuration module for Relu Consultancy AI & Automation Developer Hackathon.
Holds API key settings loaded from environment variables or custom UI inputs.
All hardcoded default keys have been completely removed per user request.
"""

import os

# Configuration dictionary using environment variables or custom UI entries only
CONFIG: dict[str, str] = {
    "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
    "SERPER_API_KEY": os.environ.get("SERPER_API_KEY", ""),
    "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
    "DEFAULT_MODEL": "google/gemini-2.5-flash",
    "GEMINI_ENDPOINT": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
    "OPENROUTER_ENDPOINT": "https://openrouter.ai/api/v1/chat/completions",
    "SERPER_ENDPOINT": "https://google.serper.dev/search",
}

def get_config() -> dict[str, str]:
    """Returns the current configuration dictionary."""
    return CONFIG.copy()
