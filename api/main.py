"""FastAPI Application Entry Point"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before database initialization

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import router
from .database import Database
from .rate_limiter import rate_limit_middleware

app = FastAPI(
    title="Secure AI Memory SDK",
    version="1.0.0",
    description="Enterprise-grade memory for LLM applications"
)

# Rate limiting middleware (FIRST - before CORS)
app.middleware("http")(rate_limit_middleware)

# CORS
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

# Initialize database on startup
@app.on_event("startup")
async def startup():
    db = Database()
    db.init_schema()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
