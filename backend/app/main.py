from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import logging
import sys

from app.config import get_settings
from app.database import init_db, close_db
from app.streaming.events import close_streaming, get_stream_manager, get_sse_manager
from app.waf.gateway import get_waf_gateway
from app.context.openapi import get_app_context
from app.api import waf, events, context, attack_lab, batch, models

settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=getattr(logging, settings.log_level.upper()),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting NEXA WAF Backend")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize WAF gateway
    waf_gateway = await get_waf_gateway()
    logger.info("WAF Gateway initialized")

    # Load demo OpenAPI spec if available
    app_context = get_app_context()
    try:
        import os
        spec_path = os.path.join(os.path.dirname(__file__), "..", "..", "demo-app", "openapi.json")
        if os.path.exists(spec_path):
            app_context.load_from_file(spec_path)
            await app_context.persist_endpoints()
            logger.info("Demo OpenAPI spec loaded")
    except Exception as e:
        logger.warning(f"Could not load demo OpenAPI spec: {e}")

    # Initialize streaming
    stream_manager = await get_stream_manager()
    if stream_manager.is_connected():
        sse_manager = await get_sse_manager()
        logger.info("Event streaming initialized")
    else:
        logger.warning("Redis not available - event streaming disabled")

    yield

    # Shutdown
    logger.info("Shutting down NEXA WAF Backend")
    await close_streaming()
    await close_db()


app = FastAPI(
    title="NEXA Adaptive Transformer WAF",
    description="Application-Aware Web Application Firewall with Transformer-based Detection",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Include routers
app.include_router(waf.router)
app.include_router(events.router)
app.include_router(context.router)
app.include_router(attack_lab.router)
app.include_router(batch.router)
app.include_router(models.router)


@app.get("/")
async def root():
    return {
        "name": "NEXA Adaptive Transformer WAF",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    from app.api.waf import health_check
    return await health_check()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
        reload=settings.debug and settings.environment != "production",
    )