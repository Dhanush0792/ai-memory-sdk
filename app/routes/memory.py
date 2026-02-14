"""
Memory API routes with V1.1 hardening.
All endpoints require authentication and include audit logging + rate limiting.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from app.models import (
    MemoryIngestRequest,
    MemoryIngestResponse,
    MemoryRetrieveRequest,
    MemoryRetrieveResponse,
    MemoryDeleteResponse,
    MemoryObject,
)
# from app.middleware.auth import verify_api_key  # Deprecated in V2
from app.auth.dependencies import get_current_user
from app.middleware.rate_limiter import rate_limit_middleware
from app.memory.extractor import extract_memories, ExtractionError
from app.memory.storage import (
    store_memories_batch,
    delete_memory,
    get_memory_by_id,
    StorageError
)
from app.memory.retrieval import retrieve_memories, RetrievalError
from app.audit import log_action


router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/ingest", response_model=MemoryIngestResponse)
async def ingest_memory(
    request: MemoryIngestRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Ingest conversation text and extract structured memories.
    
    V1.1 HARDENING:
    - Rate limiting applied
    - Audit logging (success/failure)
    - Hardened extraction validation
    - Transaction-safe storage
    
    Process:
    1. Check rate limit
    2. Extract subject-predicate-object triples using LLM
    3. Validate extracted triples (strict)
    4. Store in database with atomic versioning
    5. Log action to audit trail
    6. Return stored memories
    
    Requires: X-API-Key header
    """
    # V1.1: Rate limiting
    await rate_limit_middleware(None, user_id)
    
    try:
        # Extract memories from conversation
        triples = extract_memories(request.conversation_text)
        
        if not triples:
            # V1.1: Audit log failure
            log_action(
                tenant_id=request.tenant_id,
                action_type="INGEST",
                api_key="jwt_auth",  # Placeholder for legacy field
                success=False,
                user_id=user_id,
                metadata={"reason": "no_triples_extracted"},
                error_message="No memories extracted from conversation"
            )
            
            return MemoryIngestResponse(
                status="failure",
                memories=[],
                message="No memories extracted from conversation",
            )
        
        # Store memories with versioning
        stored_memories = store_memories_batch(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            triples=triples,
            source="conversation"
        )
        
        # V1.1: Audit log success
        for memory in stored_memories:
            log_action(
                tenant_id=request.tenant_id,
                action_type="INGEST",
                api_key=api_key,
                success=True,
                user_id=request.user_id,
                memory_id=memory.id,
                metadata={
                    "subject": memory.subject,
                    "predicate": memory.predicate,
                    "version": memory.version
                }
            )
        
        return MemoryIngestResponse(
            status="success",
            memories=stored_memories,
            message=f"Successfully stored {len(stored_memories)} memories"
        )
        
    except ExtractionError as e:
        # V1.1: Audit log extraction failure
        log_action(
            tenant_id=request.tenant_id,
            action_type="INGEST",
            api_key=api_key,
            success=False,
            user_id=request.user_id,
            metadata={"error_type": "extraction_error"},
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Extraction failed: {str(e)}"
        )
    except StorageError as e:
        # V1.1: Audit log storage failure
        log_action(
            tenant_id=request.tenant_id,
            action_type="INGEST",
            api_key=api_key,
            success=False,
            user_id=request.user_id,
            metadata={"error_type": "storage_error"},
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage failed: {str(e)}"
        )
    except Exception as e:
        # V1.1: Audit log unexpected failure
        log_action(
            tenant_id=request.tenant_id,
            action_type="INGEST",
            api_key=api_key,
            success=False,
            user_id=request.user_id,
            metadata={"error_type": "unexpected_error"},
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/retrieve", response_model=MemoryRetrieveResponse)
async def retrieve_memory(
    tenant_id: str,
    query: str,
    limit: int = 10,
    user_id: str = Depends(get_current_user)
):
    """
    Retrieve memories with deterministic relevance ranking.
    
    V1.1 HARDENING:
    - Rate limiting applied
    - Audit logging
    - Deterministic ranking algorithm
    
    Filters by:
    - tenant_id
    - user_id
    - is_active = true
    
    Ranks by:
    - Exact match (+10)
    - Partial match (+5 per token)
    - Confidence (×5.0)
    - Recency (decay 0.1/day)
    
    Requires: X-API-Key header
    """
    # V1.1: Rate limiting
    await rate_limit_middleware(None, api_key)
    
    try:
        # Validate limit
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )
        
        # Retrieve memories
        memories = retrieve_memories(
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        # V1.1: Audit log retrieval
        log_action(
            tenant_id=tenant_id,
            action_type="RETRIEVE",
            api_key=api_key,
            success=True,
            user_id=user_id,
            metadata={
                "query": query,
                "limit": limit,
                "results_count": len(memories)
            }
        )
        
        return MemoryRetrieveResponse(
            memories=memories,
            total=len(memories)
        )
        
    except RetrievalError as e:
        # V1.1: Audit log failure
        log_action(
            tenant_id=tenant_id,
            action_type="RETRIEVE",
            api_key=api_key,
            success=False,
            user_id=user_id,
            metadata={"query": query},
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval failed: {str(e)}"
        )
    except Exception as e:
        # V1.1: Audit log unexpected failure
        log_action(
            tenant_id=tenant_id,
            action_type="RETRIEVE",
            api_key=api_key,
            success=False,
            user_id=user_id,
            metadata={"query": query},
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory_endpoint(
    memory_id: UUID,
    user_id: str = Depends(get_current_user)
):
    """
    Soft delete a memory (set is_active=false).
    
    V1.1 HARDENING:
    - Rate limiting applied
    - Audit logging
    
    Preserves version history.
    
    Requires: X-API-Key header
    """
    # V1.1: Rate limiting
    await rate_limit_middleware(None, api_key)
    
    try:
        # Check if memory exists
        memory = get_memory_by_id(memory_id)
        
        if not memory:
            # V1.1: Audit log not found
            log_action(
                tenant_id="unknown",
                action_type="DELETE",
                api_key=api_key,
                success=False,
                memory_id=memory_id,
                metadata={"reason": "not_found"},
                error_message=f"Memory {memory_id} not found"
            )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory with id {memory_id} not found"
            )
        
        # Soft delete
        success = delete_memory(memory_id)
        
        if success:
            # V1.1: Audit log success
            log_action(
                tenant_id=memory.tenant_id,
                action_type="DELETE",
                api_key=api_key,
                success=True,
                user_id=memory.user_id,
                memory_id=memory_id,
                metadata={
                    "subject": memory.subject,
                    "predicate": memory.predicate
                }
            )
            
            return MemoryDeleteResponse(
                status="success",
                message=f"Memory {memory_id} deleted successfully",
                deleted_id=memory_id
            )
        else:
            # V1.1: Audit log failure
            log_action(
                tenant_id=memory.tenant_id,
                action_type="DELETE",
                api_key=api_key,
                success=False,
                user_id=memory.user_id,
                memory_id=memory_id,
                error_message="Failed to delete memory"
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete memory"
            )
        
    except HTTPException:
        raise
    except StorageError as e:
        # V1.1: Audit log storage error
        log_action(
            tenant_id="unknown",
            action_type="DELETE",
            api_key=api_key,
            success=False,
            memory_id=memory_id,
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )
    except Exception as e:
        # V1.1: Audit log unexpected error
        log_action(
            tenant_id="unknown",
            action_type="DELETE",
            api_key=api_key,
            success=False,
            memory_id=memory_id,
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
