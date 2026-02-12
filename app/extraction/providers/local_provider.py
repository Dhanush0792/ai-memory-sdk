"""
Local LLM provider stub for memory extraction.
Supports local LLM endpoints (Ollama, vLLM, etc.)
"""

import json
import requests
from typing import List
from app.extraction.providers.base import ExtractionProvider
from app.models import ExtractedTriple


EXTRACTION_PROMPT = """You are a memory extraction system. Extract structured facts from conversational text.

Extract facts as subject-predicate-object triples where:
- subject: The entity the fact is about
- predicate: The relationship or attribute
- object: The value or related entity

Return ONLY valid JSON array format:
[{{"subject": "user", "predicate": "prefers", "object": "short explanations", "confidence": 0.9}}]

Input: "{conversation_text}"

Extract all facts now:"""


class ExtractionError(Exception):
    """Raised when extraction fails."""
    pass


class LocalLLMProvider(ExtractionProvider):
    """
    Local LLM provider for memory extraction.
    
    Supports OpenAI-compatible endpoints (Ollama, vLLM, etc.)
    """
    
    def __init__(self, endpoint: str, model: str = "llama2"):
        """
        Initialize local LLM provider.
        
        Args:
            endpoint: Local LLM endpoint URL (e.g., http://localhost:11434/api/generate)
            model: Model name (e.g., llama2, mistral)
        """
        self.endpoint = endpoint
        self.model = model
    
    @property
    def provider_name(self) -> str:
        return "local"
    
    @property
    def model_name(self) -> str:
        return self.model
    
    def extract(self, conversation_text: str) -> List[ExtractedTriple]:
        """Extract memories using local LLM."""
        if not conversation_text or not conversation_text.strip():
            return []
        
        try:
            # Call local LLM endpoint (Ollama format)
            response = requests.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": EXTRACTION_PROMPT.format(conversation_text=conversation_text),
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                raise ExtractionError(f"Local LLM returned {response.status_code}")
            
            result = response.json()
            content = result.get('response', '').strip()
            
            # Parse JSON
            try:
                triples_data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ExtractionError(f"Invalid JSON from local LLM: {str(e)}")
            
            if not isinstance(triples_data, list):
                raise ExtractionError("Local LLM response must be JSON array")
            
            triples = []
            errors = []
            seen_triples = set()
            
            for idx, triple_data in enumerate(triples_data):
                if not isinstance(triple_data, dict):
                    errors.append(f"Triple {idx}: Must be JSON object")
                    continue
                
                subject = triple_data.get('subject', '').strip()
                predicate = triple_data.get('predicate', '').strip()
                obj = triple_data.get('object', '').strip()
                
                if not subject or not predicate or not obj:
                    errors.append(f"Triple {idx}: Empty field")
                    continue
                
                try:
                    confidence = float(triple_data.get('confidence', 0.7))
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, TypeError):
                    confidence = 0.7
                
                triple_key = (subject.lower(), predicate.lower(), obj.lower())
                if triple_key in seen_triples:
                    continue
                
                seen_triples.add(triple_key)
                
                triple = ExtractedTriple(
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    confidence=confidence
                )
                triples.append(triple)
            
            return triples
            
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Local LLM extraction failed: {str(e)}")
