"""
Health check endpoints for the AI Service.
Provides unauthenticated liveness and authenticated readiness/diagnostics probes.
"""

from datetime import datetime, timezone
import os
import platform
import sys
import time
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import verify_internal_key

router = APIRouter(tags=["Health & Diagnostics"])

SERVICE_START_TIME = time.time()


class LivenessResponse(BaseModel):
    status: str = "healthy"
    service: str
    version: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str = "healthy"
    service: str
    version: str
    environment: str
    uptime_seconds: int
    timestamp: str
    authenticated: bool = True
    system: Dict[str, Any] = Field(default_factory=dict)


@router.get(
    "/health",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Unauthenticated Liveness Probe",
    description="Quick ping endpoint for orchestrators (Docker/Kubernetes) to verify the server is running.",
)
async def liveness_probe() -> LivenessResponse:
    return LivenessResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/api/v1/health",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticated System Readiness Probe",
    description="Deep diagnostic probe that requires the internal security key. Used by the Gateway bridge.",
)
async def readiness_probe(
    _authenticated: str = Depends(verify_internal_key),
) -> ReadinessResponse:
    uptime = int(time.time() - SERVICE_START_TIME)

    return ReadinessResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=uptime,
        timestamp=datetime.now(timezone.utc).isoformat(),
        authenticated=True,
        system={
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "pid": os.getpid(),
        },
    )
