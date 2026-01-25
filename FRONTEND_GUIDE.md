# Frontend Integration Guide

## Quick Start

The Memory SDK now includes a modern web interface that connects to your backend API.

### 1. Start the Backend

```bash
uvicorn api.main:app --port 8001
```

The backend will automatically serve the frontend at `http://localhost:8001`

### 2. Access the Web Interface

Open your browser and navigate to:
```
http://localhost:8001
```

### 3. Configure the Interface

On first visit, you'll see a configuration panel:

- **API Key**: `dev-key-12345` (from your .env file)
- **User ID**: Any identifier (e.g., `user-123`, `alice`, etc.)
- **API URL**: `http://localhost:8001` (default)

Click "Save Configuration" to proceed to the dashboard.

---

## Features

### 📊 Dashboard
- Real-time statistics (total memories, facts, preferences, events)
- Visual cards with counts

### ➕ Add Memory
- Quick form to add new memories
- Select type: Fact, Preference, or Event
- Instant feedback

### 💬 Chat Interface
- Chat with AI assistant (requires LLM API key)
- Auto-save extracted memories option
- Conversation history

### 📚 Memory Management
- View all your memories
- Filter by type
- Delete individual memories
- Timestamps for each memory

### 🔒 GDPR Compliance
- Export all your data as JSON
- Delete all data permanently
- Full data portability

---

## Configuration Details

### API Key
The API key authenticates your requests. Default: `dev-key-12345`

To change it:
1. Update `API_KEY` in `.env` file
2. Restart the backend
3. Update the API key in the web interface

### User ID
The User ID isolates your data from other users. Each user sees only their own memories.

**Important**: The current system uses a shared API key model. See the Security Model section in README.md for deployment guidance.

---

## Architecture

```
Frontend (Port 8001)
    ↓
FastAPI Backend (Port 8001)
    ↓
PostgreSQL Database
```

The frontend is served directly by FastAPI using StaticFiles:
- `/` → Frontend HTML
- `/static/` → CSS and JavaScript
- `/api/v1/` → Backend API endpoints

---

## Development

### Frontend Files

```
frontend/
├── index.html          # Main HTML page
└── static/
    ├── style.css       # Modern dark theme styles
    └── app.js          # Application logic
```

### Customization

**Change Theme Colors**: Edit `frontend/static/style.css` `:root` variables

**Add Features**: Extend `frontend/static/app.js` with new functions

**Modify Layout**: Update `frontend/index.html` structure

---

## API Endpoints Used

The frontend integrates with these backend endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/memory` | POST | Add new memory |
| `/api/v1/memory` | GET | List all memories |
| `/api/v1/memory/{id}` | DELETE | Delete specific memory |
| `/api/v1/memory/stats` | GET | Get statistics |
| `/api/v1/chat` | POST | Chat with AI (requires LLM key) |
| `/api/v1/gdpr/export` | GET | Export all data |
| `/api/v1/gdpr/delete` | DELETE | Delete all data |

---

## Troubleshooting

### "Failed to load stats" Error
- Check that backend is running on port 8001
- Verify API key and User ID are correct
- Check browser console for CORS errors

### Chat Not Working
- Chat requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`
- Without LLM keys, chat will return an error
- This is expected behavior (see RELEASE_CLEARED.md)

### CORS Errors
- Backend has CORS enabled by default
- If issues persist, check `CORS_ORIGINS` in `.env`

---

## Production Deployment

### Security Checklist

- [ ] Change default API key
- [ ] Use HTTPS (not HTTP)
- [ ] Set proper CORS origins
- [ ] Enable rate limiting
- [ ] Review Security Model in README.md

### Hosting Options

**Backend + Frontend Together**:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8001
```

**Separate Hosting**:
- Host frontend on static hosting (Netlify, Vercel)
- Update `apiUrl` in frontend to point to backend
- Ensure CORS is configured

---

## Next Steps

1. ✅ Backend running
2. ✅ Frontend accessible
3. ✅ Configuration saved
4. 📝 Add your first memory
5. 💬 Try the chat (if LLM key configured)
6. 📊 Explore the dashboard

**Enjoy your AI Memory SDK!** 🧠
