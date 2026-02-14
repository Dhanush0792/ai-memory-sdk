"""
Chat endpoint with full memory integration.

Flow:
1. Extract user identity
2. Ingest conversation → /memory/ingest
3. Retrieve context → /memory/retrieve
4. Inject context into system prompt
5. Call LLM (OpenAI/Anthropic)
6. Return response
"""

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
import uuid

from app.config import settings
from app.observability import logger, metrics
from app.memory.storage import store_memory
from app.extraction.factory import get_extraction_provider
from app.chat.providers.factory import get_chat_provider
from app.auth.dependencies import get_current_user
from fastapi import Depends


router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=10000)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    user_id: str
    tenant_id: str
    session_id: str
    memories_retrieved: int
    memories_ingested: int
    latency_ms: float


class Memory(BaseModel):
    """Memory model for response."""
    id: str
    subject: str
    predicate: str
    object: str
    confidence: float
    version: int
    scope: str
    created_at: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user_id: str = Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(None),
):
    """
    Chat with AI assistant with full memory integration.
    
    Flow:
    1. Extract/generate user identity
    2. Ingest conversation to memory
    3. Retrieve relevant memories
    4. Inject context into LLM prompt
    5. Return response
    """
    start_time = time.time()
    
    # Extract user identity (priority: JWT > request body > generate)
    user_id = current_user_id or request.user_id or f"user-{uuid.uuid4()}"
    tenant_id = x_tenant_id or request.tenant_id or "default-tenant"
    session_id = request.session_id or f"session-{uuid.uuid4()}"
    
    logger.info(
        "chat_request_received",
        user_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        message_length=len(request.message)
    )
    
    try:
        # Step 1: Ingest conversation to extract memories
        logger.debug("chat_step_1_ingest", user_id=user_id)
        
        extraction_provider = get_extraction_provider()
        extracted_triples = extraction_provider.extract(request.message)
        
        memories_ingested = 0
        for triple in extracted_triples:
            try:
                store_memory(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    triple=triple,
                    source="chat",
                    scope="user"  # Default to user scope
                )
                memories_ingested += 1
            except Exception as e:
                logger.warning(
                    "memory_ingest_failed",
                    user_id=user_id,
                    triple=triple.dict(),
                    error=str(e)
                )
        
        logger.info(
            "chat_memories_ingested",
            user_id=user_id,
            count=memories_ingested
        )
        
        # Step 2: Retrieve relevant memories for context
        logger.debug("chat_step_2_retrieve", user_id=user_id)
        
        memories = storage.retrieve_memories(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=20  # Retrieve top 20 memories
        )
        
        logger.info(
            "chat_memories_retrieved",
            user_id=user_id,
            count=len(memories)
        )
        
        # Step 3: Build context from memories
        context = _build_context_from_memories(memories)
        
        # Step 4: Call LLM with context
        chat_provider_name = settings.get_chat_provider()
        logger.debug("chat_step_3_llm", user_id=user_id, provider=chat_provider_name)
        
        chat_provider = get_chat_provider()
        llm_response = await chat_provider.generate_chat(
            message=request.message,
            context=context
        )
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Track metrics
        metrics.chat_request_total.labels(tenant_id=tenant_id).inc()
        metrics.chat_latency_seconds.labels(tenant_id=tenant_id).observe(latency_ms / 1000)
        if context:
            metrics.chat_memory_injected_total.labels(tenant_id=tenant_id).inc()
        
        logger.info(
            "chat_request_completed",
            user_id=user_id,
            tenant_id=tenant_id,
            latency_ms=latency_ms,
            memories_retrieved=len(memories),
            memories_ingested=memories_ingested
        )
        
        return ChatResponse(
            response=llm_response,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            memories_retrieved=len(memories),
            memories_ingested=memories_ingested,
            latency_ms=latency_ms
        )
        
    except Exception as e:
        logger.error(
            "chat_request_failed",
            user_id=user_id,
            tenant_id=tenant_id,
            error=str(e),
            error_type=type(e).__name__
        )
        
        metrics.chat_error_total.labels(error_type=type(e).__name__).inc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Chat request failed: {str(e)}"
        )


def _build_context_from_memories(memories: List[Dict[str, Any]]) -> str:
    """
    Build context string from memories.
    
    Args:
        memories: List of memory dictionaries
        
    Returns:
        Formatted context string
    """
    if not memories:
        return ""
    
    context_lines = ["# User Memory Context\n"]
    
    for mem in memories:
        # Format: "User [predicate] [object]"
        context_lines.append(
            f"- {mem['subject']} {mem['predicate']} {mem['object']} "
            f"(confidence: {mem['confidence']:.2f}, version: {mem['version']})"
        )
    
    return "\n".join(context_lines)
