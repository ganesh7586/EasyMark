"""
Unit tests for FastAPI Health Endpoints and Internal Security Bridge.
Day 2 verification suite.
"""

from fastapi import HTTPException
import pytest

from app.api.health import liveness_probe, readiness_probe
from app.core.config import settings
from app.core.security import verify_internal_key


def run_coroutine(coro):
    """Directly drives coroutines synchronously without spinning up socket-bound loops."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


class TestRootAndLiveness:
    """Tests for public, unauthenticated diagnostic endpoints."""

    def test_public_liveness_probe(self):
        response = run_coroutine(liveness_probe())
        assert response.status == "healthy"
        assert response.service == settings.PROJECT_NAME
        assert response.version == settings.VERSION
        assert response.timestamp is not None


class TestSecurityBridge:
    """Tests for internal x-internal-key authentication enforcement."""

    def test_readiness_missing_key_returns_401(self):
        with pytest.raises(HTTPException) as exc_info:
            run_coroutine(verify_internal_key(provided_key=""))
        assert exc_info.value.status_code == 401
        assert "Missing required internal security header" in exc_info.value.detail

    def test_readiness_none_key_returns_401(self):
        with pytest.raises(HTTPException) as exc_info:
            run_coroutine(verify_internal_key(provided_key=None))
        assert exc_info.value.status_code == 401
        assert "Missing required internal security header" in exc_info.value.detail

    def test_readiness_invalid_key_returns_403(self):
        with pytest.raises(HTTPException) as exc_info:
            run_coroutine(verify_internal_key(provided_key="completely_wrong_unauthorized_token"))
        assert exc_info.value.status_code == 403
        assert "Forbidden: Invalid internal security key" in exc_info.value.detail

    def test_readiness_valid_key_authenticates(self):
        validated = run_coroutine(verify_internal_key(provided_key=settings.INTERNAL_API_KEY))
        assert validated == settings.INTERNAL_API_KEY

    def test_readiness_probe_authenticated_execution(self):
        response = run_coroutine(readiness_probe(_authenticated=settings.INTERNAL_API_KEY))
        assert response.status == "healthy"
        assert response.service == settings.PROJECT_NAME
        assert response.version == settings.VERSION
        assert response.authenticated is True
        assert response.uptime_seconds >= 0
        assert "python_version" in response.system
        assert "platform" in response.system
