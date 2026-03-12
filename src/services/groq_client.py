"""
Groq Client - AsyncGroq client
"""
from functools import lru_cache
from groq import AsyncGroq
from src.config import get_settings

@lru_cache()
def get_groq_client() -> AsyncGroq:
    """Lazily initialized Groq client."""
    settings = get_settings()
    return AsyncGroq(api_key=settings.groq_api_key)