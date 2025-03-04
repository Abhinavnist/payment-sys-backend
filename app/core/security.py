from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
import secrets
import string
import hashlib
import hmac
import logging

from jose import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from pydantic import ValidationError

from app.core.config import settings
from app.db.connection import execute_query
from app.schemas.auth import TokenPayload, UserInDB

# Setup logging
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token")

# API Key scheme
api_key_header = APIKeyHeader(name="X-API-Key")


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token

    Parameters:
    - subject: Token subject (usually user ID)
    - expires_delta: Token expiration time

    Returns:
    - JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Parameters:
    - plain_password: Plain text password
    - hashed_password: Hashed password from database

    Returns:
    - True if password is correct, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password

    Parameters:
    - password: Plain text password

    Returns:
    - Hashed password
    """
    return pwd_context.hash(password)


def generate_api_key() -> str:
    """
    Generate a random API key

    Returns:
    - Random API key string
    """
    # Generate a 32-character random string with letters and digits
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(32))
    return api_key


def generate_webhook_signature(payload: Dict[str, Any], secret: str) -> str:
    """
    Generate HMAC signature for webhook payloads

    Parameters:
    - payload: Webhook payload
    - secret: Merchant's webhook secret

    Returns:
    - Signature string
    """
    # Convert payload to string
    payload_str = str(sorted([(k, v) for k, v in payload.items()]))

    # Create HMAC signature
    signature = hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_webhook_signature(
        payload: Dict[str, Any],
        signature: str,
        secret: str
) -> bool:
    """
    Verify webhook signature

    Parameters:
    - payload: Webhook payload
    - signature: Signature from request
    - secret: Merchant's webhook secret

    Returns:
    - True if signature is valid, False otherwise
    """
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """
    Get current user from JWT token

    Parameters:
    - token: JWT token

    Returns:
    - User object

    Raises:
    - HTTPException: If token is invalid or user not found
    """
    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        token_data = TokenPayload(**payload)

        # Check token expiration
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (jwt.JWTError, ValidationError) as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    query = """
    SELECT 
        id, email, full_name, is_active, is_superuser
    FROM 
        users
    WHERE 
        id = %s
    """
    user = execute_query(query, (token_data.sub,), single=True)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return UserInDB(**user)


async def get_current_active_superuser(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """
    Get current superuser

    Parameters:
    - current_user: Current user

    Returns:
    - User object

    Raises:
    - HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


async def get_api_key_merchant(api_key: str = Depends(api_key_header)):
    """
    Get merchant from API key

    Parameters:
    - api_key: API key from request header

    Returns:
    - Merchant object

    Raises:
    - HTTPException: If API key is invalid or merchant not found
    """
    query = """
    SELECT 
        m.id, m.business_name, m.is_active, m.callback_url, m.webhook_secret,
        m.min_deposit, m.max_deposit, m.min_withdrawal, m.max_withdrawal
    FROM 
        merchants m
    WHERE 
        m.api_key = %s
    """
    merchant = execute_query(query, (api_key,), single=True)

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    if not merchant["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant account is inactive",
        )

    return merchant


def verify_ip_whitelist(merchant_id: str, ip_address: str) -> bool:
    """
    Verify if IP address is in whitelist

    Parameters:
    - merchant_id: Merchant ID
    - ip_address: Client IP address

    Returns:
    - True if IP is whitelisted, False otherwise
    """
    query = """
    SELECT 
        COUNT(*) as count
    FROM 
        ip_whitelist
    WHERE 
        merchant_id = %s AND ip_address = %s
    """
    result = execute_query(query, (merchant_id, ip_address), single=True)

    return result["count"] > 0