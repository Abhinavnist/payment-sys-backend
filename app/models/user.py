from datetime import datetime
from uuid import UUID
from typing import Optional


class User:
    """User model representing a user in the system"""

    def __init__(
            self,
            id: UUID,
            email: str,
            hashed_password: str,
            full_name: str,
            is_active: bool = True,
            is_superuser: bool = False,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.is_active = is_active
        self.is_superuser = is_superuser
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @classmethod
    def from_dict(cls, data: dict):
        """Create a User instance from a dictionary"""
        return cls(
            id=data.get("id"),
            email=data.get("email"),
            hashed_password=data.get("hashed_password"),
            full_name=data.get("full_name"),
            is_active=data.get("is_active", True),
            is_superuser=data.get("is_superuser", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def to_dict(self):
        """Convert User instance to a dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }