"""
LLM-based memory extraction engine.
Converts conversational text into structured subject-predicate-object triples.
"""

import json
from typing import List
from openai import OpenAI
from app.config import settings
from app.models import ExtractedTriple


# Initialize OpenAI client
client = OpenAI(api_key=settings.openai_api_key)


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


def extract_memories(conversation_text: str) -> List[ExtractedTriple]:
    """
    Extract structured memories from conversation text using LLM.
    
    V1.1 HARDENING:
    - Strict JSON parsing (no eval, only json.loads)
    - Reject non-array responses
    - Validate all fields non-empty
    - Clamp confidence to [0, 1]
    - Detect and reject duplicate triples
    
    Args:
        conversation_text: The conversation text to extract from
        
    Returns:
        List of extracted triples
        
    Raises:
        ExtractionError: If extraction fails or validation fails
    """
    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise memory extraction system. Extract facts as JSON only."
                },
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(conversation_text=conversation_text)
                }
            ],
            temperature=0.1,  # Low temperature for consistency
            max_tokens=1000,
        )
        
        # Extract response content
        content = response.choices[0].message.content.strip()
        
        # STRICT JSON PARSING (no eval, only json.loads)
        try:
            # Handle potential markdown code blocks
            if content.startswith("```"):
                # Extract JSON from code block
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            # Use only json.loads for safety
            triples_data = json.loads(content)
            
            # REJECT NON-ARRAY RESPONSES
            if not isinstance(triples_data, list):
                raise ExtractionError(
                    f"LLM response must be a JSON array, got {type(triples_data).__name__}"
                )
            
            if len(triples_data) == 0:
                raise ExtractionError("LLM returned empty array")
            
        except json.JSONDecodeError as e:
            raise ExtractionError(
                f"Failed to parse LLM response as JSON: {e}\n"
                f"Response content: {content[:200]}..."
            )
        
        # VALIDATE AND CONVERT TO PYDANTIC MODELS
        triples = []
        errors = []
        seen_triples = set()  # For duplicate detection
        
        for idx, triple_data in enumerate(triples_data):
            try:
                # Validate it's a dictionary
                if not isinstance(triple_data, dict):
                    errors.append(f"Triple {idx}: Must be a JSON object, got {type(triple_data).__name__}")
                    continue
                
                # VALIDATE NON-EMPTY FIELDS
                subject = triple_data.get('subject', '').strip()
                predicate = triple_data.get('predicate', '').strip()
                obj = triple_data.get('object', '').strip()
                
                if not subject:
                    errors.append(f"Triple {idx}: 'subject' is empty or missing")
                    continue
                
                if not predicate:
                    errors.append(f"Triple {idx}: 'predicate' is empty or missing")
                    continue
                
                if not obj:
                    errors.append(f"Triple {idx}: 'object' is empty or missing")
                    continue
                
                # VALIDATE AND CLAMP CONFIDENCE
                confidence = triple_data.get('confidence', 0.8)
                
                try:
                    confidence = float(confidence)
                except (TypeError, ValueError):
                    errors.append(f"Triple {idx}: 'confidence' must be a number, got {confidence}")
                    continue
                
                # Clamp confidence to [0, 1]
                if confidence < 0.0:
                    confidence = 0.0
                elif confidence > 1.0:
                    confidence = 1.0
                
                # DETECT DUPLICATES
                triple_key = (subject.lower(), predicate.lower(), obj.lower())
                if triple_key in seen_triples:
                    errors.append(
                        f"Triple {idx}: Duplicate detected - "
                        f"({subject}, {predicate}, {obj})"
                    )
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
                
            except Exception as e:
                errors.append(f"Triple {idx}: Validation failed - {e}")
        
        # FAIL IF ALL TRIPLES INVALID
        if errors and not triples:
            raise ExtractionError(
                f"All {len(triples_data)} triples failed validation:\n" +
                "\n".join(errors)
            )
        
        # FAIL IF NO VALID TRIPLES
        if not triples:
            raise ExtractionError("No valid triples extracted from conversation")
        
        # Log warnings for partial failures
        if errors:
            print(f"WARNING: {len(errors)} triples failed validation:", flush=True)
            for error in errors:
                print(f"  - {error}", flush=True)
        
        return triples
        
    except Exception as e:
        if isinstance(e, ExtractionError):
            raise
        raise ExtractionError(f"Extraction failed: {str(e)}")
