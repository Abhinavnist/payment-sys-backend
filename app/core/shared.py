# app/core/shared.py

from typing import Dict, Any

# Global dictionary to store IP access attempts
ip_access_attempts: Dict[str, Dict[str, Any]] = {}