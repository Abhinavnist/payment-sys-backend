import logging
import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.security import get_current_active_superuser
from app.api.v1.api import api_router
from app.middlewares.ip_whitelist import IPWhitelistMiddleware
from app.middlewares.rate_limiter import RateLimiterMiddleware
from app.services.webhook_service import process_failed_webhooks
from app.db.connection import initialize_connection_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create upload directories
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_FOLDER, "bank_statements"), exist_ok=True)
# Initialize database connection pool
initialize_connection_pool()

# App startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create upload directories
    logger.info("Starting up application")

    # Yield control back to FastAPI
    yield

    # Shutdown: cleanup
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.SERVER_NAME,
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add IP whitelist middleware
app.add_middleware(
    IPWhitelistMiddleware,
    excluded_paths=["/api/docs", "/api/openapi.json", "/api/v1/auth"]
)

# # Add rate limiter middleware
# app.add_middleware(
#     RateLimiterMiddleware,
#     excluded_paths=["/api/docs", "/api/openapi.json", "/api/v1/auth"]
# )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Custom exception handler for standard exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Payment System API"}


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Scheduled task endpoint (for cron job)
@app.post("/tasks/process-failed-webhooks")
async def run_process_failed_webhooks(request: Request):
    # Simple API key check for cron job security
    api_key = request.headers.get("X-API-Key")
    if api_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    # Process failed webhooks
    await process_failed_webhooks()

    return {"status": "success", "message": "Failed webhooks processed"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True
    )