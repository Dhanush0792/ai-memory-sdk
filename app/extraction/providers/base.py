"""
Base provider interface for model-agnostic extraction.
"""

from abc import ABC, abstractmethod
from typing import List
from app.models import ExtractedTriple


class ExtractionProvider(ABC):
    """
    Abstract base class for LLM extraction providers.
    
    All providers must implement the extract() method.
    """
    
    @abstractmethod
    def extract(self, conversation_text: str) -> List[ExtractedTriple]:
        """
        Extract structured memories from conversation text.
        
        Args:
            conversation_text: Raw conversation text
            
        Returns:
            List of extracted triples
            
        Raises:
            ExtractionError: If extraction fails
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for logging."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model name for logging."""
        pass
