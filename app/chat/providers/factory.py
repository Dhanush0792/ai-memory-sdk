"""
Chat provider factory with quota-aware fallback support.
"""

from app.config import settings
from app.chat.providers.base import ChatProvider, ChatError
from app.chat.providers.openai_chat import OpenAIChatProvider
from app.chat.providers.anthropic_chat import AnthropicChatProvider
from app.chat.providers.gemini_chat import GeminiChatProvider
from app.chat.providers.local_chat import LocalChatProvider


class FallbackChatProvider(ChatProvider):
    """
    Wrapper provider that implements quota-aware fallback.
    
    If primary provider returns 429 (rate limit), automatically
    falls back to secondary provider.
    """
    
    def __init__(self, primary: ChatProvider, fallback: ChatProvider):
        self.primary = primary
        self.fallback = fallback
    
    @property
    def provider_name(self) -> str:
        return f"{self.primary.provider_name}_with_fallback"
    
    async def generate_chat(self, message: str, context: str) -> str:
        """Generate chat with automatic fallback on rate limits."""
        from app.observability import metrics, logger
        
        try:
            # Try primary provider
            return await self.primary.generate_chat(message, context)
        except ChatError as e:
            error_msg = str(e).lower()
            
            # Check if this is a rate limit error
            if 'rate limit' in error_msg or 'quota' in error_msg or '429' in error_msg:
                logger.warning(
                    "provider_fallback_triggered",
                    from_provider=self.primary.provider_name,
                    to_provider=self.fallback.provider_name,
                    error=str(e)
                )
                
                # Record fallback metric
                try:
                    metrics.provider_fallback_total.labels(
                        from_provider=self.primary.provider_name,
                        to_provider=self.fallback.provider_name
                    ).inc()
                except AttributeError:
                    pass
                
                # Attempt fallback
                return await self.fallback.generate_chat(message, context)
            else:
                # Not a rate limit error, re-raise
                raise


def get_chat_provider() -> ChatProvider:
    """
    Get configured chat provider with optional fallback.
    
    Uses CHAT_PROVIDER if set, otherwise falls back to EXTRACTION_PROVIDER.
    If PROVIDER_FALLBACK_ENABLED=true and primary is Gemini, wraps with
    fallback to OpenAI on rate limits.
    
    Returns:
        Configured ChatProvider instance
        
    Raises:
        ValueError: If provider type is unknown or not configured
    """
    provider_type = settings.get_chat_provider().lower()
    
    # Create primary provider
    primary_provider = _create_provider(provider_type)
    
    # Check if fallback is enabled
    if settings.provider_fallback_enabled and provider_type == "gemini":
        # Create fallback provider (OpenAI)
        if settings.openai_api_key:
            fallback_provider = OpenAIChatProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_model
            )
            return FallbackChatProvider(primary_provider, fallback_provider)
    
    return primary_provider


def _create_provider(provider_type: str) -> ChatProvider:
    """Create a chat provider instance."""
    if provider_type == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        return OpenAIChatProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model
        )
    
    elif provider_type == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        return AnthropicChatProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model
        )
    
    elif provider_type == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        return GeminiChatProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model
        )
    
    elif provider_type == "local":
        if not settings.local_llm_endpoint:
            raise ValueError("LOCAL_LLM_ENDPOINT not configured")
        return LocalChatProvider(
            endpoint=settings.local_llm_endpoint,
            model=settings.local_llm_model
        )
    
    else:
        raise ValueError(
            f"Unknown chat provider: {provider_type}. "
            f"Supported: openai, anthropic, gemini, local"
        )


__all__ = ['get_chat_provider', 'ChatProvider', 'FallbackChatProvider']
