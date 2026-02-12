"""
Comprehensive test suite for Gemini reliability hardening.
Tests circuit breaker, fallback, token management, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestSafeJSONParsing:
    """Test safe JSON extraction with balanced bracket parser."""
    
    def test_multiple_arrays_in_response(self):
        """Test that only first array is extracted when multiple exist."""
        from app.extraction.providers.gemini_provider import GeminiProvider
        
        mock_response = Mock()
        mock_response.text = """[
  {"subject": "user", "predicate": "likes", "object": "Python", "confidence": 0.9}
]

[
  {"subject": "user", "predicate": "likes", "object": "Java", "confidence": 0.8}
]"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("I like Python and Java")
            
            # Should only extract first array
            assert len(triples) == 1
            assert triples[0].object == "Python"
    
    def test_nested_brackets_in_strings(self):
        """Test that brackets inside strings are ignored."""
        from app.extraction.providers.gemini_provider import GeminiProvider
        
        mock_response = Mock()
        mock_response.text = """[
  {"subject": "user", "predicate": "likes", "object": "arrays [1,2,3]", "confidence": 0.9}
]"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("I like arrays")
            
            assert len(triples) == 1
            assert triples[0].object == "arrays [1,2,3]"
    
    def test_escaped_quotes_in_json(self):
        """Test that escaped quotes are handled correctly."""
        from app.extraction.providers.gemini_provider import GeminiProvider
        
        mock_response = Mock()
        mock_response.text = r"""[
  {"subject": "user", "predicate": "said", "object": "He said \"hello\"", "confidence": 0.9}
]"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("Test")
            
            assert len(triples) == 1
            assert 'hello' in triples[0].object


class TestCircuitBreaker:
    """Test circuit breaker state machine."""
    
    def test_circuit_opens_after_failures(self):
        """Test that circuit opens after threshold failures."""
        from app.extraction.providers.gemini_provider import GeminiProvider, _circuit_breaker, ExtractionError
        
        # Reset circuit breaker
        _circuit_breaker.state = "CLOSED"
        _circuit_breaker.failure_count = 0
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            
            # Trigger 5 failures
            for i in range(5):
                with pytest.raises(ExtractionError):
                    provider.extract("Test")
            
            # Circuit should be OPEN
            assert _circuit_breaker.state == "OPEN"
            
            # Next call should fail immediately without calling API
            with pytest.raises(ExtractionError) as exc_info:
                provider.extract("Test")
            
            assert "circuit breaker" in str(exc_info.value).lower()
    
    def test_circuit_half_open_after_cooldown(self):
        """Test that circuit enters HALF_OPEN after cooldown."""
        from app.extraction.providers.gemini_provider import _circuit_breaker
        
        # Set circuit to OPEN with old failure time
        _circuit_breaker.state = "OPEN"
        _circuit_breaker.failure_count = 5
        _circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=61)
        
        # Should allow attempt (HALF_OPEN)
        assert _circuit_breaker.can_attempt() == True
        assert _circuit_breaker.state == "HALF_OPEN"
    
    def test_circuit_closes_on_success(self):
        """Test that circuit closes on successful call."""
        from app.extraction.providers.gemini_provider import GeminiProvider, _circuit_breaker
        import json
        
        # Set circuit to HALF_OPEN
        _circuit_breaker.state = "HALF_OPEN"
        _circuit_breaker.failure_count = 3
        
        mock_response = Mock()
        mock_response.text = json.dumps([
            {"subject": "user", "predicate": "likes", "object": "Python", "confidence": 0.9}
        ])
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("I like Python")
            
            # Circuit should be CLOSED
            assert _circuit_breaker.state == "CLOSED"
            assert _circuit_breaker.failure_count == 0


class TestTokenManagement:
    """Test token limit and truncation."""
    
    def test_input_truncation(self):
        """Test that oversized input is truncated."""
        from app.extraction.providers.gemini_provider import GeminiProvider
        import json
        
        mock_response = Mock()
        mock_response.text = json.dumps([])
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            provider.max_input_tokens = 100  # Very low limit
            
            # Create very long input
            long_text = "word " * 10000
            
            provider.extract(long_text)
            
            # Check that truncated text was sent
            call_args = mock_model.generate_content.call_args
            sent_text = call_args[0][0]
            
            # Should be truncated (much shorter than original)
            assert len(sent_text) < len(long_text)
    
    def test_token_estimation(self):
        """Test token estimation (4 chars ≈ 1 token)."""
        from app.extraction.providers.gemini_provider import GeminiProvider
        
        with patch('google.generativeai.GenerativeModel'):
            provider = GeminiProvider(api_key="test-key")
            
            # 400 chars should be ~100 tokens
            text = "a" * 400
            tokens = provider._estimate_tokens(text)
            assert tokens == 100


