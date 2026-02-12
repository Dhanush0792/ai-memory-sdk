"""
Extraction module for model-agnostic memory extraction.
"""

from app.extraction.factory import get_extraction_provider, ExtractionProvider, ExtractionError

__all__ = ['get_extraction_provider', 'ExtractionProvider', 'ExtractionError']
