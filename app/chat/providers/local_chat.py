"""
Local LLM chat provider (stub implementation).
"""

import requests
from app.chat.providers.base import ChatProvider, ChatError


class LocalChatProvider(ChatProvider):
    """Local LLM chat provider (Ollama, vLLM, etc.)."""
    
    def __init__(self, endpoint: str, model: str = "llama2"):
        """
        Initialize local LLM chat provider.
        
        Args:
            endpoint: Local LLM endpoint URL
            model: Model name
        """
        self.endpoint = endpoint
        self.model = model
    
    @property
    def provider_name(self) -> str:
        return "local"
    
    async def generate_chat(self, message: str, context: str) -> str:
        """Generate chat response using local LLM."""
        try:
            # Build prompt with context
            if context:
                full_prompt = f"""{context}

You are a helpful AI assistant with access to the user's memory context above.
Use this context to personalize your responses and remember information about the user.
Be natural and conversational.

User: {message}
Assistant:"""
            else:
                full_prompt = f"User: {message}\nAssistant:"
            
            # Call local LLM endpoint (Ollama format)
            response = requests.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                raise ChatError(f"Local LLM returned {response.status_code}")
            
            result = response.json()
            return result.get('response', '').strip()
            
        except ChatError:
            raise
        except Exception as e:
            raise ChatError(f"Local LLM chat generation failed: {str(e)}")
