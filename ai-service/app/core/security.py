"""
Internal security authentication module.
Protects AI endpoints using the x-internal-key header with constant-time comparison.
"""

import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

INTERNAL_KEY_NAME = "x-internal-key"

api_key_header = APIKeyHeader(
    name=INTERNAL_KEY_NAME,
    auto_error=False,
    description="Shared internal security key required for service-to-service communication",
)


async def verify_internal_key(
    provided_key: str = Security(api_key_header),
) -> str:
    """
    Validates that incoming internal requests contain the valid x-internal-key.

    Uses secrets.compare_digest to prevent side-channel timing attacks.

    Args:
        provided_key: The header value passed in x-internal-key.

    Returns:
        The validated key string if authentication succeeds.

    Raises:
        HTTPException 401: If the header is missing or empty.
        HTTPException 403: If the provided key does not match the configured secret.
    """
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required internal security header: 'x-internal-key'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    expected_key = settings.INTERNAL_API_KEY
    if not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid internal security key.",
        )

    return provided_key
