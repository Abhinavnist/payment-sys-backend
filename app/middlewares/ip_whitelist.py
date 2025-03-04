from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from typing import Callable, Dict, Any, Optional

from app.core.security import get_api_key_merchant, verify_ip_whitelist

logger = logging.getLogger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check if the client IP is whitelisted
    for the merchant associated with the API key
    """

    def __init__(self, app, excluded_paths=None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        # Skip check for excluded paths
        for path in self.excluded_paths:
            if request.url.path.startswith(path):
                return await call_next(request)

        # Skip check if not an API endpoint
        if not request.url.path.startswith("/api/v1/payments"):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        try:
            # Get API key from header
            api_key = request.headers.get("X-API-Key")

            if not api_key:
                return await call_next(request)

            # Get merchant ID from API key
            merchant = await get_api_key_merchant(api_key)
            merchant_id = merchant["id"]

            # Check if IP is whitelisted
            if not verify_ip_whitelist(merchant_id, client_ip):
                logger.warning(f"IP {client_ip} not whitelisted for merchant {merchant_id}")

                # Return error response
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "code": 1001,
                        "message": "IP Address is not whitelisted",
                        "detail": "IP Address not added in our Back End"
                    }
                )

            # IP is whitelisted, continue request
            return await call_next(request)

        except HTTPException:
            # If API key is invalid, let the regular API key check handle it
            return await call_next(request)
        except Exception as e:
            logger.error(f"Error in IP whitelist middleware: {e}")
            return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request

        Parameters:
        - request: FastAPI request object

        Returns:
        - Client IP address
        """
        # Check for X-Forwarded-For header (when behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")

        if forwarded_for:
            # Get the first IP in the list (client IP)
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client address
        return request.client.host