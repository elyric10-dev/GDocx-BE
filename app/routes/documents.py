from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError

from app.dependencies import get_current_user
from app.schemas.auth import UserResponse
from app.schemas.documents import (
    DEFAULT_CONTENT_JSON,
    DocumentCreate,
    DocumentResponse,
    DocumentSummary,
    DocumentUpdate,
)
from app.services.supabase_client import get_supabase_admin

router = APIRouter()

MISSING_TABLE_MESSAGE = (
    "The documents table does not exist yet. "
    "Run backend/database/documents.sql in the Supabase SQL Editor, then retry."
)


def _handle_supabase_error(exc: Exception) -> None:
    if isinstance(exc, APIError) and exc.code == "PGRST205":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=MISSING_TABLE_MESSAGE,
        ) from exc
    raise exc


def _parse_document(row: dict[str, Any]) -> DocumentResponse:
    return DocumentResponse(
        id=str(row["id"]),
        title=row["title"],
        content_json=row["content_json"],
        owner_id=str(row["owner_id"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _parse_summary(row: dict[str, Any]) -> DocumentSummary:
    return DocumentSummary(
        id=str(row["id"]),
        title=row["title"],
        owner_id=str(row["owner_id"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_owned_document(document_id: str, owner_id: str) -> dict[str, Any]:
    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("owner_id", owner_id)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return response.data[0]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    body: DocumentCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> DocumentResponse:
    supabase = get_supabase_admin()
    payload = {
        "title": body.title,
        "content_json": DEFAULT_CONTENT_JSON,
        "owner_id": current_user.id,
    }

    try:
        response = supabase.table("documents").insert(payload).execute()
    except Exception as exc:
        try:
            _handle_supabase_error(exc)
        except HTTPException:
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create document",
        )

    return _parse_document(response.data[0])


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    current_user: UserResponse = Depends(get_current_user),
) -> list[DocumentSummary]:
    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("documents")
            .select("id, title, owner_id, created_at, updated_at")
            .eq("owner_id", current_user.id)
            .order("updated_at", desc=True)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    return [_parse_summary(row) for row in response.data or []]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> DocumentResponse:
    row = _get_owned_document(document_id, current_user.id)
    return _parse_document(row)


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    body: DocumentUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> DocumentResponse:
    if body.title is None and body.content_json is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of title or content_json is required",
        )

    _get_owned_document(document_id, current_user.id)

    updates: dict[str, Any] = {}
    if body.title is not None:
        updates["title"] = body.title
    if body.content_json is not None:
        updates["content_json"] = body.content_json

    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("documents")
            .update(updates)
            .eq("id", document_id)
            .eq("owner_id", current_user.id)
            .execute()
        )
    except Exception as exc:
        try:
            _handle_supabase_error(exc)
        except HTTPException:
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return _parse_document(response.data[0])
