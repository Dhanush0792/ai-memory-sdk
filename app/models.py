"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from uuid import UUID


# Request Models

class MemoryIngestRequest(BaseModel):
    """Request model for memory ingestion."""
    tenant_id: str = Field(..., min_length=1, max_length=255, description="Tenant identifier")
    user_id: str = Field(..., min_length=1, max_length=255, description="User identifier")
    conversation_text: str = Field(..., min_length=1, description="Conversation text to extract memories from")
    
    @field_validator("conversation_text")
    @classmethod
    def validate_conversation_text(cls, v):
        """Ensure conversation text is not just whitespace."""
        if not v.strip():
            raise ValueError("conversation_text cannot be empty or whitespace")
        return v.strip()


class MemoryRetrieveRequest(BaseModel):
    """Request model for memory retrieval."""
    tenant_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")


# Response Models

class MemoryObject(BaseModel):
    """Memory object representation."""
    id: UUID
    tenant_id: str
    user_id: str
    subject: str
    predicate: str
    object: str
    confidence: float
    source: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class MemoryObjectWithScore(MemoryObject):
    """Memory object with relevance score for retrieval."""
    relevance_score: float = Field(..., description="Relevance score for ranking")


class MemoryIngestResponse(BaseModel):
    """Response model for memory ingestion."""
    status: str = Field(..., description="success or failure")
    memories: List[MemoryObject] = Field(default_factory=list)
    message: Optional[str] = None
    errors: Optional[List[str]] = None


class MemoryRetrieveResponse(BaseModel):
    """Response model for memory retrieval."""
    memories: List[MemoryObjectWithScore]
    total: int = Field(..., description="Total number of results returned")


class MemoryDeleteResponse(BaseModel):
    """Response model for memory deletion."""
    status: str = Field(..., description="success or failure")
    message: str
    deleted_id: Optional[UUID] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="healthy or unhealthy")
    database_connected: bool
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Internal Models for Extraction

class ExtractedTriple(BaseModel):
    """Extracted subject-predicate-object triple from LLM."""
    subject: str = Field(..., min_length=1, max_length=500)
    predicate: str = Field(..., min_length=1, max_length=255)
    object: str = Field(..., min_length=1)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    
    @field_validator("subject", "predicate", "object")
    @classmethod
    def validate_not_empty(cls, v):
        """Ensure fields are not just whitespace."""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()
