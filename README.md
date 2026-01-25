# AI Memory SDK

**Production-ready AI memory management system with LLM-powered extraction.**

A clean, minimal, and stable FastAPI-based SDK for storing and retrieving durable user memory using PostgreSQL and LLMs (OpenAI or Anthropic).

---

## ✨ Features

- 🧠 **LLM-Powered Memory Extraction** - Automatically extract facts, preferences, events from user messages
- 💾 **PostgreSQL Storage** - Durable storage with JSONB support (no vector extension required)
- 🔌 **Clean REST API** - Simple, well-documented HTTP endpoints
- 🎯 **Multi-Provider AI** - Support for OpenAI and Anthropic
- 📊 **Memory Statistics** - Track memory usage and types
- ⏰ **Expiration Support** - Optional TTL for memories
- 🪟 **Windows Compatible** - Clean installation without C compilers

---

## 🏗️ Architecture

```
app/
├── main.py                    # FastAPI bootstrap
├── api/
│   └── routes.py             # HTTP layer only
├── memory/
│   ├── sdk.py                # Business logic
│   └── extraction.py         # LLM memory extraction
├── assistant/
│   └── ai_client.py          # LLM client abstraction
└── database/
    └── connection.py         # PostgreSQL access layer
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- OpenAI or Anthropic API key

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```powershell
# Copy example environment file
copy .env.example .env

# Edit .env and set:
# - DATABASE_URL
# - AI_PROVIDER (openai or anthropic)
# - OPENAI_API_KEY or ANTHROPIC_API_KEY
```

### 3. Initialize Database

```powershell
# Create database
psql -U postgres -c "CREATE DATABASE memory_db;"

# Run schema
python scripts/init_db.py
```

### 4. Start Server

```powershell
# Development mode
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Run QA Tests

```powershell
python scripts/qa_test.py
```

---

## 📡 API Endpoints

### Health Check

```bash
GET /health
```

### Chat with Memory

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "user_id": "user123",
  "message": "My name is Alice",
  "auto_save": true
}
```

### Extract Memory Only

```bash
POST /api/v1/memory/extract?user_id=user123&message=I%20love%20pizza
```

### Retrieve Memories

```bash
GET /api/v1/memory/{user_id}?limit=10
GET /api/v1/memory/{user_id}?memory_type=fact
GET /api/v1/memory/{user_id}?key=name
```

### Delete Memories

```bash
DELETE /api/v1/memory/{user_id}
```

### Memory Statistics

```bash
GET /api/v1/memory/{user_id}/stats
```

---

## 💻 SDK Usage

```python
from app.memory.sdk import MemorySDK
from app.memory.extraction import MemoryExtractor
from app.assistant.ai_client import create_ai_client

# Initialize SDK
sdk = MemorySDK()

# Add memory manually
sdk.add_memory(
    user_id="user123",
    memory_type="fact",
    key="name",
    value="Alice"
)

# Retrieve memories
memories = sdk.retrieve_memory(user_id="user123")

# Extract memories from text
extractor = MemoryExtractor()
extracted = extractor.extract("I love pizza and hate broccoli")

# Get statistics
stats = sdk.get_memory_stats(user_id="user123")

# Delete all memories
sdk.delete_all_memory(user_id="user123")
```

---

## 🧪 Testing

### Manual Testing with cURL

```powershell
# Health check
curl http://localhost:8000/health

# Extract memory
curl -X POST "http://localhost:8000/api/v1/memory/extract?user_id=alice&message=My%20name%20is%20Alice"

# Retrieve memories
curl http://localhost:8000/api/v1/memory/alice

# Chat
curl -X POST http://localhost:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{\"user_id\":\"alice\",\"message\":\"What is my name?\",\"auto_save\":false}'

# Delete memories
curl -X DELETE http://localhost:8000/api/v1/memory/alice
```

### Automated QA Tests

```powershell
python scripts/qa_test.py
```

Expected output:
```
✓ Health Check - PASS
✓ Extract Memory - Name - PASS
✓ Extract Memory - Preference - PASS
✓ Retrieve Memories - PASS
✓ Chat with Memory - PASS
✓ Memory Statistics - PASS
✓ Delete All Memories - PASS
✓ Verify Deletion - PASS

Results: 8/8 tests passed
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);
```

**Memory Types:**
- `fact` - Concrete facts (name, age, location, job)
- `preference` - Likes, dislikes, preferences
- `event` - Past or future events, experiences
- `context` - General context or background

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `AI_PROVIDER` | No | `openai` | AI provider (`openai` or `anthropic`) |
| `OPENAI_API_KEY` | If using OpenAI | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4-turbo-preview` | OpenAI model |
| `ANTHROPIC_API_KEY` | If using Anthropic | - | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-3-sonnet-20240229` | Anthropic model |

---

## 📦 Dependencies

**Core:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `psycopg[binary]` - PostgreSQL driver (v3, Windows-compatible)

**AI:**
- `openai` - OpenAI client
- `anthropic` - Anthropic client

**Utilities:**
- `python-dotenv` - Environment management
- `httpx` - HTTP client

**No vector dependencies** - Works without `pgvector` or `voyageai`

---

## 🚨 Known Limitations

1. **No Semantic Search** - This version does not include vector embeddings or semantic search. Memories are retrieved by exact user_id, type, or key matching.

2. **Single Database** - No connection pooling across multiple databases.

3. **No Authentication** - API endpoints are not authenticated. Add your own auth layer for production.

4. **Memory Extraction Quality** - Depends on LLM quality. May miss subtle context or extract incorrectly.

5. **No Rate Limiting** - Add rate limiting middleware for production use.

6. **Synchronous Database** - Uses synchronous psycopg. For high concurrency, consider async drivers.

---

## 🛠️ Troubleshooting

### Database Connection Errors

```powershell
# Test PostgreSQL connection
psql -U postgres -d memory_db -c "SELECT 1;"

# Check DATABASE_URL format
# postgresql://username:password@localhost:5432/database_name
```

### Import Errors

```powershell
# Ensure you're in the project root
cd c:\Users\Desktop\Projects\memory

# Activate virtual environment
.\venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### API 500 Errors

Check logs for:
- Missing API keys
- Database connection issues
- Invalid memory types
- Malformed requests

---

## 📄 License

MIT License - Use freely in your projects.

---

## 🤝 Contributing

This is a production-ready baseline. Contributions welcome:
- Add vector search support
- Implement async database layer
- Add authentication
- Improve memory extraction prompts

---

## 📞 Support

For issues or questions, check:
1. This README
2. API documentation at `/docs`
3. QA test script for examples

---

**Built with ❤️ for production use.**
