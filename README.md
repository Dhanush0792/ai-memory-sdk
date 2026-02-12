# AI Memory SDK

**Production-ready AI memory management system with clean backend/frontend separation.**

A FastAPI-based backend with static HTML frontend for storing and retrieving durable user memory using PostgreSQL and LLMs (OpenAI or Anthropic).

---

## 🏗️ Architecture

This repository is organized into three main components:

```
memory/
├── backend/          # FastAPI JSON API (deployed on Render)
├── frontend/         # Static HTML/CSS/JS (deployed on Netlify)
└── sdk/              # Python SDK for programmatic access
```

### Backend (Render)
- **Location**: `/backend/`
- **Type**: FastAPI JSON API
- **Deployment**: Render
- **Documentation**: See [backend/README.md](backend/README.md)
- **API Docs**: Available at `/docs` (Swagger UI)

### Frontend (Netlify)
- **Location**: `/frontend/`
- **Type**: Static HTML/CSS/JavaScript
- **Deployment**: Netlify
- **Documentation**: See [frontend/README.md](frontend/README.md)
- **No build step required**

### SDK (Python)
- **Location**: `/sdk/`
- **Type**: Python client library
- **Usage**: Programmatic access to the API

---

## ✨ Features

- 🧠 **LLM-Powered Memory Extraction** - Automatically extract facts, preferences, events from user messages
- 💾 **PostgreSQL Storage** - Durable storage with JSONB support (no vector extension required)
- 🔌 **Clean REST API** - Simple, well-documented HTTP endpoints
- 🎯 **Multi-Provider AI** - Support for OpenAI and Anthropic
- 📊 **Memory Statistics** - Track memory usage and types
- 🔒 **Security** - Authentication, rate limiting, encryption
- 🌐 **GDPR Compliant** - Data export and deletion endpoints
- 🪟 **Windows Compatible** - Clean installation without C compilers

---

## 🚀 Quick Start

### Backend (Local Development)

1. **Navigate to backend directory**:
```bash
cd backend
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the server**:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 10000
```

Backend will be available at `http://localhost:10000`

See [backend/README.md](backend/README.md) for detailed setup instructions.

### Frontend (Local Development)

1. **Navigate to frontend directory**:
```bash
cd frontend
```

2. **Serve with any static server**:
```bash
# Python
python -m http.server 8080

# Or use VS Code Live Server extension
```

3. **Configure in browser**:
- Click "Configuration"
- Set API URL to `http://localhost:10000`
- Set API Key and User ID

See [frontend/README.md](frontend/README.md) for detailed setup instructions.

---

## 📡 API Endpoints

### Core
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

---

## 🚢 Deployment

### Backend (Render)

1. **Connect repository** to Render
2. **Set root directory**: `backend`
3. **Configure environment variables** in Render dashboard
4. **Deploy** - Render will use `Procfile` and `runtime.txt`

Backend URL: `https://ai-memory-sdk.onrender.com`

### Frontend (Netlify)

1. **Connect repository** to Netlify
2. **Set base directory**: `frontend`
3. **Set publish directory**: `frontend`
4. **Build command**: _(leave empty)_
5. **Deploy**

Frontend will automatically connect to production backend.

---

## 💻 SDK Usage

```python
from sdk.client import MemorySDKClient

# Initialize client
client = MemorySDKClient(
    api_key="your-api-key",
    user_id="user123",
    base_url="https://ai-memory-sdk.onrender.com"
)

# Add memory
client.add_memory(
    content="I love pizza",
    memory_type="preference"
)

# Retrieve memories
memories = client.get_memories(limit=10)

# Chat with memory context
response = client.chat("What do I like to eat?")

# Export data (GDPR)
data = client.export_data()

# Delete all data (GDPR)
client.delete_all_data()
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**Memory Types:**
- `fact` - Concrete facts (name, age, location, job)
- `preference` - Likes, dislikes, preferences
- `event` - Past or future events, experiences

---

## 🔧 Configuration

### Backend Environment Variables

See [backend/.env.example](backend/.env.example) for all required variables:

- `DATABASE_URL` - PostgreSQL connection string (required)
- `ENCRYPTION_KEY` - Fernet encryption key (required)
- `API_KEY` - API authentication key (required)
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `CORS_ORIGINS` - Allowed CORS origins (default: `*`)

### Frontend Configuration

Configure via UI:
- **API Key**: Your backend API key
- **User ID**: Your user identifier
- **API URL**: Backend URL (default: production)

---

## 📦 Dependencies

### Backend
- `fastapi==0.109.0` - Web framework
- `uvicorn==0.27.0` - ASGI server
- `pydantic>=2.5,<3.0` - Data validation
- `psycopg[binary]` - PostgreSQL driver
- `openai==1.10.0` - OpenAI client
- `cryptography==42.0.0` - Encryption
- `tiktoken==0.5.2` - Token counting

### Frontend
- No dependencies - Pure HTML/CSS/JavaScript

---

## 🛠️ Project Structure

```
memory/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── routes.py            # API route definitions
│   │   ├── database.py          # Database operations
│   │   ├── auth.py              # Authentication
│   │   ├── encryption.py        # Data encryption
│   │   ├── rate_limiter.py      # Rate limiting
│   │   └── services/
│   │       ├── chat_service.py
│   │       ├── llm_client.py
│   │       └── memory_extractor.py
│   ├── tests/                   # Backend tests
│   ├── requirements.txt         # Python dependencies
│   ├── runtime.txt             # Python version
│   ├── Procfile                # Render start command
│   └── README.md               # Backend documentation
│
├── frontend/
│   ├── index.html              # Main HTML page
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css       # Styles
│   │   └── js/
│   │       └── app.js          # Application logic
│   └── README.md               # Frontend documentation
│
├── sdk/
│   ├── client.py               # Python SDK client
│   └── exceptions.py           # SDK exceptions
│
└── README.md                   # This file
```

---

## 🔒 Security Features

- **API Key Authentication** - All endpoints require valid API key
- **Rate Limiting** - Configurable rate limits per endpoint
- **Data Encryption** - Memory content encrypted at rest
- **CORS Protection** - Configurable allowed origins
- **Audit Logging** - All operations logged with integrity checks

---

## 📄 License

MIT License - Use freely in your projects.

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Add vector search support
- Implement async database layer
- Improve memory extraction prompts
- Add more LLM providers

---

## 📞 Support

For issues or questions:
1. Check component-specific README ([backend](backend/README.md) or [frontend](frontend/README.md))
2. API documentation at `/docs`
3. Open an issue on GitHub

---

**Built with ❤️ from India.**
