"""
Test suite for Gemini chat provider.
Tests chat generation with memory context injection.
"""

import pytest
from unittest.mock import Mock, patch
from app.chat.providers.gemini_chat import GeminiChatProvider, ChatError


class TestGeminiChat:
    """Test Gemini chat provider."""
    
    @pytest.mark.asyncio
    async def test_basic_chat_generation(self):
        """Test basic chat generation without context."""
        mock_response = Mock()
        mock_response.text = "Hello! How can I help you today?"
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiChatProvider(api_key="test-key")
            response = await provider.generate_chat(
                message="Hello",
                context=""
            )
            
            assert response == "Hello! How can I help you today?"
            assert provider.provider_name == "gemini"
    
    @pytest.mark.asyncio
    async def test_chat_with_memory_context(self):
        """Test chat generation with memory context injection."""
        mock_response = Mock()
        mock_response.text = "Since you work at Microsoft, I can help with Azure-related questions!"
        
        context = """# User Memory Context
- user works_at Microsoft
- user prefers short answers"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiChatProvider(api_key="test-key")
            response = await provider.generate_chat(
                message="What can you help me with?",
                context=context
            )
            
            assert "Microsoft" in response
            # Verify context was included in the prompt
            call_args = mock_model.generate_content.call_args
            assert "User Memory Context" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_empty_response_error(self):
        """Test that empty response raises ChatError."""
        mock_response = Mock()
        mock_response.text = ""
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiChatProvider(api_key="test-key")
            
            with pytest.raises(ChatError) as exc_info:
                await provider.generate_chat("Hello", "")
            
            assert "empty response" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test that rate limit errors are properly handled."""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("Rate limit exceeded")
            mock_model_class.return_value = mock_model
            
            provider = GeminiChatProvider(api_key="test-key")
            
            with pytest.raises(ChatError) as exc_info:
                await provider.generate_chat("Hello", "")
            
            assert "rate limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """Test that authentication errors are properly handled."""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("Invalid API key")
            mock_model_class.return_value = mock_model
            
            provider = GeminiChatProvider(api_key="test-key")
            
            with pytest.raises(ChatError) as exc_info:
                await provider.generate_chat("Hello", "")
            
            assert "authentication failed" in str(exc_info.value).lower()
    
    def test_missing_api_key_error(self):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            GeminiChatProvider(api_key="")
        
        assert "GEMINI_API_KEY is required" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
