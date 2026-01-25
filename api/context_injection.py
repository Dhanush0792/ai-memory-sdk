"""Context Injection Engine - MANDATORY FEATURE"""

from typing import Optional
from datetime import datetime
import tiktoken

class ContextInjector:
    """Generates LLM-ready context from memories"""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """Initialize with token encoder"""
        self.encoder = tiktoken.get_encoding(encoding_name)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoder.encode(text))
    
    def build_context(
        self,
        memories: list[dict],
        query: Optional[str] = None,
        max_tokens: int = 2000,
        memory_types: Optional[list[str]] = None
    ) -> str:
        """Build token-bounded, relevance-filtered context
        
        Args:
            memories: List of memory objects
            query: Optional query for relevance filtering
            max_tokens: Maximum tokens allowed
            memory_types: Optional filter by memory types
            
        Returns:
            LLM-ready context string
        """
        # Filter by type if specified
        if memory_types:
            memories = [m for m in memories if m.get("type") in memory_types]
        
        # Filter expired memories
        now = datetime.utcnow()
        active_memories = []
        for m in memories:
            if m.get("expires_at"):
                try:
                    expires = datetime.fromisoformat(m["expires_at"].replace("Z", "+00:00"))
                    if expires > now:
                        active_memories.append(m)
                except (ValueError, TypeError, KeyError):
                    # Invalid date format - include memory anyway
                    active_memories.append(m)
            else:
                active_memories.append(m)
        
        # Sort by relevance if query provided
        if query:
            scored_memories = self._score_relevance(active_memories, query)
        else:
            # Sort by created_at descending (most recent first)
            scored_memories = sorted(
                active_memories,
                key=lambda m: m.get("created_at", ""),
                reverse=True
            )
        
        # Build context within token limit
        context_parts = ["# User Memory Context\n"]
        current_tokens = self.count_tokens(context_parts[0])
        
        # Group by type
        facts = []
        preferences = []
        events = []
        
        for memory in scored_memories:
            mem_type = memory.get("type", "fact")
            content = memory.get("content", "")
            
            if mem_type == "fact":
                facts.append(content)
            elif mem_type == "preference":
                preferences.append(content)
            elif mem_type == "event":
                events.append(content)
        
        # Add sections in order: preferences, facts, events
        sections = [
            ("## User Preferences\n", preferences),
            ("## Known Facts\n", facts),
            ("## Recent Events\n", events)
        ]
        
        for header, items in sections:
            if not items:
                continue
            
            section_tokens = self.count_tokens(header)
            if current_tokens + section_tokens > max_tokens:
                break
            
            context_parts.append(header)
            current_tokens += section_tokens
            
            for item in items:
                item_text = f"- {item}\n"
                item_tokens = self.count_tokens(item_text)
                
                if current_tokens + item_tokens > max_tokens:
                    break
                
                context_parts.append(item_text)
                current_tokens += item_tokens
        
        return "".join(context_parts)
    
    def _score_relevance(self, memories: list[dict], query: str) -> list[dict]:
        """Simple relevance scoring based on keyword overlap"""
        query_words = set(query.lower().split())
        
        scored = []
        for memory in memories:
            content = memory.get("content", "").lower()
            content_words = set(content.split())
            
            # Simple Jaccard similarity
            intersection = query_words & content_words
            union = query_words | content_words
            
            score = len(intersection) / len(union) if union else 0
            scored.append((score, memory))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [m for _, m in scored]
