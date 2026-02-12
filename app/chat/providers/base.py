"""
Base chat provider interface for model-agnostic chat generation.
"""

from abc import ABC, abstractmethod


class ChatProvider(ABC):
    """
    Abstract base class for LLM chat providers.
    
    All providers must implement the generate_chat() method.
    """
    
    @abstractmethod
    async def generate_chat(self, message: str, context: str) -> str:
        """
        Generate chat response with memory context.
        
        Args:
            message: User message
            context: Memory context to inject into system prompt
            
        Returns:
            LLM response text
            
        Raises:
            ChatError: If chat generation fails
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for logging."""
        pass


class ChatError(Exception):
    """Raised when chat generation fails."""
    pass
