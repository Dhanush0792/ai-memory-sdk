"""LLM Client Abstraction - OpenAI and Anthropic support"""

import os
from typing import List, Dict, Optional


class LLMClient:
    """Abstract LLM client interface"""
    
    def get_completion(self, messages: List[Dict[str, str]]) -> str:
        """Get completion from LLM"""
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI client implementation"""
    
    def __init__(self, api_key: str):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
    
    def get_completion(self, messages: List[Dict[str, str]]) -> str:
        """Get completion from OpenAI"""
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content


class AnthropicClient(LLMClient):
    """Anthropic client implementation"""
    
    def __init__(self, api_key: str):
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
    
    def get_completion(self, messages: List[Dict[str, str]]) -> str:
        """Get completion from Anthropic"""
        # Convert OpenAI format to Anthropic format
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_messages = [m for m in messages if m["role"] != "system"]
        
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=system_msg,
            messages=user_messages
        )
        return response.content[0].text


def create_llm_client() -> LLMClient:
    """
    Create LLM client based on available API keys
    
    Checks environment for OPENAI_API_KEY or ANTHROPIC_API_KEY.
    Returns first available client.
    
    Raises:
        ValueError: If no API keys are configured
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if openai_key:
        return OpenAIClient(openai_key)
    elif anthropic_key:
        return AnthropicClient(anthropic_key)
    else:
        raise ValueError(
            "No LLM API key configured. "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file."
        )
