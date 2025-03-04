from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from app.schemas.auth import Token, UserInDB, UserCreate, UserUpdate
from app.db.connection import execute_query

router = APIRouter()


@router.post("/login/access-token", response_model=Token)
async def login_access_token(
        form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Query user by email
    query = """
    SELECT 
        id, email, hashed_password, full_name, is_active, is_superuser
    FROM 
        users
    WHERE 
        email = %s
    """

    user = execute_query(query, (form_data.username,), single=True)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user["id"],
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/test-token", response_model=UserInDB)
async def test_token(current_user: UserInDB = Depends(get_current_user)) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/reset-password")
async def reset_password(
        current_password: str = Body(...),
        new_password: str = Body(...),
        current_user: UserInDB = Depends(get_current_user)
) -> Any:
    """
    Reset password
    """
    # Verify current password
    query = """
    SELECT 
        hashed_password
    FROM 
        users
    WHERE 
        id = %s
    """

    user = execute_query(query, (current_user.id,), single=True)

    if not verify_password(current_password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    # Update password
    hashed_password = get_password_hash(new_password)

    update_query = """
    UPDATE users
    SET 
        hashed_password = %s,
        updated_at = NOW()
    WHERE 
        id = %s
    """

    execute_query(update_query, (hashed_password, current_user.id), fetch=False)

    return {"message": "Password updated successfully"}