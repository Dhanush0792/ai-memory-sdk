"""
Memory retrieval logic with ranking and filtering.

V1.1 DETERMINISTIC RANKING SPECIFICATION:
1. Normalization: Lowercase all text
2. Tokenization: Split on whitespace
3. Stop words: None (keep all terms)
4. Exact match: Full query in predicate OR object → +10 points
5. Partial match: Each query token in predicate OR object → +5 points per token
6. Confidence weight: confidence × 5.0
7. Recency weight: max(0, 5.0 - (age_days × 0.1))
8. Final score: exact_match + partial_match + confidence_weight + recency_weight
9. Sorting: Descending by score, ties broken by created_at DESC (stable sort)
"""

import re
from typing import List
from app.database import db
from app.models import MemoryObjectWithScore


class RetrievalError(Exception):
    """Raised when retrieval operations fail."""
    pass


def retrieve_memories(
    tenant_id: str,
    user_id: str,
    query: str,
    limit: int = 10
) -> List[MemoryObjectWithScore]:
    """
    Retrieve memories with deterministic relevance ranking.
    
    V1.1 HARDENING:
    - Formalized ranking algorithm (see module docstring)
    - Deterministic output (no randomness)
    - Stable sort for tie-breaking
    
    Args:
        tenant_id: Tenant identifier
        user_id: User identifier
        query: Search query
        limit: Maximum number of results
        
    Returns:
        List of memories with relevance scores, sorted by score descending
        
    Raises:
        RetrievalError: If retrieval fails
    """
    try:
        # STEP 1: NORMALIZATION
        # Lowercase query for case-insensitive matching
        query_normalized = query.lower().strip()
        
        # STEP 2: TOKENIZATION
        # Split on whitespace, remove empty strings
        query_tokens = [t for t in query_normalized.split() if t]
        
        if not query_tokens:
            # Empty query returns all memories sorted by recency
            query_normalized = ""
            query_tokens = []
        
        with db.get_cursor() as cur:
            # Retrieve all active memories for this user
            cur.execute("""
                SELECT *,
                    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) as age_seconds
                FROM memories
                WHERE tenant_id = %s
                  AND user_id = %s
                  AND is_active = true
                ORDER BY created_at DESC
            """, (tenant_id, user_id))
            
            memories = cur.fetchall()
            
            if not memories:
                return []
            
            # Calculate relevance scores
            scored_memories = []
            
            for memory in memories:
                score = calculate_relevance_score_deterministic(
                    memory,
                    query_normalized,
                    query_tokens
                )
                
                scored_memories.append({
                    **memory,
                    'relevance_score': score
                })
            
            # STEP 9: STABLE SORT
            # Sort by relevance score descending, then by created_at descending
            # This ensures deterministic ordering even with tied scores
            scored_memories.sort(
                key=lambda x: (x['relevance_score'], x['created_at']),
                reverse=True
            )
            
            # Limit results
            scored_memories = scored_memories[:limit]
            
            # Convert to Pydantic models
            return [MemoryObjectWithScore(**m) for m in scored_memories]
            
    except Exception as e:
        raise RetrievalError(f"Failed to retrieve memories: {e}")


def calculate_relevance_score_deterministic(
    memory: dict,
    query_normalized: str,
    query_tokens: List[str]
) -> float:
    """
    Calculate relevance score using formalized deterministic algorithm.
    
    ALGORITHM SPECIFICATION (V1.1):
    
    1. Normalization: Lowercase predicate and object
    2. Tokenization: Not needed for matching (use substring matching)
    3. Stop words: None
    4. Exact match: Full query appears in predicate OR object → +10 points
    5. Partial match: Each query token in predicate OR object → +5 points per token
    6. Confidence weight: confidence × 5.0
    7. Recency weight: max(0, 5.0 - (age_days × 0.1))
    8. Final score: sum of all components
    
    Args:
        memory: Memory record from database
        query_normalized: Lowercased, trimmed query string
        query_tokens: List of query tokens (lowercased, split on whitespace)
        
    Returns:
        Relevance score (float, higher = more relevant)
    """
    score = 0.0
    
    # STEP 1: NORMALIZE MEMORY FIELDS
    predicate_normalized = memory['predicate'].lower()
    object_normalized = memory['object'].lower()
    
    # STEP 4: EXACT MATCH SCORING
    # Full query appears as substring in predicate OR object
    if query_normalized and (
        query_normalized in predicate_normalized or 
        query_normalized in object_normalized
    ):
        score += 10.0
    
    # STEP 5: PARTIAL MATCH SCORING
    # Each query token appears in predicate OR object
    for token in query_tokens:
        if token in predicate_normalized or token in object_normalized:
            score += 5.0
    
    # STEP 6: CONFIDENCE WEIGHT
    # confidence is in [0, 1], multiply by 5.0 for weighting
    score += float(memory['confidence']) * 5.0
    
    # STEP 7: RECENCY WEIGHT
    # Newer memories get higher scores
    # Decay: 0.1 points per day, max 5.0 points for very recent
    age_seconds = float(memory['age_seconds'])
    age_days = age_seconds / 86400.0  # Convert seconds to days
    recency_score = max(0.0, 5.0 - (age_days * 0.1))
    score += recency_score
    
    # STEP 8: FINAL SCORE
    # Sum of all components (already computed above)
    return score
