"""Memory Extraction Service - Extract structured memories from text using LLM"""

import json
from typing import List, Dict
from .llm_client import create_llm_client


class MemoryExtractor:
    """Extract structured memories from natural language text"""
    
    def __init__(self):
        """Initialize extractor (LLM client created lazily)"""
        self._llm_client = None
    
    @property
    def llm_client(self):
        """Lazy-load LLM client"""
        if self._llm_client is None:
            self._llm_client = create_llm_client()
        return self._llm_client
    
    def extract(self, text: str) -> List[Dict[str, str]]:
        """
        Extract memories from text
        
        Args:
            text: Natural language text to extract from
        
        Returns:
            List of memories: [{"type": "fact", "key": "name", "value": "Alice"}, ...]
        """
        if not text or not text.strip():
            return []
        
        system_prompt = """You are a memory extraction system. Extract structured memories from user messages.

Output ONLY valid JSON array of memories. Each memory must have:
- type: "fact", "preference", or "event"
- key: short identifier (e.g., "name", "diet", "location")
- value: the actual information

Examples:
Input: "My name is Alice and I love pizza"
Output: [{"type": "fact", "key": "name", "value": "Alice"}, {"type": "preference", "key": "food", "value": "loves pizza"}]

Input: "I live in San Francisco"
Output: [{"type": "fact", "key": "location", "value": "San Francisco"}]

Extract ALL relevant information. If no memories found, return empty array [].
Output ONLY the JSON array, no other text."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract memories from: {text}"}
        ]
        
        try:
            response = self.llm_client.get_completion(messages)
            
            # Parse JSON response
            # Try to extract JSON from response (LLM might add extra text)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            memories = json.loads(response)
            
            # Validate structure
            if not isinstance(memories, list):
                return []
            
            validated = []
            for mem in memories:
                if isinstance(mem, dict) and "type" in mem and "key" in mem and "value" in mem:
                    if mem["type"] in ["fact", "preference", "event"]:
                        validated.append(mem)
            
            return validated
            
        except json.JSONDecodeError as e:
            # LLM didn't return valid JSON - propagate error
            raise ValueError(f"Memory extraction JSON parse error: {str(e)}")
        except Exception:
            # Any other error (API failure, etc.) - propagate
            raise
