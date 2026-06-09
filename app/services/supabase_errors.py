from typing import Callable, TypeVar

import httpx
from fastapi import HTTPException, status
from postgrest.exceptions import APIError

from app.services.supabase_retry import execute_supabase, is_transient_supabase_error

T = TypeVar("T")

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


def handle_supabase_error(exc: Exception) -> None:
    if isinstance(exc, APIError) and exc.code == "PGRST205":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_missing_table_message(exc),
        ) from exc

    if is_transient_supabase_error(exc) or isinstance(exc, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please retry.",
        ) from exc

    raise exc


def supabase_execute(fn: Callable[[], T]) -> T:
    try:
        return execute_supabase(fn)
    except HTTPException:
        raise
    except Exception as exc:
        handle_supabase_error(exc)