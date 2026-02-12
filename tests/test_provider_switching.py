"""
Test suite for provider switching functionality.
Verifies system works with all provider combinations.
"""

import pytest
from unittest.mock import Mock, patch
from app.extraction.factory import get_extraction_provider
from app.chat.providers.factory import get_chat_provider
from app.config import Settings


class TestProviderSwitching:
    """Test provider switching scenarios."""
    
    def test_gemini_extraction_gemini_chat(self):
        """Test with both extraction and chat using Gemini."""
        settings = Settings(
            database_url="postgresql://test",
            api_key="test-api-key-1234567890",
            extraction_provider="gemini",
            chat_provider="gemini",
            gemini_api_key="test-gemini-key"
        )
        
        with patch('app.extraction.factory.settings', settings):
            with patch('app.chat.providers.factory.settings', settings):
                with patch('google.generativeai.GenerativeModel'):
                    extraction_provider = get_extraction_provider()
                    chat_provider = get_chat_provider()
                    
                    assert extraction_provider.provider_name == "gemini"
                    assert chat_provider.provider_name == "gemini"
    
    def test_openai_extraction_gemini_chat(self):
        """Test with OpenAI extraction and Gemini chat (mixed providers)."""
        settings = Settings(
            database_url="postgresql://test",
            api_key="test-api-key-1234567890",
            extraction_provider="openai",
            chat_provider="gemini",
            openai_api_key="test-openai-key",
            gemini_api_key="test-gemini-key"
        )
        
        with patch('app.extraction.factory.settings', settings):
            with patch('app.chat.providers.factory.settings', settings):
                with patch('google.generativeai.GenerativeModel'):
                    extraction_provider = get_extraction_provider()
                    chat_provider = get_chat_provider()
                    
                    assert extraction_provider.provider_name == "openai"
                    assert chat_provider.provider_name == "gemini"
    
    def test_gemini_extraction_openai_chat(self):
        """Test with Gemini extraction and OpenAI chat (mixed providers)."""
        settings = Settings(
            database_url="postgresql://test",
            api_key="test-api-key-1234567890",
            extraction_provider="gemini",
            chat_provider="openai",
            openai_api_key="test-openai-key",
            gemini_api_key="test-gemini-key"
        )
        
        with patch('app.extraction.factory.settings', settings):
            with patch('app.chat.providers.factory.settings', settings):
                with patch('google.generativeai.GenerativeModel'):
                    extraction_provider = get_extraction_provider()
                    chat_provider = get_chat_provider()
                    
                    assert extraction_provider.provider_name == "gemini"
                    assert chat_provider.provider_name == "openai"
    
    def test_openai_fallback_when_chat_provider_not_set(self):
        """Test that chat provider falls back to extraction provider."""
        settings = Settings(
            database_url="postgresql://test",
            api_key="test-api-key-1234567890",
            extraction_provider="openai",
            chat_provider=None,  # Not set
            openai_api_key="test-openai-key"
        )
        
        with patch('app.chat.providers.factory.settings', settings):
            chat_provider = get_chat_provider()
            assert chat_provider.provider_name == "openai"
    
    def test_gemini_fallback_when_chat_provider_not_set(self):
        """Test that chat provider falls back to Gemini extraction provider."""
        settings = Settings(
            database_url="postgresql://test",
            api_key="test-api-key-1234567890",
            extraction_provider="gemini",
            chat_provider=None,  # Not set
            gemini_api_key="test-gemini-key"
        )
        
        with patch('app.chat.providers.factory.settings', settings):
            with patch('google.generativeai.GenerativeModel'):
                chat_provider = get_chat_provider()
                assert chat_provider.provider_name == "gemini"
    
    def test_anthropic_extraction_anthropic_chat(self):
        """Test with Anthropic for both extraction and chat."""
        settings = Settings(
            database_url="postgresql://test",
            api_key="test-api-key-1234567890",
            extraction_provider="anthropic",
            chat_provider=None,  # Falls back to extraction_provider
            anthropic_api_key="test-anthropic-key"
        )
        
        with patch('app.extraction.factory.settings', settings):
            with patch('app.chat.providers.factory.settings', settings):
                extraction_provider = get_extraction_provider()
                chat_provider = get_chat_provider()
                
                assert extraction_provider.provider_name == "anthropic"
                assert chat_provider.provider_name == "anthropic"
    
    def test_missing_gemini_key_raises_error(self):
        """Test that missing Gemini API key raises ValueError."""
        settings = Settings(
            database_url="postgresql://test",
            api_key="test-api-key-1234567890",
            extraction_provider="gemini",
            gemini_api_key=None  # Missing
        )
        
        with patch('app.extraction.factory.settings', settings):
            with pytest.raises(ValueError) as exc_info:
                get_extraction_provider()
            
            assert "GEMINI_API_KEY not configured" in str(exc_info.value)
    
    def test_invalid_provider_raises_error(self):
        """Test that invalid provider name raises ValueError."""
        settings = Settings(
            database_url="postgresql://test",
            api_key="test-api-key-1234567890",
            extraction_provider="invalid_provider",
            openai_api_key="test-key"
        )
        
        # This should fail at settings validation level
        # But if it somehow gets through, factory should catch it
        with patch('app.extraction.factory.settings', settings):
            with pytest.raises(ValueError):
                get_extraction_provider()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
