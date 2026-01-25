# Secure AI Memory SDK - Public API (FROZEN)

## Installation

```bash
pip install secure-ai-memory
```

## Initialization

```python
from secure_ai_memory import MemorySDK

sdk = MemorySDK(
    api_key: str,
    user_id: str,
    base_url: str = "https://api.memory.ai"
)
```

## Core Memory Operations

### add_memory()
```python
sdk.add_memory(
    content: str,
    memory_type: Literal["fact", "preference", "event"],
    metadata: dict = None,
    expires_at: datetime = None
) -> dict
```

**Returns:**
```python
{
    "id": str,
    "user_id": str,
    "content": str,
    "type": str,
    "created_at": str,
    "expires_at": str | None
}
```

### get_memories()
```python
sdk.get_memories(
    memory_type: Literal["fact", "preference", "event"] = None,
    limit: int = 100
) -> list[dict]
```

**Returns:** List of memory objects

### delete_memory()
```python
sdk.delete_memory(
    memory_id: str
) -> dict
```

**Returns:**
```python
{
    "deleted": bool,
    "memory_id": str
}
```

## Context Injection (MANDATORY)

### get_context()
```python
sdk.get_context(
    query: str = None,
    max_tokens: int = 2000,
    memory_types: list[str] = None
) -> str
```

**Returns:** LLM-ready context string, token-bounded, relevance-filtered, safe for direct prompt insertion.

**Example:**
```python
context = sdk.get_context(query="user preferences", max_tokens=1500)
prompt = f"{context}\n\nUser: {user_message}"
```

## GDPR Compliance

### export_user_data()
```python
sdk.export_user_data() -> dict
```

**Returns:**
```python
{
    "user_id": str,
    "exported_at": str,
    "memories": list[dict],
    "metadata": dict
}
```

### delete_user_data()
```python
sdk.delete_user_data(
    confirm: bool = False
) -> dict
```

**Returns:**
```python
{
    "deleted": bool,
    "user_id": str,
    "deleted_count": int,
    "irreversible": bool
}
```

### delete_by_type()
```python
sdk.delete_by_type(
    memory_type: Literal["fact", "preference", "event"]
) -> dict
```

**Returns:**
```python
{
    "deleted": bool,
    "type": str,
    "deleted_count": int
}
```

### delete_by_key()
```python
sdk.delete_by_key(
    key: str
) -> dict
```

**Returns:**
```python
{
    "deleted": bool,
    "key": str,
    "deleted_count": int
}
```

## Error Handling

All methods raise:
- `MemoryAuthError` - Invalid API key or unauthorized
- `MemoryNotFoundError` - Resource not found
- `MemoryValidationError` - Invalid input
- `MemoryAPIError` - Server error

## Types

```python
MemoryType = Literal["fact", "preference", "event"]

Memory = {
    "id": str,
    "user_id": str,
    "content": str,
    "type": MemoryType,
    "metadata": dict,
    "created_at": str,
    "expires_at": str | None
}
```
