import logging
from typing import Dict, Any, List, Optional
import uuid

from app.core.security import get_password_hash
from app.db.connection import execute_query
from app.services.merchant_service import get_merchants, get_merchant_details, create_merchant, update_merchant, \
    regenerate_api_key

logger = logging.getLogger(__name__)


def get_users(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all users

    Parameters:
    - skip: Number of records to skip
    - limit: Maximum number of records to return

    Returns:
    - List of users
    """
    query = """
    SELECT 
        id, email, full_name, is_active, is_superuser, created_at, updated_at
    FROM 
        users
    ORDER BY 
        created_at DESC
    LIMIT %s OFFSET %s
    """

    users = execute_query(query, (limit, skip))

    return users


def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user

    Parameters:
    - user_data: User data

    Returns:
    - Created user
    """
    # Check if email already exists
    check_query = """
    SELECT id FROM users WHERE email = %s
    """

    existing_user = execute_query(check_query, (user_data.get("email"),), single=True)

    if existing_user:
        raise ValueError("Email already exists")

    # Hash password
    password = user_data.get("password")
    if not password:
        raise ValueError("Password is required")

    hashed_password = get_password_hash(password)

    # Build query
    query = """
    INSERT INTO users (
        email, hashed_password, full_name, is_active, is_superuser
    ) VALUES (
        %s, %s, %s, %s, %s
    ) RETURNING id, email, full_name, is_active, is_superuser, created_at, updated_at
    """

    params = (
        user_data.get("email"),
        hashed_password,
        user_data.get("full_name"),
        user_data.get("is_active", True),
        user_data.get("is_superuser", False)
    )

    user = execute_query(query, params, single=True)

    return user


def update_user(user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing user

    Parameters:
    - user_id: User ID
    - user_data: User data

    Returns:
    - Updated user
    """
    # Build update fields
    fields = []
    params = []

    if "email" in user_data:
        # Check if email already exists for another user
        check_query = """
        SELECT id FROM users WHERE email = %s AND id != %s
        """

        existing_user = execute_query(
            check_query,
            (user_data["email"], user_id),
            single=True
        )

        if existing_user:
            raise ValueError("Email already exists")

        fields.append("email = %s")
        params.append(user_data["email"])

    if "full_name" in user_data:
        fields.append("full_name = %s")
        params.append(user_data["full_name"])

    if "is_active" in user_data:
        fields.append("is_active = %s")
        params.append(user_data["is_active"])

    if "is_superuser" in user_data:
        fields.append("is_superuser = %s")
        params.append(user_data["is_superuser"])

    if "password" in user_data:
        hashed_password = get_password_hash(user_data["password"])
        fields.append("hashed_password = %s")
        params.append(hashed_password)

    # If no fields to update, return current user
    if not fields:
        query = """
        SELECT 
            id, email, full_name, is_active, is_superuser, created_at, updated_at
        FROM 
            users
        WHERE 
            id = %s
        """

        user = execute_query(query, (user_id,), single=True)

        if not user:
            raise ValueError("User not found")

        return user

    # Build update query
    update_query = f"""
    UPDATE users
    SET {", ".join(fields)}, updated_at = NOW()
    WHERE id = %s
    RETURNING id, email, full_name, is_active, is_superuser, created_at, updated_at
    """

    params.append(user_id)

    # Execute update
    user = execute_query(update_query, tuple(params), single=True)

    if not user:
        raise ValueError("User not found")

    return user


def delete_user(user_id: str) -> Dict[str, Any]:
    """
    Delete a user

    Parameters:
    - user_id: User ID

    Returns:
    - Deleted user
    """
    # Get user before deletion
    query = """
    SELECT 
        id, email, full_name, is_active, is_superuser, created_at, updated_at
    FROM 
        users
    WHERE 
        id = %s
    """

    user = execute_query(query, (user_id,), single=True)

    if not user:
        raise ValueError("User not found")

    # Check if user is associated with a merchant
    check_query = """
    SELECT id FROM merchants WHERE user_id = %s
    """

    merchant = execute_query(check_query, (user_id,), single=True)

    if merchant:
        raise ValueError("Cannot delete user associated with a merchant")

    # Delete user
    delete_query = """
    DELETE FROM users
    WHERE id = %s
    """

    execute_query(delete_query, (user_id,), fetch=False)

    return user