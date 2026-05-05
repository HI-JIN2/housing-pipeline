from typing import Any

from pydantic import BaseModel, Field


class NoticeItem(BaseModel):
    source: str
    external_id: str
    title: str
    url: str
    published_at: str | None = None
    deadline_at: str | None = None
    department: str | None = None
    region: str | None = None
    status: str | None = None
    views: str | None = None
    category: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
