"""
Test suite for Gemini extraction provider.
Tests extraction, JSON edge cases, and error scenarios.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from app.extraction.providers.gemini_provider import GeminiProvider, ExtractionError
from app.models import ExtractedTriple


class TestGeminiExtraction:
    """Test Gemini extraction provider."""
    
    def test_basic_extraction(self):
        """Test basic memory extraction from conversation."""
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.text = json.dumps([
            {"subject": "user", "predicate": "works_at", "object": "Microsoft", "confidence": 0.95},
            {"subject": "user", "predicate": "prefers", "object": "short answers", "confidence": 0.9}
        ])
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key", model="gemini-1.5-flash")
            triples = provider.extract("I work at Microsoft and prefer short answers")
            
            assert len(triples) == 2
            assert triples[0].subject == "user"
            assert triples[0].predicate == "works_at"
            assert triples[0].object == "Microsoft"
            assert triples[0].confidence == 0.95
            
            assert triples[1].subject == "user"
            assert triples[1].predicate == "prefers"
            assert triples[1].object == "short answers"
            assert triples[1].confidence == 0.9
    
    def test_markdown_wrapped_json(self):
        """Test handling of markdown-wrapped JSON response."""
        # Mock Gemini returning markdown-wrapped JSON
        mock_response = Mock()
        mock_response.text = """```json
[
  {"subject": "user", "predicate": "likes", "object": "Python", "confidence": 0.9}
]
```"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("I like Python")
            
            assert len(triples) == 1
            assert triples[0].object == "Python"
    
    def test_json_with_trailing_commentary(self):
        """Test handling of JSON with trailing commentary."""
        mock_response = Mock()
        mock_response.text = """[
  {"subject": "user", "predicate": "is", "object": "engineer", "confidence": 0.85}
]

I extracted one fact about the user being an engineer."""
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("I am an engineer")
            
            assert len(triples) == 1
            assert triples[0].object == "engineer"
    
    def test_malformed_json_error(self):
        """Test that malformed JSON raises ExtractionError."""
        mock_response = Mock()
        mock_response.text = "This is not valid JSON at all"
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            
            with pytest.raises(ExtractionError) as exc_info:
                provider.extract("Some text")
            
            assert "Could not extract valid JSON" in str(exc_info.value)
    
    def test_non_array_json_error(self):
        """Test that non-array JSON raises ExtractionError."""
        mock_response = Mock()
        mock_response.text = '{"error": "not an array"}'
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            
            with pytest.raises(ExtractionError) as exc_info:
                provider.extract("Some text")
            
            assert "must be a JSON array" in str(exc_info.value)
    
    def test_empty_conversation_returns_empty_list(self):
        """Test that empty conversation returns empty list."""
        with patch('google.generativeai.GenerativeModel'):
            provider = GeminiProvider(api_key="test-key")
            
            assert provider.extract("") == []
            assert provider.extract("   ") == []
    
    def test_confidence_clamping(self):
        """Test that confidence values are clamped to [0, 1]."""
        mock_response = Mock()
        mock_response.text = json.dumps([
            {"subject": "user", "predicate": "likes", "object": "coffee", "confidence": 1.5},
            {"subject": "user", "predicate": "dislikes", "object": "tea", "confidence": -0.2}
        ])
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("I like coffee but dislike tea")
            
            assert len(triples) == 2
            assert triples[0].confidence == 1.0  # Clamped from 1.5
            assert triples[1].confidence == 0.0  # Clamped from -0.2
    
    def test_duplicate_detection(self):
        """Test that duplicate triples are filtered out."""
        mock_response = Mock()
        mock_response.text = json.dumps([
            {"subject": "user", "predicate": "likes", "object": "Python", "confidence": 0.9},
            {"subject": "User", "predicate": "LIKES", "object": "python", "confidence": 0.85}
        ])
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("I like Python")
            
            # Should only return one triple (duplicate filtered)
            assert len(triples) == 1
    
    def test_empty_field_validation(self):
        """Test that triples with empty fields are rejected."""
        mock_response = Mock()
        mock_response.text = json.dumps([
            {"subject": "", "predicate": "likes", "object": "Python", "confidence": 0.9},
            {"subject": "user", "predicate": "", "object": "Python", "confidence": 0.9},
            {"subject": "user", "predicate": "likes", "object": "", "confidence": 0.9},
            {"subject": "user", "predicate": "likes", "object": "Java", "confidence": 0.8}
        ])
        
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            triples = provider.extract("I like Java")
            
            # Only the valid triple should be returned
            assert len(triples) == 1
            assert triples[0].object == "Java"
    
    def test_provider_properties(self):
        """Test provider name and model name properties."""
        with patch('google.generativeai.GenerativeModel'):
            provider = GeminiProvider(api_key="test-key", model="gemini-1.5-pro")
            
            assert provider.provider_name == "gemini"
            assert provider.model_name == "gemini-1.5-pro"
    
    def test_missing_api_key_error(self):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            GeminiProvider(api_key="", model="gemini-1.5-flash")
        
        assert "GEMINI_API_KEY is required" in str(exc_info.value)


class TestGeminiErrorHandling:
    """Test Gemini error handling scenarios."""
    
    def test_rate_limit_error(self):
        """Test that rate limit errors are properly handled."""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("Rate limit exceeded")
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            
            with pytest.raises(ExtractionError) as exc_info:
                provider.extract("Some text")
            
            assert "rate limit" in str(exc_info.value).lower()
    
    def test_authentication_error(self):
        """Test that authentication errors are properly handled."""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("Invalid API key")
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            
            with pytest.raises(ExtractionError) as exc_info:
                provider.extract("Some text")
            
            assert "authentication failed" in str(exc_info.value).lower()
    
    def test_generic_api_error(self):
        """Test that generic API errors are properly handled."""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("Unknown error")
            mock_model_class.return_value = mock_model
            
            provider = GeminiProvider(api_key="test-key")
            
            with pytest.raises(ExtractionError) as exc_info:
                provider.extract("Some text")
            
            assert "Gemini extraction failed" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
