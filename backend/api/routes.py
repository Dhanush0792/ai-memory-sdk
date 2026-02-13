"""FastAPI Routes for Memory SDK"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, validator
from typing import Optional, Literal, Any
from datetime import datetime
import json
from .context_injection import ContextInjector
from .database import Database
from .auth import get_api_key_context, APIKeyContext, get_authenticated_user

router = APIRouter()
db = Database()
context_injector = ContextInjector()

# Request Models
class AddMemoryRequest(BaseModel):
    user_id: str
    content: str
    type: Literal["fact", "preference", "event", "system"]
    key: Optional[str] = None
    value: Optional[Any] = None
    confidence: float = 1.0
    importance: Optional[int] = None
    ttl_seconds: Optional[int] = None
    ingestion_mode: Literal["explicit", "rules"] = "explicit"
    metadata: dict = {}
    expires_at: Optional[str] = None
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('user_id cannot be empty')
        if len(v) > 255:
            raise ValueError('user_id too long (max 255 chars)')
        return v
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('content cannot be empty')
        if len(v) > 10000:
            raise ValueError('content too long (max 10000 chars)')
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('confidence must be between 0.0 and 1.0')
        return v
    
    @validator('importance')
    def validate_importance(cls, v):
        if v is not None and not (1 <= v <= 5):
            raise ValueError('importance must be between 1 and 5')
        return v
    
    @validator('metadata')
    def validate_metadata(cls, v):
        if not v:
            return {}
        
        # Check JSON size
        json_str = json.dumps(v)
        if len(json_str) > 5000:  # 5KB limit
            raise ValueError('Metadata too large (max 5KB)')
        
        # Check nesting depth
        def check_depth(obj, depth=0):
            if depth > 5:
                raise ValueError('Metadata too deeply nested (max 5 levels)')
            if isinstance(obj, dict):
                for val in obj.values():
                    check_depth(val, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, depth + 1)
        
        check_depth(v)
        return v

class ContextRequest(BaseModel):
    query: Optional[str] = None
    max_tokens: int = 2000
    memory_types: Optional[list[str]] = None

class ChatRequest(BaseModel):
    message: str
    auto_save: bool = True
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('message cannot be empty')
        if len(v) > 5000:
            raise ValueError('message too long (max 5000 chars)')
        return v

class ExtractRequest(BaseModel):
    message: str
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('message cannot be empty')
        if len(v) > 5000:
            raise ValueError('message too long (max 5000 chars)')
        return v

# Routes
@router.post("/api/v1/memory")
async def add_memory(
    req_body: AddMemoryRequest,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Add a new memory (Memory Contract v1)"""
    owner_id = api_key_context.owner_id
    
    expires_at = None
    if req_body.expires_at:
        try:
            expires_at = datetime.fromisoformat(req_body.expires_at.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=422, detail=f"Invalid expires_at format: {str(e)}")
    
    memory = db.add_memory(
        owner_id=owner_id,
        user_id=req_body.user_id,
        content=req_body.content,
        memory_type=req_body.type,
        key=req_body.key,
        value=req_body.value,
        confidence=req_body.confidence,
        importance=req_body.importance,
        metadata=req_body.metadata,
        ttl_seconds=req_body.ttl_seconds,
        ingestion_mode=req_body.ingestion_mode,
        expires_at=expires_at
    )
    
    return memory

