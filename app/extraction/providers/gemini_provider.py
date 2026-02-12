"""
Gemini provider for memory extraction.
Implements robust JSON parsing, token management, circuit breaker, and observability.
"""

import json
import re
import time
from typing import List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from app.extraction.providers.base import ExtractionProvider
from app.config import settings
from app.models import ExtractedTriple


# Extraction prompt (same as other providers for consistency)
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


# Circuit breaker state (in-memory, per-process)
class CircuitBreakerState:
    """Lightweight in-memory circuit breaker for Gemini provider."""
    
    def __init__(self):
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.cooldown_seconds = 60
        self.failure_threshold = 5
    
    def record_success(self):
        """Record successful call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def can_attempt(self) -> bool:
        """Check if we can attempt a call."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # Check if cooldown period has passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.cooldown_seconds:
                    self.state = "HALF_OPEN"
                    return True
            return False
        
        if self.state == "HALF_OPEN":
            return True
        
        return False


# Global circuit breaker instance
_circuit_breaker = CircuitBreakerState()


class GeminiProvider(ExtractionProvider):
    """Gemini-based extraction provider with robust JSON parsing, token management, and circuit breaker."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key
            model: Model to use (default: gemini-1.5-flash)
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name_str = model
        
        # Token limits (configurable via environment)
        self.max_input_tokens = getattr(settings, 'gemini_max_input_tokens', 8000)
        self.max_output_tokens = getattr(settings, 'gemini_max_output_tokens', 1024)
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    @property
    def model_name(self) -> str:
        return self.model_name_str
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (4 chars ≈ 1 token)."""
        return len(text) // 4
    
    def _truncate_to_token_limit(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        estimated_tokens = self._estimate_tokens(text)
        if estimated_tokens <= max_tokens:
            return text
        
        # Truncate to approximate character count
        max_chars = max_tokens * 4
        return text[:max_chars]
    
    def _clean_json_response(self, content: str) -> str:
        """
        Clean Gemini response to extract valid JSON using safe parsing.
        
        Gemini often returns:
        - Markdown-wrapped JSON: ```json\n[...]\n```
        - JSON with trailing commentary
        - Mixed content with JSON embedded
        - Multiple JSON arrays
        
        Args:
            content: Raw response from Gemini
            
        Returns:
            Cleaned JSON string
            
        Raises:
            ExtractionError: If no valid JSON found
        """
        content = content.strip()
        
        # Strategy 1: Strip markdown code fences
        if content.startswith("```"):
            # Remove opening fence (```json or ```)
            content = re.sub(r'^```(?:json)?\s*\n?', '', content)
            # Remove closing fence
            content = re.sub(r'\n?```\s*$', '', content)
            content = content.strip()
        
        # Strategy 2: Extract first valid JSON array using balanced bracket parsing
        # This is safer than greedy regex and handles nested brackets correctly
        start_idx = content.find('[')
        if start_idx == -1:
            raise ExtractionError(
                f"No JSON array found in Gemini response. "
                f"Response preview: {content[:100]}..."
            )
        
        # Parse balanced brackets manually
        bracket_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start_idx, len(content)):
            char = content[i]
            
            # Handle string escaping
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            # Track string boundaries (ignore brackets inside strings)
            if char == '"':
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            # Count brackets
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                
                # Found matching closing bracket
                if bracket_count == 0:
                    json_str = content[start_idx:i+1]
                    return json_str
        
        # If we get here, brackets were unbalanced
        raise ExtractionError(
            f"Unbalanced brackets in Gemini response. "
            f"Response preview: {content[:200]}..."
        )
    
    def extract(self, conversation_text: str) -> List[ExtractedTriple]:
        """
        Extract memories using Gemini API.
        
        Implements production-grade hardening:
        - Circuit breaker
        - Token management
        - Strict JSON parsing
        - Comprehensive metrics
        - Reject non-array responses
        - Validate all fields
        - Clamp confidence
        - Detect duplicates
        """
        if not conversation_text or not conversation_text.strip():
            return []
        
        # Import metrics here to avoid circular dependency
        from app.observability import metrics, logger
        
        # Check circuit breaker
        if not _circuit_breaker.can_attempt():
            logger.warning(
                "gemini_circuit_open",
                state=_circuit_breaker.state,
                failure_count=_circuit_breaker.failure_count
            )
            # Increment circuit open metric
            try:
                metrics.gemini_circuit_open_total.inc()
            except AttributeError:
                pass  # Metric not yet defined
            
            raise ExtractionError(
                f"Gemini circuit breaker is {_circuit_breaker.state}. "
                f"Service temporarily unavailable."
            )
        
        # Truncate input to token limit
        truncated_text = self._truncate_to_token_limit(
            conversation_text,
            self.max_input_tokens
        )
        
        if len(truncated_text) < len(conversation_text):
            logger.info(
                "gemini_input_truncated",
                original_tokens=self._estimate_tokens(conversation_text),
                truncated_tokens=self._estimate_tokens(truncated_text)
            )
        
        start_time = time.time()
        
        try:
            # Call Gemini API with token limits
            response = self.model.generate_content(
                EXTRACTION_PROMPT.format(conversation_text=truncated_text),
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=self.max_output_tokens,
                )
            )
            
            # Extract text from response
            if not response.text:
                raise ExtractionError("Gemini returned empty response")
            
            content = response.text.strip()
            
            # Clean JSON response (handle markdown wrapping, etc.)
            cleaned_content = self._clean_json_response(content)
            
            # Strict JSON parsing (no eval)
            try:
                triples_data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                # Increment JSON parse failure metric
                try:
                    metrics.gemini_json_parse_failures_total.inc()
                except AttributeError:
                    pass
                
                raise ExtractionError(
                    f"Invalid JSON from Gemini after cleaning: {str(e)}. "
                    f"Cleaned content: {cleaned_content[:200]}..."
                )
            
            # Reject non-array responses
            if not isinstance(triples_data, list):
                try:
                    metrics.gemini_json_parse_failures_total.inc()
                except AttributeError:
                    pass
                
                raise ExtractionError(
                    f"Gemini response must be a JSON array, got {type(triples_data).__name__}"
                )
            
            triples = []
            errors = []
            seen_triples = set()  # For duplicate detection
            confidence_values = []
            
            for idx, triple_data in enumerate(triples_data):
                # Validate dictionary
                if not isinstance(triple_data, dict):
                    errors.append(
                        f"Triple {idx}: Must be JSON object, got {type(triple_data).__name__}"
                    )
                    continue
                
                # Validate non-empty fields
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
                
                # Validate and clamp confidence
                try:
                    confidence = float(triple_data.get('confidence', 0.8))
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
                    confidence_values.append(confidence)
                except (ValueError, TypeError):
                    errors.append(f"Triple {idx}: Invalid confidence value")
                    continue
                
                # Detect duplicates
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
                raise ExtractionError(
                    f"All triples failed validation: {'; '.join(errors)}"
                )
            
            # Record success
            _circuit_breaker.record_success()
            
            # Calculate metrics
            duration = time.time() - start_time
            triple_count = len(triples)
            avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
            
            # Record comprehensive metrics
            try:
                # Latency
                metrics.llm_call_latency_seconds.labels(
                    provider="gemini",
                    type="extraction"
                ).observe(duration)
                
                # Triple count histogram
                metrics.gemini_extraction_triple_count_histogram.observe(triple_count)
                
                # Average confidence
                metrics.gemini_extraction_confidence_avg.labels(
                    provider="gemini"
                ).set(avg_confidence)
            except AttributeError:
                pass  # Metrics not yet defined
            
            logger.info(
                "gemini_extraction_success",
                duration=duration,
                triple_count=triple_count,
                avg_confidence=avg_confidence
            )
            
            return triples
            
        except ExtractionError:
            # Record failure
            _circuit_breaker.record_failure()
            
            try:
                metrics.gemini_failure_total.inc()
            except AttributeError:
                pass
            
            raise
        except Exception as e:
            # Record failure
            _circuit_breaker.record_failure()
            
            try:
                metrics.gemini_failure_total.inc()
            except AttributeError:
                pass
            
            # Handle API errors
            error_msg = str(e).lower()
            
            # Check for rate limiting (429)
            if 'rate limit' in error_msg or 'quota' in error_msg or '429' in error_msg:
                raise ExtractionError(f"Gemini rate limit exceeded: {str(e)}")
            
            # Check for authentication errors
            if 'api key' in error_msg or 'authentication' in error_msg or 'permission' in error_msg:
                raise ExtractionError(f"Gemini authentication failed: {str(e)}")
            
            # Generic error
            raise ExtractionError(f"Gemini extraction failed: {str(e)}")
