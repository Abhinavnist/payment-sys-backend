import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from app.core.security import get_password_hash, verify_password, create_access_token
from app.db.connection import execute_query
from app.models.user import User

logger = logging.getLogger(__name__)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user with email and password

    Parameters:
    - email: User email
    - password: User password

    Returns:
    - User object if authentication is successful, None otherwise
    """
    try:
        # Get user from database
        query = """
        SELECT 
            id, email, hashed_password, full_name, is_active, is_superuser
        FROM 
            users
        WHERE 
            email = %s
        """

        user = execute_query(query, (email,), single=True)

        if not user:
            return None

        # Verify password
        if not verify_password(password, user["hashed_password"]):
            return None

        # Check if user is active
        if not user["is_active"]:
            return None

        # Return user without hashed_password
        user_data = dict(user)
        user_data.pop("hashed_password", None)
        return user_data

    except Exception as e:
        logger.error(f"Error authenticating user: {e}")
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by ID

    Parameters:
    - user_id: User ID

    Returns:
    - User object if found, None otherwise
    """
    try:
        # Get user from database
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
            return None

        return user

    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None


def create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create new user

    Parameters:
    - user_data: User data

    Returns:
    - Created user object if successful, None otherwise
    """
    try:
        # Check if email already exists
        check_query = """
        SELECT id FROM users WHERE email = %s
        """

        existing_user = execute_query(check_query, (user_data.get("email"),), single=True)

        if existing_user:
            raise ValueError("Email already exists")

        # Hash password
        hashed_password = get_password_hash(user_data.get("password"))

        # Insert user
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

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise


def update_user(user_id: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update user

    Parameters:
    - user_id: User ID
    - user_data: User data

    Returns:
    - Updated user object if successful, None otherwise
    """
    try:
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
            return get_user_by_id(user_id)

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

    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise


def delete_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Delete user

    Parameters:
    - user_id: User ID

    Returns:
    - Deleted user object if successful, None otherwise
    """
    try:
        # Get user before deletion
        user = get_user_by_id(user_id)

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

    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise


def reset_password(user_id: str, current_password: str, new_password: str) -> bool:
    """
    Reset user password

    Parameters:
    - user_id: User ID
    - current_password: Current password
    - new_password: New password

    Returns:
    - True if password reset is successful, False otherwise
    """
    try:
        # Get user from database
        query = """
        SELECT 
            hashed_password
        FROM 
            users
        WHERE 
            id = %s
        """

        user = execute_query(query, (user_id,), single=True)

        if not user:
            raise ValueError("User not found")

        # Verify current password
        if not verify_password(current_password, user["hashed_password"]):
            raise ValueError("Current password is incorrect")

        # Hash new password
        hashed_password = get_password_hash(new_password)

        # Update password
        update_query = """
        UPDATE users
        SET 
            hashed_password = %s,
            updated_at = NOW()
        WHERE 
            id = %s
        """

        execute_query(update_query, (hashed_password, user_id), fetch=False)

        return True

    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise


def generate_auth_token(user_id: str) -> str:
    """
    Generate authentication token

    Parameters:
    - user_id: User ID

    Returns:
    - Authentication token
    """
    return create_access_token(subject=user_id)


def get_users(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get list of users

    Parameters:
    - skip: Number of records to skip
    - limit: Maximum number of records to return

    Returns:
    - List of users
    """
    try:
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

    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise