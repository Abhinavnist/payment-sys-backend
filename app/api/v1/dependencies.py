from fastapi import Depends, HTTPException, status, Request
from typing import Generator, Dict, Any
import hmac
import hashlib
import logging

from app.core.config import settings
from app.core.security import get_current_user, get_current_active_superuser, get_api_key_merchant
from app.schemas.auth import UserInDB
from app.db.connection import get_db_connection


logger = logging.getLogger(__name__)

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

async def verify_sms_source(request: Request) -> bool:
    """
    Verify that the SMS comes from an authorized source
    
    Parameters:
    - request: FastAPI request object
    
    Returns:
    - True if the source is verified, raises HTTP exception otherwise
    """
    # List of authorized device IDs from settings
    authorized_devices = getattr(settings, 'SMS_FORWARDER_DEVICES', [])
    
    # Secret key for HMAC signature
    sms_secret_key = getattr(settings, 'SMS_FORWARDER_SECRET_KEY', '')
    
    # Get client IP
    client_ip = get_client_ip(request)
    
    # Get device ID from headers
    device_id = request.headers.get("X-Device-ID")
    
    # Get signature from headers
    signature = request.headers.get("X-Signature")
    
    # Check if IP is whitelisted (optional, based on your security requirements)
    if hasattr(settings, 'SMS_FORWARDER_IPS') and settings.SMS_FORWARDER_IPS:
        if client_ip not in settings.SMS_FORWARDER_IPS:
            logger.warning(f"SMS from non-whitelisted IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized SMS source IP"
            )
    
    # Check if device is authorized
    if authorized_devices and device_id not in authorized_devices:
        logger.warning(f"SMS from unauthorized device: {device_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized SMS forwarder device"
        )
    
    # If signature verification is required
    if sms_secret_key and signature:
        # Get request body as bytes
        body = await request.body()
        
        # Create HMAC signature
        expected_signature = hmac.new(
            sms_secret_key.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Verify signature
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(f"Invalid SMS signature from device: {device_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature"
            )
    
    return True