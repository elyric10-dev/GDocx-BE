from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.schemas.auth import UserResponse

OWNER = UserResponse(id="11111111-1111-1111-1111-111111111111", email="owner@test.com")
OTHER = UserResponse(id="22222222-2222-2222-2222-222222222222", email="other@test.com")

DOCUMENT = {
    "id": "33333333-3333-3333-3333-333333333333",
    "title": "Quarterly report",
    "content_json": {"type": "doc", "content": [{"type": "paragraph"}]},
    "owner_id": OWNER.id,
    "created_at": "2024-06-01T12:00:00+00:00",
    "updated_at": "2024-06-01T12:00:00+00:00",
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_supabase_delete():
    supabase = MagicMock()
    table = MagicMock()
    supabase.table.return_value = table
    table.delete.return_value = table
    table.eq.return_value = table
    table.execute.return_value = MagicMock(data=[DOCUMENT])
    return supabase


def test_only_owner_can_delete_document(client):
    """Document deletion is restricted to the owner, not shared viewers."""
    document_id = DOCUMENT["id"]

    with patch("app.routes.documents._get_document_by_id", return_value=DOCUMENT):
        app.dependency_overrides[get_current_user] = lambda: OTHER
        denied = client.delete(f"/api/documents/{document_id}", headers=_auth_headers())

        app.dependency_overrides[get_current_user] = lambda: OWNER
        with patch(
            "app.routes.documents.get_supabase_admin",
            return_value=_mock_supabase_delete(),
        ):
            allowed = client.delete(f"/api/documents/{document_id}", headers=_auth_headers())

    assert denied.status_code == 404
    assert denied.json()["detail"] == "Document not found"

    assert allowed.status_code == 200
    assert allowed.json() == {"message": "Document deleted"}
