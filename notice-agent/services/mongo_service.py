import os
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from models import NoticeItem


class MongoService:
    def __init__(self):
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client.housing_db
        self.notice_collection = self.db.notice_announcements

    async def has_source_items(self, source: str) -> bool:
        existing = await self.notice_collection.find_one({"source": source}, {"_id": 1})
        return existing is not None

    async def save_notice_if_new(self, notice: NoticeItem) -> bool:
        now = datetime.now(timezone.utc).isoformat()
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
