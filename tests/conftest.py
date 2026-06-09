"""
Pytest configuration and shared fixtures.

Env vars are set before any app import so pydantic-settings doesn't
raise a validation error when the real .env isn't present in CI.
"""
import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.schemas.auth import UserResponse

FAKE_USER = UserResponse(id="user-123", email="test@example.com")


@pytest.fixture()
def client():
    """TestClient with authentication bypassed."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def unauthed_client():
    """TestClient with no dependency overrides (real auth path)."""
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
