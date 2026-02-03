# AI Memory SDK - Backend

FastAPI-based backend providing JSON APIs for AI memory management.

## Overview

This backend exposes RESTful JSON APIs for:
- Memory storage and retrieval (facts, preferences, events)
- AI-powered memory extraction from conversations
- Chat with memory context injection
- GDPR compliance (data export/deletion)
- Authentication and rate limiting

**Deployed on**: Render  
**API Documentation**: Available at `/docs` (Swagger UI)

## Running Locally

### Prerequisites
- Python 3.11.9
- PostgreSQL database

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Initialize database:
```bash
python -c "from api.database import Database; db = Database(); db.init_schema()"
```

4. Run the server:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 10000
```

The API will be available at `http://localhost:10000`

## Environment Variables

See `.env.example` for all required environment variables:

- `DATABASE_URL` - PostgreSQL connection string (required)
- `ENCRYPTION_KEY` - Fernet encryption key for memory data (required)
- `API_KEY` - API authentication key (required)
- `OPENAI_API_KEY` - OpenAI API key for LLM features (optional)
- `CORS_ORIGINS` - Allowed CORS origins (comma-separated, see below)

### CORS Configuration

The backend uses environment-driven CORS configuration to control which frontend origins can access the API.

**Environment Variable**: `CORS_ORIGINS`

**Format**: Comma-separated list of allowed origins

**Examples**:
```bash
# Single origin
CORS_ORIGINS=https://ai-memory-sdk.netlify.app

# Multiple origins (production + staging)
CORS_ORIGINS=https://ai-memory-sdk.netlify.app,https://ai-memory-sdk-staging.netlify.app

# Local development
CORS_ORIGINS=http://localhost:8080,http://localhost:3000
```

**Important Security Notes**:
- ⚠️ **Never use `*` (wildcard) in production** - This allows any website to access your API
- Always specify exact origins including protocol (`https://`)
- Update this when deploying to new domains
- Missing or empty `CORS_ORIGINS` will block all cross-origin requests (secure by default)
- Whitespace around commas is automatically trimmed

## API Endpoints

### Core Endpoints
- `GET /` - Status check (returns JSON)
- `GET /health` - Health check
- `GET /docs` - Swagger API documentation

### Memory Management
- `POST /api/v1/memory` - Add memory
- `GET /api/v1/memory` - List memories
- `DELETE /api/v1/memory/{memory_id}` - Delete memory
- `GET /api/v1/memory/stats` - Get memory statistics

### Chat
- `POST /api/v1/chat` - Chat with memory context

### GDPR
- `GET /api/v1/gdpr/export` - Export user data
- `DELETE /api/v1/gdpr/delete` - Delete all user data

## Deployment (Render)

The backend is configured for Render deployment:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: Defined in `Procfile`
- **Python Version**: Specified in `runtime.txt`
- **Environment Variables**: Set in Render dashboard

## Architecture

```
backend/
├── api/
│   ├── main.py              # FastAPI app entry point
│   ├── routes.py            # API route definitions
│   ├── database.py          # Database operations
│   ├── auth.py              # Authentication
│   ├── encryption.py        # Data encryption
│   ├── rate_limiter.py      # Rate limiting
│   ├── context_injection.py # Memory context injection
│   └── services/
│       ├── chat_service.py      # Chat logic
│       ├── llm_client.py        # LLM integration
│       └── memory_extractor.py  # Memory extraction
├── requirements.txt         # Python dependencies
├── runtime.txt             # Python version
├── Procfile                # Render start command
└── .env.example            # Environment template
```

## Notes

- **Backend does NOT serve frontend files** - Frontend is deployed separately on Netlify
- All endpoints return JSON (no HTML)
- CORS is configured to allow frontend access
- Rate limiting is enabled by default
