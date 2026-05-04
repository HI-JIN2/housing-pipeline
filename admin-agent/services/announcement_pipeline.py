from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote
import uuid

import httpx

from shared.pipeline import AsyncFinishJob, AsyncJob, AsyncPipeline


@dataclass
class SaveAnnouncementStore:
    payload: dict[str, Any]
    mongo_service: Any
    geo_agent_url: str
    announcement_title: str = ""
    houses: list[dict[str, Any]] = field(default_factory=list)
    announcement_document: dict[str, Any] = field(default_factory=dict)
    geo_cleanup_url: str = ""
    saved_count: int = 0


class InitSaveAnnouncementJob(AsyncJob[SaveAnnouncementStore]):
    async def process(self, store: SaveAnnouncementStore) -> None:
        store.announcement_title = store.payload.get("announcement_title", "Untitled")
        store.houses = list(store.payload.get("houses", []))
        store.geo_cleanup_url = f"{store.geo_agent_url.rsplit('/', 1)[0]}/housing/{quote(store.announcement_title)}"


class ValidateAnnouncementPayloadJob(AsyncJob[SaveAnnouncementStore]):
    async def process(self, store: SaveAnnouncementStore) -> None:
        if not store.houses:
            raise ValueError("No houses to save")


class BuildAnnouncementDocumentJob(AsyncJob[SaveAnnouncementStore]):
    async def process(self, store: SaveAnnouncementStore) -> None:
        store.announcement_document = {
            "announcement_title": store.announcement_title,
            "announcement_description": store.payload.get("announcement_description"),
            "parsed_houses": store.houses,
            "created_at": store.payload.get("created_at") or str(uuid.uuid1()),
        }


class PersistAnnouncementJob(AsyncJob[SaveAnnouncementStore]):
    async def process(self, store: SaveAnnouncementStore) -> None:
        await store.mongo_service.save_announcement(store.announcement_document)


class CleanupExistingGeoDataJob(AsyncJob[SaveAnnouncementStore]):
    async def process(self, store: SaveAnnouncementStore) -> None:
        async with httpx.AsyncClient() as client:
            try:
                await client.delete(store.geo_cleanup_url, timeout=10.0)
            except Exception as exc:
                logging.error(f"Postgres cleanup failed: {exc}")


class DispatchGeoEnrichmentJob(AsyncJob[SaveAnnouncementStore]):
    async def process(self, store: SaveAnnouncementStore) -> None:
        async with httpx.AsyncClient() as client:
            tasks = []
            for house in store.houses:
                tasks.append(
                    client.post(
                        store.geo_agent_url,
                        json={**house, "announcement_id": store.announcement_title},
                        timeout=60.0,
                    )
                )

            await asyncio.gather(*tasks, return_exceptions=True)
            store.saved_count = len(store.houses)


class FinishSaveAnnouncementJob(AsyncFinishJob[SaveAnnouncementStore, dict[str, Any]]):
    async def process(self, store: SaveAnnouncementStore) -> dict[str, Any]:
        return {
            "status": "success",
            "message": f"Saved {store.saved_count} records",
        }


async def execute_save_announcement_pipeline(
    payload: dict[str, Any],
    mongo_service: Any,
    geo_agent_url: str,
) -> dict[str, Any]:
    pipeline = AsyncPipeline(
        store=SaveAnnouncementStore(payload=payload, mongo_service=mongo_service, geo_agent_url=geo_agent_url),
        init_job=InitSaveAnnouncementJob(),
        jobs=[
            ValidateAnnouncementPayloadJob(),
            BuildAnnouncementDocumentJob(),
            PersistAnnouncementJob(),
            CleanupExistingGeoDataJob(),
            DispatchGeoEnrichmentJob(),
        ],
        finish_job=FinishSaveAnnouncementJob(),
    )
    return await pipeline.execute()
