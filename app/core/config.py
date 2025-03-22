# import os
# import secrets
# from typing import Any, Dict, List, Optional, Union
# from pydantic import field_validator
# from pydantic_settings import BaseSettings


# class Settings(BaseSettings):
#     API_V1_STR: str = "/api/v1"
#     SECRET_KEY: str = secrets.token_urlsafe(32)
#     # 60 minutes * 24 hours * 8 days = 8 days
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
#     SERVER_NAME: str = "Payment System API"
#     SERVER_HOST: str = "localhost"
#     SERVER_PORT: int = 5678

#     # CORS
#     BACKEND_CORS_ORIGINS: list[str] | str = ["http://localhost:3000", "http://localhost:8000","http://0.0.0.0"]

#     @field_validator("BACKEND_CORS_ORIGINS", mode="before")
#     def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
#         if isinstance(v, str) and not v.startswith("["):
#             return [i.strip() for i in v.split(",")]
#         elif isinstance(v, (list, str)):
#             return v
#         raise ValueError(v)

#     # PostgreSQL Connection
#     POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
#     POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
#     POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "root")
#     POSTGRES_DB: str = os.getenv("POSTGRES_DB", "payment_system")
#     POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

#     # # Redis Connection (for rate limiting)
#     # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
#     # REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
#     # REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

#     # Payment Settings
#     DEFAULT_CURRENCY: str = "INR"
#     MIN_DEPOSIT_AMOUNT: int = 500
#     MAX_DEPOSIT_AMOUNT: int = 300000
#     MIN_WITHDRAWAL_AMOUNT: int = 1000
#     MAX_WITHDRAWAL_AMOUNT: int = 1000000

#     # File Upload
#     UPLOAD_FOLDER: str = "uploads"
#     ALLOWED_EXTENSIONS: List[str] = ["csv", "xlsx", "pdf", "xls"]
#     MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB

#     # Webhook Settings
#     WEBHOOK_RETRY_ATTEMPTS: int = 3
#     WEBHOOK_RETRY_DELAY: int = 60  # seconds

#     # QR Code Settings
#     QR_CODE_BOX_SIZE: int = 10
#     QR_CODE_BORDER: int = 4

#     # API Rate Limiting
#     DEFAULT_RATE_LIMIT: int = 60  # requests per minute

#     class Config:
#         case_sensitive = True
#         env_file = ".env"


# settings = Settings()
import os
import secrets
from typing import Any, Dict, List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    SERVER_NAME: str = "Payment System API"
    SERVER_HOST: str = "localhost"
    SERVER_PORT: int = 5678

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://0.0.0.0"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # PostgreSQL Connection
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "root")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "payment_system")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))  # Cast to int

    # Redis Connection (for rate limiting)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))  # Cast to int
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))  # Cast to int

    # Payment Settings
    DEFAULT_CURRENCY: str = "INR"
    MIN_DEPOSIT_AMOUNT: int = 500
    MAX_DEPOSIT_AMOUNT: int = 300000
    MIN_WITHDRAWAL_AMOUNT: int = 1000
    MAX_WITHDRAWAL_AMOUNT: int = 1000000

    # File Upload
    UPLOAD_FOLDER: str = "uploads"
    ALLOWED_EXTENSIONS: List[str] = ["csv", "xlsx", "pdf", "xls"]
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB

    # Webhook Settings
    WEBHOOK_RETRY_ATTEMPTS: int = 3
    WEBHOOK_RETRY_DELAY: int = 60  # seconds

    # QR Code Settings
    QR_CODE_BOX_SIZE: int = 10
    QR_CODE_BORDER: int = 4

    # API Rate Limiting
    DEFAULT_RATE_LIMIT: int = 60  # requests per minute

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
