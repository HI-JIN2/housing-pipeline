from enum import Enum
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


class NoticePipelineStage(str, Enum):
    DISCOVERED = "DISCOVERED"
    DETAIL_FETCHED = "DETAIL_FETCHED"
    ATTACHMENTS_DOWNLOADED = "ATTACHMENTS_DOWNLOADED"
    PARSED = "PARSED"
    ENRICHED = "ENRICHED"
    PUBLISHED = "PUBLISHED"
    NOTIFIED = "NOTIFIED"


class PipelineStageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NoticeStageRecord(BaseModel):
    stage: NoticePipelineStage
    status: PipelineStageStatus
    updated_at: str
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NoticeAttachment(BaseModel):
    name: str
    url: str
    content_type: str | None = None
    local_path: str | None = None
    downloaded_at: str | None = None


class NoticePipelineSnapshot(BaseModel):
    last_run_id: str | None = None
    current_stage: NoticePipelineStage | None = None
    current_status: PipelineStageStatus | None = None
    last_error: str | None = None
    retry_count: int = 0
    attachments: list[NoticeAttachment] = Field(default_factory=list)
    stage_records: dict[NoticePipelineStage, NoticeStageRecord] = Field(default_factory=dict)
