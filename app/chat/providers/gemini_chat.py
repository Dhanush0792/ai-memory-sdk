"""
Gemini chat provider with context truncation and metrics.
"""

import time
import google.generativeai as genai
from app.chat.providers.base import ChatProvider, ChatError
from app.config import settings


class GeminiChatProvider(ChatProvider):
    """Gemini-based chat provider with context management and observability."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Initialize Gemini chat provider.
        
        Args:
            api_key: Gemini API key
            model: Model to use (default: gemini-1.5-flash)
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name_str = model
        
        # Token limits (configurable via environment)
        self.max_input_tokens = getattr(settings, 'gemini_max_input_tokens', 8000)
        self.max_output_tokens = getattr(settings, 'gemini_max_output_tokens', 1024)
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (4 chars ≈ 1 token)."""
        return len(text) // 4
    
    def _truncate_context(self, message: str, context: str) -> tuple[str, bool]:
        """
        Truncate context to fit within token limits.
        
        Strategy:
        - Preserve the user message
        - Trim memory context if needed
        
        Returns:
            (truncated_context, was_truncated)
        """
        message_tokens = self._estimate_tokens(message)
        context_tokens = self._estimate_tokens(context)
        
        # Reserve tokens for message and system prompt
        system_prompt_tokens = 100  # Approximate
        available_for_context = self.max_input_tokens - message_tokens - system_prompt_tokens
        
        if context_tokens <= available_for_context:
            return context, False
        
        # Truncate context to fit
        max_context_chars = available_for_context * 4
        truncated_context = context[:max_context_chars]
        
        return truncated_context, True
    
    async def generate_chat(self, message: str, context: str) -> str:
        """Generate chat response using Gemini API with context management."""
        # Import metrics here to avoid circular dependency
        from app.observability import metrics, logger
        
        # Truncate context if needed
        truncated_context, was_truncated = self._truncate_context(message, context)
        
        if was_truncated:
            logger.info(
                "gemini_context_truncated",
                original_tokens=self._estimate_tokens(context),
                truncated_tokens=self._estimate_tokens(truncated_context)
            )
            try:
                metrics.chat_context_truncated_total.labels(provider="gemini").inc()
            except AttributeError:
                pass
        
        start_time = time.time()
        
        try:
            # Build prompt with context
            # Note: Gemini doesn't have separate system/user roles like OpenAI
            # We include context in the user message
            if truncated_context:
                full_prompt = f"""{truncated_context}

You are a helpful AI assistant with access to the user's memory context above.
Use this context to personalize your responses and remember information about the user.
Be natural and conversational.

User message: {message}"""
            else:
                full_prompt = message
            
            # Call Gemini API
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=self.max_output_tokens,
                )
            )
            
            if not response.text:
                raise ChatError("Gemini returned empty response")
            
            # Record latency
            duration = time.time() - start_time
            try:
                metrics.llm_call_latency_seconds.labels(
                    provider="gemini",
                    type="chat"
                ).observe(duration)
            except AttributeError:
                pass
            
            logger.info(
                "gemini_chat_success",
                duration=duration,
                context_truncated=was_truncated
            )
            
            return response.text.strip()
            
        except ChatError:
            raise
        except Exception as e:
            # Handle API errors
            error_msg = str(e).lower()
            
            # Check for rate limiting (429)
            if 'rate limit' in error_msg or 'quota' in error_msg or '429' in error_msg:
                raise ChatError(f"Gemini rate limit exceeded: {str(e)}")
            
            # Check for authentication errors
            if 'api key' in error_msg or 'authentication' in error_msg or 'permission' in error_msg:
                raise ChatError(f"Gemini authentication failed: {str(e)}")
            
            # Generic error
            raise ChatError(f"Gemini chat generation failed: {str(e)}")
