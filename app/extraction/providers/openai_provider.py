"""
OpenAI provider for memory extraction.
"""

import json
from typing import List
from openai import OpenAI
from app.extraction.providers.base import ExtractionProvider
from app.models import ExtractedTriple


# Extraction prompt template
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


class OpenAIProvider(ExtractionProvider):
    """OpenAI-based extraction provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def model_name(self) -> str:
        return self.model
    
    def extract(self, conversation_text: str) -> List[ExtractedTriple]:
        """
        Extract memories using OpenAI API.
        
        V1.1 HARDENING:
        - Strict JSON parsing
        - Reject non-array responses
        - Validate all fields
        - Clamp confidence
        - Detect duplicates
        """
        if not conversation_text or not conversation_text.strip():
            return []
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise memory extraction system. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT.format(conversation_text=conversation_text)
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # V1.1: Strict JSON parsing (no eval)
            try:
                triples_data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ExtractionError(f"Invalid JSON from LLM: {str(e)}")
            
            # V1.1: Reject non-array responses
            if not isinstance(triples_data, list):
                raise ExtractionError("LLM response must be a JSON array")
            
            triples = []
            errors = []
            seen_triples = set()  # For duplicate detection
            
            for idx, triple_data in enumerate(triples_data):
                # Validate dictionary
                if not isinstance(triple_data, dict):
                    errors.append(f"Triple {idx}: Must be JSON object, got {type(triple_data).__name__}")
                    continue
                
                # V1.1: Validate non-empty fields
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
                
                # V1.1: Validate and clamp confidence
                try:
                    confidence = float(triple_data.get('confidence', 0.8))
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
                except (ValueError, TypeError):
                    errors.append(f"Triple {idx}: Invalid confidence value")
                    continue
                
                # V1.1: Detect duplicates
                triple_key = (subject.lower(), predicate.lower(), obj.lower())
                if triple_key in seen_triples:
                    errors.append(f"Triple {idx}: Duplicate detected")
                    continue
                
                seen_triples.add(triple_key)
                
                # Create validated triple
                triple = ExtractedTriple(
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    confidence=confidence
                )
                triples.append(triple)
            
            # If all triples failed validation, raise error
            if errors and not triples:
                raise ExtractionError(f"All triples failed validation: {'; '.join(errors)}")
            
            return triples
            
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"OpenAI extraction failed: {str(e)}")
