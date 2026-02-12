"""
Provider factory for model-agnostic extraction.
"""

from app.config import settings
from app.extraction.providers.base import ExtractionProvider
from app.extraction.providers.openai_provider import OpenAIProvider, ExtractionError
from app.extraction.providers.anthropic_provider import AnthropicProvider
from app.extraction.providers.gemini_provider import GeminiProvider
from app.extraction.providers.local_provider import LocalLLMProvider


def get_extraction_provider() -> ExtractionProvider:
    """
    Get configured extraction provider.
    
    Returns:
        Configured ExtractionProvider instance
        
    Raises:
        ValueError: If provider type is unknown
    """
    provider_type = settings.extraction_provider.lower()
    
    if provider_type == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model
        )
    
    elif provider_type == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model
        )
    
    elif provider_type == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model
        )
    
    elif provider_type == "local":
        if not settings.local_llm_endpoint:
            raise ValueError("LOCAL_LLM_ENDPOINT not configured")
        return LocalLLMProvider(
            endpoint=settings.local_llm_endpoint,
            model=settings.local_llm_model
        )
    
    else:
        raise ValueError(
            f"Unknown extraction provider: {provider_type}. "
            f"Supported: openai, anthropic, gemini, local"
        )


__all__ = ['get_extraction_provider', 'ExtractionProvider', 'ExtractionError']
