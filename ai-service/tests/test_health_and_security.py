"""
Unit tests for FastAPI Health Endpoints and Internal Security Bridge.
Day 2 verification suite.
"""

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.main import app

client = TestClient(app)


class TestRootAndLiveness:
    """Tests for public, unauthenticated diagnostic endpoints."""

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == settings.PROJECT_NAME
        assert data["version"] == settings.VERSION
        assert data["status"] == "running"

    def test_public_liveness_probe(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == settings.PROJECT_NAME
        assert data["version"] == settings.VERSION
        assert "timestamp" in data


class TestSecurityBridge:
    """Tests for internal x-internal-key authentication enforcement."""

    def test_readiness_missing_key_returns_401(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 401
        data = response.json()
        assert "Missing required internal security header" in data["detail"]

    def test_readiness_empty_key_returns_401(self):
        response = client.get("/api/v1/health", headers={"x-internal-key": ""})
        assert response.status_code == 401
        data = response.json()
        assert "Missing required internal security header" in data["detail"]

    def test_readiness_invalid_key_returns_403(self):
        response = client.get(
            "/api/v1/health",
            headers={"x-internal-key": "completely_wrong_unauthorized_token"},
        )
        assert response.status_code == 403
        data = response.json()
        assert "Forbidden: Invalid internal security key" in data["detail"]

    def test_readiness_valid_key_returns_200(self):
        response = client.get(
            "/api/v1/health",
            headers={"x-internal-key": settings.INTERNAL_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == settings.PROJECT_NAME
        assert data["version"] == settings.VERSION
        assert data["authenticated"] is True
        assert data["uptime_seconds"] >= 0
        assert "python_version" in data["system"]
        assert "platform" in data["system"]
