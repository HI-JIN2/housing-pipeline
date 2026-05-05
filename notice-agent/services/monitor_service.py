import asyncio
import logging
import os
from typing import Any

from services.lh_scraper import DEFAULT_LH_NOTICE_URL, LhScraper
from services.mongo_service import MongoService
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
            *(self._crawl_source(source, scraper) for source, scraper in self.scrapers.items())
        )

        for source, source_summary in source_results:
            summary["sources"][source] = source_summary
            summary["totals"]["fetched"] += source_summary["fetched"]
            summary["totals"]["new"] += source_summary["new"]
            summary["totals"]["notified"] += source_summary["notified"]

        return summary

    async def _crawl_source(self, source: str, scraper: Any) -> tuple[str, dict[str, Any]]:
        items = await scraper.fetch_items()
        had_existing = await self.mongo_service.has_source_items(source)
        source_summary = {
            "fetched": len(items),
            "new": 0,
            "notified": 0,
            "bootstrap_seeded": not had_existing,
        }

        semaphore = asyncio.Semaphore(self.item_concurrency)
        results = await asyncio.gather(
            *(self._process_item(item, had_existing, semaphore) for item in items)
        )

        source_summary["new"] = sum(new_count for new_count, _ in results)
        source_summary["notified"] = sum(notified_count for _, notified_count in results)

        return source, source_summary

    async def _process_item(
        self, item: Any, had_existing: bool, semaphore: asyncio.Semaphore
    ) -> tuple[int, int]:
        async with semaphore:
            created = await self.mongo_service.save_notice_if_new(item)
            if not created:
                return 0, 0

            if had_existing or self.notify_on_bootstrap:
                notified = await self.slack_service.send_new_notice(item)
                return 1, int(notified)

            return 1, 0

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
