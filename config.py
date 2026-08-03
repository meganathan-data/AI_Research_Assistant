"""
Configuration module for CorpIntel AI.
Safely loads environment variables without hardcoding secret keys in source code.
Compatible with local development and Vercel serverless deployment.
"""

import os

def get_config() -> dict[str, str]:
    """Returns application configuration dictionary from environment variables."""
    return {
        "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
        "SERPER_API_KEY": os.environ.get("SERPER_API_KEY", ""),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL", "google/gemini-2.5-flash")
    }
