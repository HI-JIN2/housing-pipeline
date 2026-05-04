from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from shared.pipeline import AsyncFinishJob, AsyncJob, AsyncPipeline


@dataclass
class AnnouncementDetailStore:
    announcement_id: str
    mongo_service: Any
    db_service: Any
    announcement: Optional[dict[str, Any]] = None
    parsed_houses: list[dict[str, Any]] = field(default_factory=list)
    enriched_rows: list[dict[str, Any]] = field(default_factory=list)
    merged_houses: list[dict[str, Any]] = field(default_factory=list)


class InitAnnouncementDetailJob(AsyncJob[AnnouncementDetailStore]):
    async def process(self, store: AnnouncementDetailStore) -> None:
        store.announcement = await store.mongo_service.get_announcement(store.announcement_id)


class ExtractParsedHousesJob(AsyncJob[AnnouncementDetailStore]):
    async def process(self, store: AnnouncementDetailStore) -> None:
        if not store.announcement:
            return
        store.parsed_houses = list(store.announcement.get("parsed_houses", []))


class LoadEnrichedHousesJob(AsyncJob[AnnouncementDetailStore]):
    async def process(self, store: AnnouncementDetailStore) -> None:
        if not store.parsed_houses:
            return

        house_ids = [house.get("id") for house in store.parsed_houses if house.get("id")]
        if not house_ids:
            return

        store.enriched_rows = await store.db_service.get_enriched_data_by_ids(house_ids)


class MergeAnnouncementDetailJob(AsyncJob[AnnouncementDetailStore]):
    async def process(self, store: AnnouncementDetailStore) -> None:
        if not store.parsed_houses:
            store.merged_houses = []
            return

        enriched_map = {item["id"]: item for item in store.enriched_rows if item.get("id")}
        store.merged_houses = [
            {**house, **enriched_map[house["id"]]} if house.get("id") in enriched_map else house
            for house in store.parsed_houses
        ]


class FinishAnnouncementDetailJob(AsyncFinishJob[AnnouncementDetailStore, Optional[list[dict[str, Any]]]]):
    async def process(self, store: AnnouncementDetailStore) -> Optional[list[dict[str, Any]]]:
        if not store.announcement:
            return None
        return store.merged_houses


async def execute_announcement_detail_pipeline(
    announcement_id: str,
    mongo_service: Any,
    db_service: Any,
) -> Optional[list[dict[str, Any]]]:
    pipeline = AsyncPipeline(
        store=AnnouncementDetailStore(
            announcement_id=announcement_id,
            mongo_service=mongo_service,
            db_service=db_service,
        ),
        init_job=InitAnnouncementDetailJob(),
        jobs=[
            ExtractParsedHousesJob(),
            LoadEnrichedHousesJob(),
            MergeAnnouncementDetailJob(),
        ],
        finish_job=FinishAnnouncementDetailJob(),
    )
    return await pipeline.execute()
