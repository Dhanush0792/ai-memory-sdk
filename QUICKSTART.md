# Secure AI Memory SDK - Quick Start

**Integration time: ≤15 minutes**  
**Encryption: ON by default** 🔒

## 1. Install (2 minutes)

```bash
pip install -r requirements.txt
```

## 2. Setup Database (3 minutes)

**Option A: Using existing PostgreSQL (recommended)**
```bash
python setup_db.py
```

**Option B: Using Docker**
```bash
docker run -d \
  --name memory-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memory_db \
  -p 5432:5432 \
  postgres:15
```

## 3. Configure (3 minutes)

```bash
cp .env.example .env
```

**Generate encryption key (REQUIRED):**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Edit `.env` and set:**
- `ENCRYPTION_KEY` to generated key
- `API_KEY` to your API key
- `DATABASE_URL` if not using defaults

⚠️ **WARNING:** Never commit `.env` with real keys to version control

## 4. Start API (1 minute)

```bash
python -m uvicorn api.main:app --reload
```

API runs at `http://localhost:8000`

## 5. Use SDK (5 minutes)

```python
from sdk import MemorySDK

# Initialize
sdk = MemorySDK(
    api_key="your-api-key",
    user_id="user-123"
)

# Add memories
sdk.add_memory("User prefers dark mode", "preference")
sdk.add_memory("User lives in San Francisco", "fact")
sdk.add_memory("User logged in at 2pm", "event")

# Get LLM context (MANDATORY FEATURE)
context = sdk.get_context(
    query="user preferences",
    max_tokens=2000
)

# Use in your LLM prompt
prompt = f"{context}\n\nUser: What's my preferred theme?"
```

## 6. Run Demo App (2 minutes)

```bash
export OPENAI_API_KEY=your-key
python demo/chat_app.py
```

## Core Features

### Memory Operations
```python
# Add
sdk.add_memory(content, type, metadata, expires_at)

# Retrieve
sdk.get_memories(memory_type, limit)

# Delete
sdk.delete_memory(memory_id)
```

### Context Injection (MANDATORY)
```python
context = sdk.get_context(
    query="optional query",
    max_tokens=2000,  # Approximate limit (chars vs tokens)
    memory_types=["fact", "preference"]
)
```

**Note:** `max_tokens` is approximate. Actual character count may vary due to tokenization.

### GDPR Compliance
```python
# Export all data
data = sdk.export_user_data()

# Hard delete all data
sdk.delete_user_data(confirm=True)

# Delete by type
sdk.delete_by_type("preference")

# Delete by metadata key
sdk.delete_by_key("session_id")
```

## Error Handling

```python
from sdk import (
    MemoryAuthError,
    MemoryNotFoundError,
    MemoryValidationError,
    MemoryAPIError
)

try:
    sdk.add_memory("test", "fact")
except MemoryAuthError:
    print("Invalid API key")
except MemoryValidationError:
    print("Invalid input")
except MemoryAPIError:
    print("Server error")
```

## Production Checklist

- [ ] Generate and set strong `ENCRYPTION_KEY` (required)
- [ ] Set strong `API_KEY` in production
- [ ] Rotate `ENCRYPTION_KEY` securely (backup before rotation)
- [ ] Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
- [ ] Enable SSL for database connections
- [ ] Set up monitoring and logging
- [ ] Configure CORS for your domain
- [ ] Set up rate limiting (not included in v1.0)
- [ ] Enable audit log retention

**Encryption Notes:**
- Memory content is encrypted at rest using Fernet (AES-128-CBC + HMAC)
- Legacy plaintext data is readable but will not be re-encrypted automatically
- Lost encryption keys = permanent data loss

## API Endpoints

- `POST /api/v1/memory` - Add memory
- `GET /api/v1/memory` - Get memories
- `DELETE /api/v1/memory/{id}` - Delete memory
- `POST /api/v1/memory/context` - Get LLM context
- `GET /api/v1/gdpr/export/{user_id}` - Export data
- `DELETE /api/v1/gdpr/delete/{user_id}` - Delete data
- `DELETE /api/v1/memory/type/{type}` - Delete by type
- `DELETE /api/v1/memory/key/{key}` - Delete by key

## Support

See `SDK_API.md` for complete API reference.
