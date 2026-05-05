import asyncio
import logging
import os
from typing import Any

from services.lh_scraper import DEFAULT_LH_NOTICE_URL, LhScraper
from services.mongo_service import MongoService
from services.pipeline_service import NoticePipelineService
from services.sh_scraper import DEFAULT_SH_NOTICE_URL, ShScraper
from services.slack_service import SlackService


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class NoticeMonitorService:
    def __init__(self, mongo_service: MongoService, slack_service: SlackService):
        self.mongo_service = mongo_service
        self.slack_service = slack_service
        self.pipeline_service = NoticePipelineService(mongo_service, slack_service)
        self.enabled = _env_flag("NOTICE_CRAWLER_ENABLED", default=False)
        self.notify_on_bootstrap = _env_flag("NOTICE_NOTIFY_ON_BOOTSTRAP", default=False)
        self.interval_seconds = int(os.getenv("NOTICE_CRAWL_INTERVAL_SECONDS", "3600"))
        self.item_concurrency = max(1, int(os.getenv("NOTICE_ITEM_CONCURRENCY", "5")))
        self.stop_event = asyncio.Event()
        self.scrapers = {
            "SH": ShScraper(os.getenv("SH_NOTICE_URL", DEFAULT_SH_NOTICE_URL)),
            "LH": LhScraper(os.getenv("LH_NOTICE_URL", DEFAULT_LH_NOTICE_URL)),
        }

    async def crawl_once(self) -> dict[str, Any]:
        summary: dict[str, Any] = {"sources": {}, "totals": {"fetched": 0, "new": 0, "notified": 0}}

        source_results = await asyncio.gather(
            *(self._crawl_source(source, scraper) for source, scraper in self.scrapers.items()),
            return_exceptions=True,
        )

        for result in source_results:
            if isinstance(result, Exception):
                logging.exception("Notice source crawl failed: %s", result)
                continue

            source, source_summary = result
            summary["sources"][source] = source_summary
            summary["totals"]["fetched"] += source_summary["fetched"]
            summary["totals"]["new"] += source_summary["new"]
            summary["totals"]["notified"] += source_summary["notified"]

        return summary

    async def _crawl_source(self, source: str, scraper: Any) -> tuple[str, dict[str, Any]]:
        items = await scraper.fetch_items()
        had_existing = await self.mongo_service.has_source_items(source)
        source_summary: dict[str, Any] = {
            "fetched": len(items),
            "new": 0,
            "notified": 0,
            "bootstrap_seeded": not had_existing,
            "pipeline_runs": [],
        }

        semaphore = asyncio.Semaphore(self.item_concurrency)
        results = await asyncio.gather(
            *(self._process_item(item, had_existing, semaphore) for item in items),
            return_exceptions=True,
        )

        for item, result in zip(items, results):
            if isinstance(result, Exception):
                logging.exception(
                    "Notice item task failed: source=%s external_id=%s title=%s",
                    source,
                    getattr(item, "external_id", "unknown"),
                    getattr(item, "title", "unknown"),
                )
                continue

            source_summary["new"] += result["new"]
            source_summary["notified"] += result["notified"]
            if result["pipeline_run"] is not None:
                source_summary["pipeline_runs"].append(result["pipeline_run"])

        return source, source_summary

    async def _process_item(
        self,
        item: Any,
        had_existing: bool,
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        async with semaphore:
            created = await self.mongo_service.save_notice_if_new(item)
            if not created:
                return {"new": 0, "notified": 0, "pipeline_run": None}

            should_notify = had_existing or self.notify_on_bootstrap
            pipeline_result = await self.pipeline_service.process_discovered_notice(
                notice=item,
                should_notify=should_notify,
            )
            return {
                "new": 1,
                "notified": int(pipeline_result.notified),
                "pipeline_run": {
                    "run_id": pipeline_result.run_id,
                    "notice_key": pipeline_result.notice_key,
                    "current_stage": (
                        pipeline_result.current_stage.value if pipeline_result.current_stage else None
                    ),
                    "current_status": (
                        pipeline_result.current_status.value if pipeline_result.current_status else None
                    ),
                },
            }

    async def run_forever(self):
        if not self.enabled:
            logging.info("Notice crawler is disabled. Scheduler will not start.")
            return

        logging.info("Notice crawler started. interval_seconds=%s", self.interval_seconds)
        while not self.stop_event.is_set():
            try:
                result = await self.crawl_once()
                logging.info("Notice crawl completed: %s", result)
            except Exception as exc:
                logging.exception("Notice crawl failed: %s", exc)

            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def stop(self):
        self.stop_event.set()
