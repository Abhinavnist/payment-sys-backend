import time
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import redis
from typing import Callable, Dict, Any, Optional

from app.core.security import get_api_key_merchant
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to implement rate limiting for API endpoints
    """

    def __init__(self, app, redis_host=None, redis_port=None, redis_db=None, excluded_paths=None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or []

        # Connect to Redis
        self.redis = redis.Redis(
            host=redis_host or settings.REDIS_HOST,
            port=redis_port or settings.REDIS_PORT,
            db=redis_db or settings.REDIS_DB
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        # Skip check for excluded paths
        for path in self.excluded_paths:
            if request.url.path.startswith(path):
                return await call_next(request)

        # Skip check if not an API endpoint
        if not request.url.path.startswith("/api/v1/payments"):
            return await call_next(request)

        try:
            # Get API key from header
            api_key = request.headers.get("X-API-Key")

            if not api_key:
                return await call_next(request)

            # Get merchant from API key
            merchant = await get_api_key_merchant(api_key)
            merchant_id = merchant["id"]

            # Extract endpoint from path
            endpoint = self._extract_endpoint(request.url.path)

            # Check rate limit
            if not self._check_rate_limit(merchant_id, endpoint):
                logger.warning(f"Rate limit exceeded for merchant {merchant_id} on endpoint {endpoint}")

                # Return error response
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "code": 4001,
                        "message": "Rate limit exceeded",
                        "detail": "Too many requests, please try again later"
                    }
                )

            # Rate limit not exceeded, continue request
            return await call_next(request)

        except HTTPException:
            # If API key is invalid, let the regular API key check handle it
            return await call_next(request)
        except Exception as e:
            logger.error(f"Error in rate limit middleware: {e}")
            return await call_next(request)

    def _extract_endpoint(self, path: str) -> str:
        """
        Extract endpoint from path

        Parameters:
        - path: Request path

        Returns:
        - Endpoint string (e.g., 'payments/request')
        """
        # Remove API prefix and leading/trailing slashes
        endpoint = path.replace(settings.API_V1_STR, "").strip("/")

        # Get base endpoint (first part of path)
        return endpoint.split("/")[0] if endpoint else "default"

    def _check_rate_limit(self, merchant_id: str, endpoint: str) -> bool:
        """
        Check if request is within rate limit

        Parameters:
        - merchant_id: Merchant ID
        - endpoint: API endpoint

        Returns:
        - True if request is within rate limit, False otherwise
        """
        # Create Redis key for this merchant and endpoint
        key = f"rate_limit:{merchant_id}:{endpoint}"

        # Get current time (minute)
        current_minute = int(time.time() / 60)

        # Create Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Get rate limit for this merchant and endpoint
        limit_key = f"rate_limit:config:{merchant_id}:{endpoint}"
        pipe.get(limit_key)

        # Get current request count
        pipe.get(key)

        # Execute pipeline
        limit_value, current_count = pipe.execute()

        # Convert values
        rate_limit = int(limit_value) if limit_value else settings.DEFAULT_RATE_LIMIT
        count = int(current_count) if current_count else 0

        # Check if rate limit is exceeded
        if count >= rate_limit:
            return False

        # Increment request count
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)  # Expire after 1 minute
        pipe.execute()

        # Log rate limit usage
        self._log_rate_limit_usage(merchant_id, endpoint)

        return True

    def _log_rate_limit_usage(self, merchant_id: str, endpoint: str) -> None:
        """
        Log rate limit usage to database

        Parameters:
        - merchant_id: Merchant ID
        - endpoint: API endpoint
        """
        try:
            from app.db.connection import execute_query

            # Get client IP (for logging only)
            client_ip = "0.0.0.0"  # Placeholder

            # Insert rate limit log
            query = """
            INSERT INTO rate_limit_logs (merchant_id, endpoint, ip_address)
            VALUES (%s, %s, %s)
            """

            execute_query(query, (merchant_id, endpoint, client_ip), fetch=False)
        except Exception as e:
            logger.error(f"Error logging rate limit usage: {e}")