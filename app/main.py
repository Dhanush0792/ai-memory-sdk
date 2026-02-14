"""
Enterprise Memory Infrastructure Phase 2
FastAPI application with RBAC, policies, TTL, observability, and model-agnostic extraction.
"""

import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import settings
from app.database import db
from app.routes.auth import router as auth_router
from app.routes.memory import router as memory_router
from app.routes.chat import router as chat_router
from app.routes.user_memory import router as user_memory_router
from app.routes.admin import router as admin_router
from app.models import HealthResponse
from app.jobs import ttl_cleanup_job
from app.observability import configure_logging, logger, system_info


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown with Phase 2 components.
    """
    # Configure logging
    configure_logging()
    
    # Startup
    logger.info("startup_begin", version="Phase 2", environment=settings.environment)
    
    # Set system info for Prometheus
    system_info.info({
        'version': 'Phase 2',
        'environment': settings.environment,
        'extraction_provider': settings.extraction_provider
    })
    
    # Validate configuration
    logger.info("config_loaded",
                database=settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured',
                extraction_provider=settings.extraction_provider,
                cors_origins=settings.cors_origins,
                rate_limit=settings.rate_limit_requests,
                metrics_enabled=settings.metrics_enabled)
    
    # Initialize database
    try:
        db.initialize()
        
        # Apply migrations (Basic check/create for users table)
        # Note: In production, consider a proper migration tool like Alembic.
        # For this minimal setup, we'll execute the raw SQL if needed.
        with db.get_cursor() as cur:
            try:
                # Basic check if table exists
                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'users'")
                if not cur.fetchone():
                    logger.info("applying_migrations")
                    with open("database/migrations/001_create_users.sql", "r") as f:
                        cur.execute(f.read())
                    logger.info("migrations_applied")
            except Exception as e:
                logger.warning("migration_check_failed", error=str(e))
                # Don't fail startup on migration check error, DB might be fine

        if db.health_check():
            logger.info("database_ready")
        else:
            logger.error("database_health_check_failed")
            raise RuntimeError("Database not accessible")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        raise
    
    # Start TTL cleanup job
    ttl_task = None
    if settings.ttl_cleanup_interval > 0:
        ttl_task = asyncio.create_task(ttl_cleanup_job.run_forever())
        logger.info("ttl_cleanup_started", interval=settings.ttl_cleanup_interval)
    
    logger.info("startup_complete")
    
    yield
    
    # Shutdown
    logger.info("shutdown_begin")
    
    # Stop TTL cleanup job
    if ttl_task:
        ttl_cleanup_job.stop()
        ttl_task.cancel()
        try:
            await ttl_task
        except asyncio.CancelledError:
            pass
        logger.info("ttl_cleanup_stopped")
    
    # Close database
    db.close()
    logger.info("shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="Memory Infrastructure Phase 2",
    description="Enterprise-grade cognitive state infrastructure with RBAC, policies, and observability",
    version="2.0.0",
    lifespan=lifespan
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS (restricted origins, no wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request size limit middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Limit request body size."""
    if request.method in ["POST", "PUT", "PATCH"]:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_size:
            return JSONResponse(
                status_code=413,
                content={"error": "Request too large", "max_size": settings.max_request_size}
            )
    
    response = await call_next(request)
    return response

# ============================================================================
# ROUTES
# ============================================================================

# Include API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(user_memory_router, prefix="/api/v1")

# ============================================================================
# SYSTEM ENDPOINTS
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    """Root endpoint."""
    return {
        "service": "Memory Infrastructure Phase 2",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "RBAC",
            "Policy Engine",
            "TTL Management",
            "Scoped Memory",
            "Model-Agnostic Extraction",
            "Prometheus Metrics",
            "Structured Logging"
        ]
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check endpoint."""
    db_healthy = db.health_check()
    
    return HealthResponse(
        status="healthy" if db_healthy else "unhealthy",
        database="connected" if db_healthy else "disconnected",
        version="2.0.0"
    )


@app.get("/metrics", tags=["Observability"])
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    """
    if not settings.metrics_enabled:
        return JSONResponse(
            status_code=404,
            content={"error": "Metrics disabled"}
        )
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with logging."""
    logger.error("unhandled_exception",
                 path=request.url.path,
                 method=request.method,
                 error=str(exc),
                 exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
