"""
Tests for Pydantic request/response schemas.

These are pure-Python unit tests — no HTTP stack, no Supabase.
"""
import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.documents import (
    DEFAULT_CONTENT_JSON,
    DocumentCreate,
    DocumentUpdate,
)


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class TestRegisterRequest:
    def test_valid(self):
        req = RegisterRequest(email="user@example.com", password="secret123")
        assert req.email == "user@example.com"
        assert req.full_name is None

    def test_with_full_name(self):
        req = RegisterRequest(email="user@example.com", password="secret123", full_name="Alice")
        assert req.full_name == "Alice"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="secret123")

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="short")


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(email="user@example.com", password="any")
        assert req.email == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="any")


# ---------------------------------------------------------------------------
# Document schemas
# ---------------------------------------------------------------------------

class TestDocumentCreate:
    def test_defaults(self):
        doc = DocumentCreate(title="My Doc")
        assert doc.title == "My Doc"
        assert doc.content_json is None

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            DocumentCreate(title="x" * 501)

    def test_title_empty(self):
        with pytest.raises(ValidationError):
            DocumentCreate(title="")

    def test_custom_content_json(self):
        content = {"type": "doc", "content": []}
        doc = DocumentCreate(title="T", content_json=content)
        assert doc.content_json == content


class TestDocumentUpdate:
    def test_both_none_is_valid_schema(self):
        """Schema allows both None; the route rejects it via HTTPException."""
        update = DocumentUpdate()
        assert update.title is None
        assert update.content_json is None

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            DocumentUpdate(title="x" * 501)

    def test_title_empty(self):
        with pytest.raises(ValidationError):
            DocumentUpdate(title="")

    def test_partial_update_title_only(self):
        update = DocumentUpdate(title="New title")
        assert update.title == "New title"
        assert update.content_json is None


class TestDefaultContentJson:
    def test_structure(self):
        assert DEFAULT_CONTENT_JSON["type"] == "doc"
        assert isinstance(DEFAULT_CONTENT_JSON["content"], list)
