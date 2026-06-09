from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

DEFAULT_CONTENT_JSON: dict[str, Any] = {
    "type": "doc",
    "content": [{"type": "paragraph"}],
}


class DocumentCreate(BaseModel):
    title: str = Field(default="Untitled", min_length=1, max_length=500)
    content_json: Optional[dict[str, Any]] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    content_json: Optional[dict[str, Any]] = None


class DocumentSummary(BaseModel):
    id: str
    title: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    owner_email: Optional[str] = None
    shared_at: Optional[datetime] = None
    share_count: int = 0


class DocumentShareCreate(BaseModel):
    user_id: str


class DocumentShareResponse(BaseModel):
    id: str
    document_id: str
    user_id: str
    created_at: datetime


class DocumentShareDetail(BaseModel):
    id: str
    user_id: str
    user_email: str
    created_at: datetime


class ShareableUser(BaseModel):
    id: str
    email: str


class DocumentResponse(DocumentSummary):
    content_json: dict[str, Any]
