"""
Integration-style tests for the /api/documents routes.

Supabase calls are mocked via pytest-mock so the suite runs without
a real Supabase project.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat()

FAKE_DOC = {
    "id": "doc-001",
    "title": "Test Document",
    "content_json": {"type": "doc", "content": [{"type": "paragraph"}]},
    "owner_id": "user-123",
    "created_at": NOW,
    "updated_at": NOW,
}


def _mock_response(data):
    """Build a mock object that looks like a Supabase execute() response."""
    m = MagicMock()
    m.data = data
    return m


# ---------------------------------------------------------------------------
# GET /api/documents
# ---------------------------------------------------------------------------

class TestListDocuments:
    def test_returns_empty_list(self, client, mocker):
        mocker.patch(
            "app.routes.documents.supabase_execute",
            return_value=_mock_response([]),
        )
        response = client.get("/api/documents")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_documents(self, client, mocker):
        mocker.patch(
            "app.routes.documents.supabase_execute",
            side_effect=[
                _mock_response([FAKE_DOC]),
                _mock_response([]),
            ],
        )
        response = client.get("/api/documents")
        assert response.status_code == 200
        docs = response.json()
        assert len(docs) == 1
        assert docs[0]["id"] == "doc-001"
        assert docs[0]["title"] == "Test Document"


# ---------------------------------------------------------------------------
# POST /api/documents
# ---------------------------------------------------------------------------

class TestCreateDocument:
    def test_create_with_title(self, client, mocker):
        mocker.patch(
            "app.routes.documents.supabase_execute",
            return_value=_mock_response([FAKE_DOC]),
        )
        response = client.post("/api/documents", json={"title": "Test Document"})
        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Test Document"
        assert body["owner_id"] == "user-123"

    def test_create_with_default_title(self, client, mocker):
        doc = {**FAKE_DOC, "title": "Untitled"}
        mocker.patch(
            "app.routes.documents.supabase_execute",
            return_value=_mock_response([doc]),
        )
        response = client.post("/api/documents", json={})
        assert response.status_code == 201

    def test_create_empty_title_rejected(self, client):
        response = client.post("/api/documents", json={"title": ""})
        assert response.status_code == 422

    def test_create_title_too_long_rejected(self, client):
        response = client.post("/api/documents", json={"title": "x" * 501})
        assert response.status_code == 422

    def test_requires_auth(self, unauthed_client):
        response = unauthed_client.post("/api/documents", json={"title": "T"})
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/documents/{id}
# ---------------------------------------------------------------------------

class TestGetDocument:
    def test_get_own_document(self, client, mocker):
        mocker.patch(
            "app.routes.documents.supabase_execute",
            return_value=_mock_response([FAKE_DOC]),
        )
        response = client.get("/api/documents/doc-001")
        assert response.status_code == 200
        assert response.json()["id"] == "doc-001"

    def test_get_not_found(self, client, mocker):
        mocker.patch(
            "app.routes.documents.supabase_execute",
            return_value=_mock_response([]),
        )
        response = client.get("/api/documents/nonexistent")
        assert response.status_code == 404

    def test_get_document_shared_with_user(self, client, mocker):
        """A document owned by someone else but shared with current user is accessible."""
        shared_doc = {**FAKE_DOC, "owner_id": "other-user"}
        mocker.patch(
            "app.routes.documents.supabase_execute",
            side_effect=[
                _mock_response([shared_doc]),
                _mock_response([{"id": "share-1"}]),
            ],
        )
        response = client.get("/api/documents/doc-001")
        assert response.status_code == 200

    def test_get_unshared_foreign_document_is_404(self, client, mocker):
        foreign_doc = {**FAKE_DOC, "owner_id": "other-user"}
        mocker.patch(
            "app.routes.documents.supabase_execute",
            side_effect=[
                _mock_response([foreign_doc]),
                _mock_response([]),
            ],
        )
        response = client.get("/api/documents/doc-001")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/documents/{id}
# ---------------------------------------------------------------------------

class TestUpdateDocument:
    def test_update_title(self, client, mocker):
        updated = {**FAKE_DOC, "title": "New Title"}
        mocker.patch(
            "app.routes.documents.supabase_execute",
            side_effect=[
                _mock_response([FAKE_DOC]),
                _mock_response([updated]),
            ],
        )
        response = client.put("/api/documents/doc-001", json={"title": "New Title"})
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    def test_update_with_no_fields_rejected(self, client):
        response = client.put("/api/documents/doc-001", json={})
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()

    def test_update_empty_title_rejected(self, client):
        response = client.put("/api/documents/doc-001", json={"title": ""})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/documents/{id}
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    def test_delete_own_document(self, client, mocker):
        mocker.patch(
            "app.routes.documents.supabase_execute",
            side_effect=[
                _mock_response([FAKE_DOC]),
                _mock_response([FAKE_DOC]),
            ],
        )
        response = client.delete("/api/documents/doc-001")
        assert response.status_code == 200
        assert response.json()["message"] == "Document deleted"

    def test_delete_foreign_document_rejected(self, client, mocker):
        foreign_doc = {**FAKE_DOC, "owner_id": "other-user"}
        mocker.patch(
            "app.routes.documents.supabase_execute",
            return_value=_mock_response([foreign_doc]),
        )
        response = client.delete("/api/documents/doc-001")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/documents/{id}/share
# ---------------------------------------------------------------------------

class TestShareDocument:
    def test_share_with_valid_user(self, client, mocker):
        share_row = {
            "id": "share-1",
            "document_id": "doc-001",
            "user_id": "user-456",
            "created_at": NOW,
        }
        mocker.patch(
            "app.routes.documents.supabase_execute",
            side_effect=[
                _mock_response([FAKE_DOC]),
                _mock_response([{"id": "user-456"}]),
                _mock_response([share_row]),
            ],
        )
        response = client.post(
            "/api/documents/doc-001/share", json={"user_id": "user-456"}
        )
        assert response.status_code == 200
        assert response.json()["user_id"] == "user-456"

    def test_cannot_share_with_self(self, client, mocker):
        mocker.patch(
            "app.routes.documents.supabase_execute",
            return_value=_mock_response([FAKE_DOC]),
        )
        response = client.post(
            "/api/documents/doc-001/share", json={"user_id": "user-123"}
        )
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"]
