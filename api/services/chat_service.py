"""Chat Service - Orchestrates chat flow with memory integration"""

from typing import List, Dict
from .llm_client import create_llm_client
from .memory_extractor import MemoryExtractor


class ChatService:
    """Orchestrates chat with memory retrieval, LLM, and extraction"""
    
    def __init__(self):
        """Initialize chat service (LLM client created lazily)"""
        self._llm_client = None
        self._extractor = None
    
    @property
    def llm_client(self):
        """Lazy-load LLM client"""
        if self._llm_client is None:
            self._llm_client = create_llm_client()
        return self._llm_client
    
    @property
    def extractor(self):
        """Lazy-load memory extractor"""
        if self._extractor is None:
            self._extractor = MemoryExtractor()
        return self._extractor
    
    def build_memory_context(self, memories: List[Dict]) -> str:
        """Build context string from memories"""
        if not memories:
            return ""
        
        context = "\\n\\nWhat you know about this user:\\n"
        for mem in memories:
            # Extract content from memory
            content = mem.get("content", "")
            mem_type = mem.get("type", "fact")
            
            # Format based on type
            if mem_type == "preference":
                context += f"- Preference: {content}\\n"
            elif mem_type == "event":
                context += f"- Event: {content}\\n"
            else:  # fact
                context += f"- {content}\\n"
        
        return context
    
    def chat(
        self,
        message: str,
        memories: List[Dict],
        auto_save: bool = True
    ) -> Dict:
        """
        Process chat message with memory integration
        
        Args:
            message: User message
            memories: Retrieved memories for context
            auto_save: Whether to extract and return new memories
        
        Returns:
            {
                "response": str,
                "extracted_memories": List[Dict] (if auto_save=True)
            }
        """
        # Build context from memories
        memory_context = self.build_memory_context(memories)
        
        # Build system prompt
        system_prompt = f"""You are a helpful AI assistant with memory.
You remember information about users across conversations.{memory_context}

Respond naturally and reference relevant memories when appropriate."""
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        # Get LLM response
        response = self.llm_client.get_completion(messages)
        
        result = {"response": response}
        
        # Extract memories if requested
        if auto_save:
            extracted = self.extractor.extract(message)
            result["extracted_memories"] = extracted
        
        return result
