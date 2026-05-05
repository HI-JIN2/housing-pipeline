import os
import uuid
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from models import (
    NoticeAttachment,
    NoticeItem,
    NoticePipelineSnapshot,
    NoticePipelineStage,
    NoticeStageRecord,
    PipelineStageStatus,
)


class MongoService:
    def __init__(self):
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client.housing_db
        self.notice_collection = self.db.notice_announcements
        self.pipeline_run_collection = self.db.notice_pipeline_runs

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def has_source_items(self, source: str) -> bool:
        existing = await self.notice_collection.find_one({"source": source}, {"_id": 1})
        return existing is not None

    async def save_notice_if_new(self, notice: NoticeItem) -> bool:
        now = self._now_iso()
        result = await self.notice_collection.update_one(
            {"source": notice.source, "external_id": notice.external_id},
            {
                "$setOnInsert": {
                    **notice.model_dump(),
                    "created_at": now,
                },
                "$set": {
                    "updated_at": now,
                    "title": notice.title,
                    "url": notice.url,
                    "published_at": notice.published_at,
                    "deadline_at": notice.deadline_at,
                    "department": notice.department,
                    "region": notice.region,
                    "status": notice.status,
                    "views": notice.views,
                    "category": notice.category,
                    "raw": notice.raw,
                },
            },
            upsert=True,
        )
        return result.upserted_id is not None

    async def start_pipeline_run(
        self,
        *,
        notice: NoticeItem,
        stages: list[NoticePipelineStage],
    ) -> str:
        run_id = str(uuid.uuid4())
        now = self._now_iso()
        await self.pipeline_run_collection.insert_one(
            {
                "run_id": run_id,
                "source": notice.source,
                "external_id": notice.external_id,
                "title": notice.title,
                "status": "RUNNING",
                "planned_stages": [stage.value for stage in stages],
                "stage_records": [],
                "created_at": now,
                "updated_at": now,
            }
        )
        return run_id

    async def record_notice_stage(
        self,
        *,
        notice: NoticeItem,
        run_id: str,
        record: NoticeStageRecord,
        retry_count: int = 0,
        attachments: list[NoticeAttachment] | None = None,
        last_error: str | None = None,
    ) -> None:
        snapshot = NoticePipelineSnapshot(
            last_run_id=run_id,
            current_stage=record.stage,
            current_status=record.status,
            last_error=last_error,
            retry_count=retry_count,
            attachments=attachments or [],
            stage_records={record.stage: record},
        )

        await self.notice_collection.update_one(
            {"source": notice.source, "external_id": notice.external_id},
            {
                "$setOnInsert": {
                    **notice.model_dump(),
                    "created_at": record.updated_at,
                },
                "$set": {
                    "updated_at": record.updated_at,
                    "title": notice.title,
                    "url": notice.url,
                    "published_at": notice.published_at,
                    "deadline_at": notice.deadline_at,
                    "department": notice.department,
                    "region": notice.region,
                    "status": notice.status,
                    "views": notice.views,
                    "category": notice.category,
                    "raw": notice.raw,
                    "pipeline.last_run_id": snapshot.last_run_id,
                    "pipeline.current_stage": snapshot.current_stage.value if snapshot.current_stage else None,
                    "pipeline.current_status": snapshot.current_status.value if snapshot.current_status else None,
                    "pipeline.last_error": snapshot.last_error,
                    "pipeline.retry_count": snapshot.retry_count,
                    "pipeline.attachments": [item.model_dump(mode="json") for item in snapshot.attachments],
                    f"pipeline.stage_records.{record.stage.value}": record.model_dump(mode="json"),
                },
            },
            upsert=True,
        )

        await self.pipeline_run_collection.update_one(
            {"run_id": run_id},
            {
                "$pull": {"stage_records": {"stage": record.stage.value}},
            },
        )
        await self.pipeline_run_collection.update_one(
            {"run_id": run_id},
            {
                "$push": {"stage_records": record.model_dump(mode="json")},
                "$set": {"updated_at": record.updated_at},
            },
        )

    async def finish_pipeline_run(
        self,
        *,
        run_id: str,
        status: PipelineStageStatus,
        error: str | None = None,
    ) -> None:
        now = self._now_iso()
        update_fields: dict[str, Any] = {
            "status": status.value,
            "updated_at": now,
            "finished_at": now,
        }
        if error:
            update_fields["error"] = error

        await self.pipeline_run_collection.update_one(
            {"run_id": run_id},
            {"$set": update_fields},
        )

    async def list_recent_pipeline_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        cursor = (
            self.pipeline_run_collection
            .find({})
            .sort("created_at", -1)
            .limit(limit)
        )

        documents: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
        return documents

    async def list_recent_notices(self, limit: int = 50, source: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if source:
            query["source"] = source

        cursor = (
            self.notice_collection
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

        documents: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
        return documents
