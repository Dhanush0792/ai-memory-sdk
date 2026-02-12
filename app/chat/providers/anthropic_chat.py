"""
Anthropic chat provider.
"""

from anthropic import Anthropic
from app.chat.providers.base import ChatProvider, ChatError


class AnthropicChatProvider(ChatProvider):
    """Anthropic Claude-based chat provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Anthropic chat provider.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-5-sonnet)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    async def generate_chat(self, message: str, context: str) -> str:
        """Generate chat response using Anthropic API."""
        try:
            # Build system prompt with context
            if context:
                system_prompt = f"""{context}

You are a helpful AI assistant with access to the user's memory context above.
Use this context to personalize your responses and remember information about the user.
Be natural and conversational."""
            else:
                system_prompt = "You are a helpful AI assistant."
            
            # Call Anthropic API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise ChatError(f"Anthropic chat generation failed: {str(e)}")