@router.get("/api/v1/memory")
async def get_memories(
    user_id: str,
    type: Optional[str] = None,
    limit: int = 100,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Get memories for authenticated user (Memory Contract v1)"""
    owner_id = api_key_context.owner_id
    
    memories = db.get_memories(owner_id=owner_id, user_id=user_id, memory_type=type, limit=limit)
    return memories

@router.delete("/api/v1/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    user_id: str,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Hard delete a specific memory (only if owned by owner)"""
    owner_id = api_key_context.owner_id
    
    deleted = db.delete_memory(memory_id, owner_id, user_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found or not owned by user")
    
    return {"deleted": True, "memory_id": memory_id}

@router.delete("/api/v1/memory/{memory_id}/soft")
async def soft_delete_memory(
    memory_id: str,
    user_id: str,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Soft delete a specific memory (Memory Contract v1)"""
    owner_id = api_key_context.owner_id
    
    deleted = db.soft_delete_memory(memory_id, owner_id, user_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found or not owned by user")
    
    return {"soft_deleted": True, "memory_id": memory_id}

@router.post("/api/v1/chat")
async def chat(
    req_body: ChatRequest,
    request: Request,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Chat with AI assistant that remembers user context"""
    owner_id = api_key_context.owner_id
    user_id = get_authenticated_user(request)
    
    try:
        from .services.chat_service import ChatService
        
        # Retrieve user memories
        memories = db.get_memories(owner_id=owner_id, user_id=user_id, limit=20)
        
        # Process chat
        chat_service = ChatService()
        result = chat_service.chat(
            message=req_body.message,
            memories=memories,
            auto_save=req_body.auto_save
        )
        
        # Save extracted memories if auto_save enabled
        saved_memories = []
        if req_body.auto_save and "extracted_memories" in result:
            for mem in result["extracted_memories"]:
                saved = db.add_memory(
                    owner_id=owner_id,
                    user_id=user_id,
                    content=mem["value"],
                    memory_type=mem["type"],
                    metadata={"key": mem["key"]}
                )
                saved_memories.append(saved)
        
        return {
            "response": result["response"],
            "memories_extracted": len(saved_memories),
            "memories_saved": saved_memories
        }
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.post("/api/v1/memory/context")
async def get_context(
    req_body: ContextRequest,
    request: Request,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Get LLM-ready context (MANDATORY)"""
    owner_id = api_key_context.owner_id
    user_id = get_authenticated_user(request)
    
    memories = db.get_memories(owner_id=owner_id, user_id=user_id)
    
    context = context_injector.build_context(
        memories=memories,
        query=req_body.query,
        max_tokens=req_body.max_tokens,
        memory_types=req_body.memory_types
    )
    
    return {"context": context, "token_count": context_injector.count_tokens(context)}

@router.get("/api/v1/gdpr/export")
async def export_user_data(
    request: Request,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Export all user data (GDPR) - only for authenticated user"""
    owner_id = api_key_context.owner_id
    user_id = get_authenticated_user(request)
    
    memories = db.get_memories(owner_id=owner_id, user_id=user_id)
    
    return {
        "user_id": user_id,
        "exported_at": datetime.utcnow().isoformat(),
        "memories": memories,
        "metadata": {
            "total_count": len(memories),
            "export_version": "1.0"
        }
    }

@router.delete("/api/v1/gdpr/delete")
async def delete_user_data(
    request: Request,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Hard delete all user data (GDPR) - only for authenticated user"""
    owner_id = api_key_context.owner_id
    user_id = get_authenticated_user(request)
    
    count = db.delete_user_data(owner_id, user_id)
    
    return {
        "deleted": True,
        "user_id": user_id,
        "deleted_count": count,
        "irreversible": True
    }

@router.delete("/api/v1/memory/type/{memory_type}")
async def delete_by_type(
    memory_type: str,
    request: Request,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Delete memories by type for authenticated user"""
    owner_id = api_key_context.owner_id
    user_id = get_authenticated_user(request)
    
    count = db.delete_by_type(owner_id=owner_id, user_id=user_id, memory_type=memory_type)
    
    return {
        "deleted": True,
        "type": memory_type,
        "deleted_count": count
    }

@router.delete("/api/v1/memory/key/{key}")
async def delete_by_key(
    key: str,
    request: Request,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Delete memories by metadata key for authenticated user"""
    owner_id = api_key_context.owner_id
    user_id = get_authenticated_user(request)
    
    count = db.delete_by_key(owner_id=owner_id, user_id=user_id, key=key)
    
    return {
        "deleted": True,
        "key": key,
        "deleted_count": count
    }

@router.post("/api/v1/memory/extract")
async def extract_memories(
    req_body: ExtractRequest,
    request: Request,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Extract and save memories from text using LLM"""
    owner_id = api_key_context.owner_id
    user_id = get_authenticated_user(request)
    
    try:
        from .services.memory_extractor import MemoryExtractor
        
        extractor = MemoryExtractor()
        extracted = extractor.extract(req_body.message)
        
        saved = []
        for mem in extracted:
            memory = db.add_memory(
                owner_id=owner_id,
                user_id=user_id,
                content=mem["value"],
                memory_type=mem["type"],
                metadata={"key": mem["key"]}
            )
            saved.append(memory)
        
        return {
            "extracted_count": len(saved),
            "memories": saved
        }
    except ValueError as e:
        # LLM configuration or parsing errors
        raise HTTPException(
            status_code=503,
            detail=f"LLM service unavailable or failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(e)}")

@router.get("/api/v1/memory/stats")
async def get_memory_stats(
    user_id: str,
    api_key_context: APIKeyContext = Depends(get_api_key_context)
):
    """Get memory statistics for authenticated user (Memory Contract v1)"""
    owner_id = api_key_context.owner_id
    
    stats = db.get_memory_stats(owner_id, user_id)
    return stats
