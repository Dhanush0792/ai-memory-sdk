"""FastAPI Routes for Memory SDK"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from typing import Optional, Literal
from datetime import datetime
import json
from .context_injection import ContextInjector
from .database import Database
from .auth import get_authenticated_user

router = APIRouter()
db = Database()
context_injector = ContextInjector()

# Request Models
class AddMemoryRequest(BaseModel):
    content: str
    type: Literal["fact", "preference", "event"]
    metadata: dict = {}
    expires_at: Optional[str] = None
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('content cannot be empty')
        if len(v) > 10000:
            raise ValueError('content too long (max 10000 chars)')
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
    request: AddMemoryRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Add a new memory"""
    expires_at = None
    if request.expires_at:
        try:
            expires_at = datetime.fromisoformat(request.expires_at.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=422, detail=f"Invalid expires_at format: {str(e)}")
    
    memory = db.add_memory(
        user_id=user_id,
        content=request.content,
        memory_type=request.type,
        metadata=request.metadata,
        expires_at=expires_at
    )
    
    return memory

@router.get("/api/v1/memory")
async def get_memories(
    type: Optional[str] = None,
    limit: int = 100,
    user_id: str = Depends(get_authenticated_user)
):
    """Get memories for authenticated user"""
    memories = db.get_memories(user_id=user_id, memory_type=type, limit=limit)
    return memories

@router.delete("/api/v1/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Delete a specific memory (only if owned by user)"""
    deleted = db.delete_memory(memory_id, user_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found or not owned by user")
    
    return {"deleted": True, "memory_id": memory_id}

@router.post("/api/v1/chat")
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Chat with AI assistant that remembers user context"""
    try:
        from .services.chat_service import ChatService
        
        # Retrieve user memories
        memories = db.get_memories(user_id=user_id, limit=20)
        
        # Process chat
        chat_service = ChatService()
        result = chat_service.chat(
            message=request.message,
            memories=memories,
            auto_save=request.auto_save
        )
        
        # Save extracted memories if auto_save enabled
        saved_memories = []
        if request.auto_save and "extracted_memories" in result:
            for mem in result["extracted_memories"]:
                saved = db.add_memory(
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
    request: ContextRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Get LLM-ready context (MANDATORY)"""
    memories = db.get_memories(user_id=user_id)
    
    context = context_injector.build_context(
        memories=memories,
        query=request.query,
        max_tokens=request.max_tokens,
        memory_types=request.memory_types
    )
    
    return {"context": context, "token_count": context_injector.count_tokens(context)}

@router.get("/api/v1/gdpr/export")
async def export_user_data(user_id: str = Depends(get_authenticated_user)):
    """Export all user data (GDPR) - only for authenticated user"""
    memories = db.get_memories(user_id=user_id)
    
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
async def delete_user_data(user_id: str = Depends(get_authenticated_user)):
    """Hard delete all user data (GDPR) - only for authenticated user"""
    count = db.delete_user_data(user_id)
    
    return {
        "deleted": True,
        "user_id": user_id,
        "deleted_count": count,
        "irreversible": True
    }

@router.delete("/api/v1/memory/type/{memory_type}")
async def delete_by_type(
    memory_type: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Delete memories by type for authenticated user"""
    count = db.delete_by_type(user_id=user_id, memory_type=memory_type)
    
    return {
        "deleted": True,
        "type": memory_type,
        "deleted_count": count
    }

@router.delete("/api/v1/memory/key/{key}")
async def delete_by_key(
    key: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Delete memories by metadata key for authenticated user"""
    count = db.delete_by_key(user_id=user_id, key=key)
    
    return {
        "deleted": True,
        "key": key,
        "deleted_count": count
    }

@router.post("/api/v1/memory/extract")
async def extract_memories(
    request: ExtractRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Extract and save memories from text using LLM"""
    try:
        from .services.memory_extractor import MemoryExtractor
        
        extractor = MemoryExtractor()
        extracted = extractor.extract(request.message)
        
        saved = []
        for mem in extracted:
            memory = db.add_memory(
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
async def get_memory_stats(user_id: str = Depends(get_authenticated_user)):
    """Get memory statistics for authenticated user"""
    stats = db.get_memory_stats(user_id)
    return stats
