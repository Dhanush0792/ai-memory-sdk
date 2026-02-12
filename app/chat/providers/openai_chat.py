"""
OpenAI chat provider.
"""

from openai import OpenAI
from app.chat.providers.base import ChatProvider, ChatError


class OpenAIChatProvider(ChatProvider):
    """OpenAI-based chat provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize OpenAI chat provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    async def generate_chat(self, message: str, context: str) -> str:
        """Generate chat response using OpenAI API."""
        try:
            # Build system prompt with context
            if context:
                system_prompt = f"""{context}

You are a helpful AI assistant with access to the user's memory context above.
Use this context to personalize your responses and remember information about the user.
Be natural and conversational."""
            else:
                system_prompt = "You are a helpful AI assistant."
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise ChatError(f"OpenAI chat generation failed: {str(e)}")
