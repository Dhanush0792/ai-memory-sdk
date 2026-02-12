"""FastAPI Application Entry Point"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before database initialization

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .database import Database

app = FastAPI(
    title="Secure AI Memory SDK",
    version="1.0.0",
    description="Enterprise-grade memory for LLM applications"
)


# CORS - Environment-driven configuration
cors_origins = os.getenv("CORS_ORIGINS", "")
origins = [o.strip() for o in cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)

# Root endpoint - JSON only (no frontend serving)
@app.get("/")
def root():
    return {"status": "AI Memory SDK backend running"}

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

# Initialize database on startup
@app.on_event("startup")
async def startup():
    if os.getenv("DATABASE_URL"):
        db = Database()
        db.init_schema()
    else:
        import logging
        logging.warning("DATABASE_URL not set - skipping database initialization")

