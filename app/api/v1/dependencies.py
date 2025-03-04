from fastapi import Depends, HTTPException, status, Request
from typing import Generator, Dict, Any

from app.core.config import settings
from app.core.security import get_current_user, get_current_active_superuser, get_api_key_merchant
from app.schemas.auth import UserInDB
from app.db.connection import get_db_connection


def get_client_ip(request: Request) -> str:
    """
    Get the client IP address from the request

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


def check_api_key_and_ip(
        request: Request,
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
) -> Dict[str, Any]:
    """
    Check both API key and IP whitelist

    Parameters:
    - request: FastAPI request object
    - merchant: Merchant object from API key

    Returns:
    - Merchant object if checks pass

    Raises:
    - HTTPException: If IP is not whitelisted
    """
    from app.core.security import verify_ip_whitelist

    # Get client IP
    client_ip = get_client_ip(request)

    # Check if IP is whitelisted
    if not verify_ip_whitelist(merchant["id"], client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IP Address is not whitelisted"
        )

    return merchant


def get_db() -> Generator:
    """
    Get database connection for dependency injection

    Returns:
    - Database connection
    """
    with get_db_connection() as conn:
        yield conn