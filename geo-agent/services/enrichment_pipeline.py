from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from shared.models import EnrichedHousingData, ParsedHousingData
from shared.pipeline import AsyncFinishJob, AsyncJob, AsyncPipeline


@dataclass
class EnrichmentStore:
    raw_data: dict[str, Any]
    db_service: Any
    kakao_client: Any
    parsed_data: Optional[ParsedHousingData] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    station_name: str = ""
    distance_meters: int = 0
    walking_time_mins: int = 0
    cached_location: Optional[dict[str, Any]] = None
    enriched_data: Optional[EnrichedHousingData] = None


class InitEnrichmentJob(AsyncJob[EnrichmentStore]):
    async def process(self, store: EnrichmentStore) -> None:
        if not store.db_service.pool:
            await store.db_service.init_pool()


class ValidateParsedHousingJob(AsyncJob[EnrichmentStore]):
    async def process(self, store: EnrichmentStore) -> None:
        store.parsed_data = ParsedHousingData(**store.raw_data)


class ResolveLocationJob(AsyncJob[EnrichmentStore]):
    async def process(self, store: EnrichmentStore) -> None:
        if not store.parsed_data:
            return

        store.cached_location = await store.db_service.get_cached_location(store.parsed_data.address)
        if store.cached_location:
            store.lat = store.cached_location["lat"]
            store.lng = store.cached_location["lng"]
            store.station_name = store.cached_location["nearest_station"]
            store.distance_meters = store.cached_location["distance_meters"]
            store.walking_time_mins = store.cached_location["walking_time_mins"]
            print(f"Cache Hit: Used cached location for {store.parsed_data.address}")
            return

        print(f"Cache Miss: Calling Kakao API for {store.parsed_data.address}")
        lat, lng = await store.kakao_client.get_coordinates(store.parsed_data.address)
        if lat is None or lng is None:
            raise ValueError(
                f"FAILED TO GEOCODE: '{store.parsed_data.address}' for house '{store.parsed_data.id}'"
            )

        station_name, distance_meters = await store.db_service.find_nearest_station(lat, lng)
        store.lat = lat
        store.lng = lng
        store.station_name = station_name or "알수없음"
        store.distance_meters = distance_meters or 0
        store.walking_time_mins = int((store.distance_meters * 1.3) / 72) if store.distance_meters else 0


class CacheLocationJob(AsyncJob[EnrichmentStore]):
    async def process(self, store: EnrichmentStore) -> None:
        if store.cached_location or store.parsed_data is None or store.lat is None or store.lng is None:
            return

        await store.db_service.save_cached_location(
            {
                "address": store.parsed_data.address,
                "name": store.parsed_data.id,
                "lat": store.lat,
                "lng": store.lng,
                "nearest_station": store.station_name,
                "distance_meters": store.distance_meters,
                "walking_time_mins": store.walking_time_mins,
            }
        )


class BuildEnrichedHousingJob(AsyncJob[EnrichmentStore]):
    async def process(self, store: EnrichmentStore) -> None:
        if store.lat is None or store.lng is None:
            return

        store.enriched_data = EnrichedHousingData(
            **store.raw_data,
            lat=store.lat,
            lng=store.lng,
            nearest_station=store.station_name,
            distance_meters=store.distance_meters,
            walking_time_mins=store.walking_time_mins,
        )


class SaveEnrichedHousingJob(AsyncJob[EnrichmentStore]):
    async def process(self, store: EnrichmentStore) -> None:
        if store.enriched_data is None:
            return

        enriched_dict = store.enriched_data.model_dump()
        enriched_dict["announcement_id"] = store.raw_data.get("announcement_id")
        await store.db_service.save_enriched_data(enriched_dict)


class FinishEnrichmentJob(AsyncFinishJob[EnrichmentStore, Optional[dict[str, Any]]]):
    async def process(self, store: EnrichmentStore) -> Optional[dict[str, Any]]:
        if store.enriched_data is None:
            return None

        print(
            f"Processed and saved: {store.enriched_data.id} -> "
            f"{store.station_name} ({store.distance_meters}m)"
        )
        return store.enriched_data.model_dump()


async def execute_enrichment_pipeline(
    raw_data: dict[str, Any],
    db_service: Any,
    kakao_client: Any,
) -> Optional[dict[str, Any]]:
    pipeline = AsyncPipeline(
        store=EnrichmentStore(raw_data=raw_data, db_service=db_service, kakao_client=kakao_client),
        init_job=InitEnrichmentJob(),
        jobs=[
            ValidateParsedHousingJob(),
            ResolveLocationJob(),
            CacheLocationJob(),
            BuildEnrichedHousingJob(),
            SaveEnrichedHousingJob(),
        ],
        finish_job=FinishEnrichmentJob(),
    )
    return await pipeline.execute()