class TestContextTruncation:
    """Test chat context truncation."""
    
    @pytest.mark.asyncio
    async def test_context_truncation_preserves_message(self):
        """Test that user message is preserved when context is truncated."""
        from app.chat.providers.gemini_chat import GeminiChatProvider
        
        mock_response = Mock()
        mock_response.text = "Response"
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiChatProvider(api_key="test-key")
            provider.max_input_tokens = 200  # Low limit
            
            message = "What's my name?"
            context = "Memory: " + ("user likes Python. " * 1000)  # Very long context
            
            response = await provider.generate_chat(message, context)
            
            # Check that prompt contains message
            call_args = mock_model.generate_content.call_args
            sent_prompt = call_args[0][0]
            
            assert "What's my name?" in sent_prompt


class TestFallbackMechanism:
    """Test quota-aware fallback."""
    
    @pytest.mark.asyncio
    async def test_fallback_on_429(self):
        """Test that fallback triggers on rate limit error."""
        from app.chat.providers.factory import FallbackChatProvider
        from app.chat.providers.base import ChatError
        from app.chat.providers.gemini_chat import GeminiChatProvider
        from app.chat.providers.openai_chat import OpenAIChatProvider
        
        # Create mock providers
        primary = Mock(spec=GeminiChatProvider)
        primary.provider_name = "gemini"
        primary.generate_chat = Mock(side_effect=ChatError("Gemini rate limit exceeded: 429"))
        
        fallback = Mock(spec=OpenAIChatProvider)
        fallback.provider_name = "openai"
        fallback.generate_chat = Mock(return_value="Fallback response")
        
        wrapper = FallbackChatProvider(primary, fallback)
        
        # Should fallback to OpenAI
        response = await wrapper.generate_chat("Hello", "")
        
        assert response == "Fallback response"
        assert fallback.generate_chat.called
    
    @pytest.mark.asyncio
    async def test_no_fallback_on_other_errors(self):
        """Test that fallback does NOT trigger on non-rate-limit errors."""
        from app.chat.providers.factory import FallbackChatProvider
        from app.chat.providers.base import ChatError
        
        primary = Mock()
        primary.provider_name = "gemini"
        primary.generate_chat = Mock(side_effect=ChatError("Authentication failed"))
        
        fallback = Mock()
        fallback.provider_name = "openai"
        
        wrapper = FallbackChatProvider(primary, fallback)
        
        # Should re-raise, not fallback
        with pytest.raises(ChatError) as exc_info:
            await wrapper.generate_chat("Hello", "")
        
        assert "Authentication failed" in str(exc_info.value)
        assert not fallback.generate_chat.called


class TestMetricsTracking:
    """Test that metrics are recorded correctly."""
    
    def test_extraction_metrics_recorded(self):
        """Test that extraction metrics are recorded."""
        from app.extraction.providers.gemini_provider import GeminiProvider
        import json
        
        mock_response = Mock()
        mock_response.text = json.dumps([
            {"subject": "user", "predicate": "likes", "object": "Python", "confidence": 0.9},
            {"subject": "user", "predicate": "likes", "object": "Java", "confidence": 0.8}
        ])
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            
            # Mock metrics
            with patch('app.observability.metrics') as mock_metrics:
                mock_metrics.llm_call_latency_seconds = Mock()
                mock_metrics.llm_call_latency_seconds.labels = Mock(return_value=Mock())
                mock_metrics.gemini_extraction_triple_count_histogram = Mock()
                mock_metrics.gemini_extraction_confidence_avg = Mock()
                mock_metrics.gemini_extraction_confidence_avg.labels = Mock(return_value=Mock())
                
                triples = provider.extract("I like Python and Java")
                
                # Verify metrics were called
                assert mock_metrics.llm_call_latency_seconds.labels.called
                assert mock_metrics.gemini_extraction_triple_count_histogram.observe.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
