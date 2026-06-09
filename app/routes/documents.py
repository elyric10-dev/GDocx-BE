from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError

from app.dependencies import get_current_user
from app.schemas.auth import UserResponse
from app.schemas.documents import (
    DEFAULT_CONTENT_JSON,
    DocumentCreate,
    DocumentResponse,
    DocumentShareCreate,
    DocumentShareDetail,
    DocumentShareResponse,
    DocumentSummary,
    DocumentUpdate,
    ShareableUser,
)
from app.services.supabase_client import get_supabase_admin

router = APIRouter()

MIGRATION_FILES = {
    "profiles": "backend/database/profiles.sql",
    "documents": "backend/database/documents.sql",
    "document_shares": "backend/database/document_shares.sql",
}


def _missing_table_message(exc: APIError) -> str:
    error_text = exc.message or str(exc)
    for table_name, migration_file in MIGRATION_FILES.items():
        if f"public.{table_name}" in error_text or f"'{table_name}'" in error_text:
            return (
                f"The {table_name} table does not exist yet. "
                f"Run {migration_file} in the Supabase SQL Editor, then retry."
            )

    return (
        f"Required database table not found ({error_text}). "
        "Run backend/database/schema.sql in the Supabase SQL Editor, then retry."
    )


def _handle_supabase_error(exc: Exception) -> None:
    if isinstance(exc, APIError) and exc.code == "PGRST205":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_missing_table_message(exc),
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


def _parse_summary(
    row: dict[str, Any],
    *,
    owner_email: Optional[str] = None,
    shared_at: Optional[Any] = None,
    share_count: int = 0,
) -> DocumentSummary:
    return DocumentSummary(
        id=str(row["id"]),
        title=row["title"],
        owner_id=str(row["owner_id"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        owner_email=owner_email,
        shared_at=shared_at,
        share_count=share_count,
    )


def _get_share_counts(document_ids: list[str]) -> dict[str, int]:
    if not document_ids:
        return {}

    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("document_shares")
            .select("document_id")
            .in_("document_id", document_ids)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    counts: dict[str, int] = {}
    for row in response.data or []:
        doc_id = str(row["document_id"])
        counts[doc_id] = counts.get(doc_id, 0) + 1
    return counts


def _get_document_by_id(document_id: str) -> Optional[dict[str, Any]]:
    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("documents")
            .select("*")
            .eq("id", document_id)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    if not response.data:
        return None
    return response.data[0]


def _user_has_share_access(document_id: str, user_id: str) -> bool:
    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("document_shares")
            .select("id")
            .eq("document_id", document_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    return bool(response.data)


def _get_owned_document(document_id: str, owner_id: str) -> dict[str, Any]:
    row = _get_document_by_id(document_id)
    if not row or str(row["owner_id"]) != owner_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return row


def _get_accessible_document(document_id: str, user_id: str) -> dict[str, Any]:
    row = _get_document_by_id(document_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if str(row["owner_id"]) == user_id:
        return row

    if _user_has_share_access(document_id, user_id):
        return row

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document not found",
    )


def _get_profile_emails(user_ids: list[str]) -> dict[str, str]:
    if not user_ids:
        return {}

    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("profiles")
            .select("id, email")
            .in_("id", user_ids)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    return {str(row["id"]): row["email"] for row in response.data or []}


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    body: DocumentCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> DocumentResponse:
    supabase = get_supabase_admin()
    payload = {
        "title": body.title,
        "content_json": body.content_json or DEFAULT_CONTENT_JSON,
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

    rows = response.data or []
    document_ids = [str(row["id"]) for row in rows]
    share_counts = _get_share_counts(document_ids)

    return [
        _parse_summary(row, share_count=share_counts.get(str(row["id"]), 0))
        for row in rows
    ]


@router.get("/shared", response_model=list[DocumentSummary])
def list_shared_documents(
    current_user: UserResponse = Depends(get_current_user),
) -> list[DocumentSummary]:
    supabase = get_supabase_admin()
    try:
        shares_response = (
            supabase.table("document_shares")
            .select("document_id, created_at")
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    shares = shares_response.data or []
    if not shares:
        return []

    document_ids = [share["document_id"] for share in shares]
    try:
        documents_response = (
            supabase.table("documents")
            .select("id, title, owner_id, created_at, updated_at")
            .in_("id", document_ids)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    documents_by_id = {
        str(row["id"]): row for row in documents_response.data or []
    }
    owner_emails = _get_profile_emails(
        [str(documents_by_id[str(doc_id)]["owner_id"]) for doc_id in document_ids if str(doc_id) in documents_by_id]
    )

    results: list[DocumentSummary] = []
    for share in shares:
        doc_id = str(share["document_id"])
        row = documents_by_id.get(doc_id)
        if not row:
            continue
        owner_id = str(row["owner_id"])
        results.append(
            _parse_summary(
                row,
                owner_email=owner_emails.get(owner_id),
                shared_at=share["created_at"],
            )
        )

    return results


@router.get("/share-users", response_model=list[ShareableUser])
def list_share_users(
    current_user: UserResponse = Depends(get_current_user),
) -> list[ShareableUser]:
    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("profiles")
            .select("id, email")
            .neq("id", current_user.id)
            .order("email")
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    return [
        ShareableUser(id=str(row["id"]), email=row["email"])
        for row in response.data or []
    ]


@router.post("/{document_id}/share", response_model=DocumentShareResponse)
def share_document(
    document_id: str,
    body: DocumentShareCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> DocumentShareResponse:
    _get_owned_document(document_id, current_user.id)

    if body.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share a document with yourself",
        )

    supabase = get_supabase_admin()
    try:
        profile_response = (
            supabase.table("profiles")
            .select("id")
            .eq("id", body.user_id)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    if not profile_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    payload = {
        "document_id": document_id,
        "user_id": body.user_id,
    }

    try:
        response = supabase.table("document_shares").insert(payload).execute()
    except Exception as exc:
        error_text = str(exc).lower()
        if "duplicate" in error_text or "unique" in error_text:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document already shared with this user",
            ) from exc
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
            detail="Failed to share document",
        )

    row = response.data[0]
    return DocumentShareResponse(
        id=str(row["id"]),
        document_id=str(row["document_id"]),
        user_id=str(row["user_id"]),
        created_at=row["created_at"],
    )


@router.get("/{document_id}/shares", response_model=list[DocumentShareDetail])
def list_document_shares(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> list[DocumentShareDetail]:
    _get_owned_document(document_id, current_user.id)

    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("document_shares")
            .select("id, user_id, created_at")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    shares = response.data or []
    user_emails = _get_profile_emails([str(row["user_id"]) for row in shares])

    return [
        DocumentShareDetail(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            user_email=user_emails.get(str(row["user_id"]), "Unknown user"),
            created_at=row["created_at"],
        )
        for row in shares
    ]


@router.delete("/{document_id}/share/{user_id}")
def unshare_document(
    document_id: str,
    user_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> dict[str, str]:
    _get_owned_document(document_id, current_user.id)

    supabase = get_supabase_admin()
    try:
        response = (
            supabase.table("document_shares")
            .delete()
            .eq("document_id", document_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        _handle_supabase_error(exc)

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )

    return {"message": "Share removed"}


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> DocumentResponse:
    row = _get_accessible_document(document_id, current_user.id)
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

    _get_accessible_document(document_id, current_user.id)

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
