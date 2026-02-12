"""
Anthropic Claude provider for memory extraction.
"""

import json
from typing import List
from anthropic import Anthropic
from app.extraction.providers.base import ExtractionProvider
from app.models import ExtractedTriple


# Extraction prompt (same as OpenAI)
EXTRACTION_PROMPT = """You are a memory extraction system. Your task is to extract structured facts from conversational text.

Extract facts as subject-predicate-object triples where:
- subject: The entity the fact is about (e.g., "user", "manager", "preference")
- predicate: The relationship or attribute (e.g., "prefers", "is", "likes", "works_with")
- object: The value or related entity (e.g., "short explanations", "Ravi", "Python")

Rules:
1. Extract only explicit facts stated in the text
2. Use simple, clear predicates
3. Keep subjects and predicates concise
4. Each triple should be atomic (one fact)
5. Return ONLY valid JSON, no additional text

Input: "{conversation_text}"

Output format (JSON array):
[
  {{"subject": "user", "predicate": "prefers", "object": "short explanations", "confidence": 0.9}},
  {{"subject": "user_manager", "predicate": "is", "object": "Ravi", "confidence": 0.95}}
]

Extract all facts now:"""


class ExtractionError(Exception):
    """Raised when extraction fails."""
    pass


class AnthropicProvider(ExtractionProvider):
    """Anthropic Claude-based extraction provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-5-sonnet)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def model_name(self) -> str:
        return self.model
    
    def extract(self, conversation_text: str) -> List[ExtractedTriple]:
        """Extract memories using Anthropic Claude API."""
        if not conversation_text or not conversation_text.strip():
            return []
        
        try:
            # Call Anthropic API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT.format(conversation_text=conversation_text)
                    }
                ]
            )
            
            content = response.content[0].text.strip()
            
            # Strict JSON parsing
            try:
                triples_data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ExtractionError(f"Invalid JSON from Claude: {str(e)}")
            
            # Reject non-array responses
            if not isinstance(triples_data, list):
                raise ExtractionError("Claude response must be a JSON array")
            
            triples = []
            errors = []
            seen_triples = set()
            
            for idx, triple_data in enumerate(triples_data):
                if not isinstance(triple_data, dict):
                    errors.append(f"Triple {idx}: Must be JSON object")
                    continue
                
                subject = triple_data.get('subject', '').strip()
                if not subject:
                    errors.append(f"Triple {idx}: 'subject' is empty")
                    continue
                
                predicate = triple_data.get('predicate', '').strip()
                if not predicate:
                    errors.append(f"Triple {idx}: 'predicate' is empty")
                    continue
                
                obj = triple_data.get('object', '').strip()
                if not obj:
                    errors.append(f"Triple {idx}: 'object' is empty")
                    continue
                
                try:
                    confidence = float(triple_data.get('confidence', 0.8))
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, TypeError):
                    errors.append(f"Triple {idx}: Invalid confidence")
                    continue
                
                triple_key = (subject.lower(), predicate.lower(), obj.lower())
                if triple_key in seen_triples:
                    errors.append(f"Triple {idx}: Duplicate")
                    continue
                
                seen_triples.add(triple_key)
                
                triple = ExtractedTriple(
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    confidence=confidence
                )
                triples.append(triple)
            
            if errors and not triples:
                raise ExtractionError(f"All triples failed validation: {'; '.join(errors)}")
            
            return triples
            
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Anthropic extraction failed: {str(e)}")
