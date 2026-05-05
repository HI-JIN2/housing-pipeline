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
        self.stop_event = asyncio.Event()
        self.scrapers = {
            "SH": ShScraper(os.getenv("SH_NOTICE_URL", DEFAULT_SH_NOTICE_URL)),
            "LH": LhScraper(os.getenv("LH_NOTICE_URL", DEFAULT_LH_NOTICE_URL)),
        }

    async def crawl_once(self) -> dict[str, Any]:
        summary: dict[str, Any] = {"sources": {}, "totals": {"fetched": 0, "new": 0, "notified": 0}}

        for source, scraper in self.scrapers.items():
            items = await scraper.fetch_items()
            had_existing = await self.mongo_service.has_source_items(source)
            source_summary = {
                "fetched": len(items),
                "new": 0,
                "notified": 0,
                "bootstrap_seeded": not had_existing,
            }

            for item in items:
                created = await self.mongo_service.save_notice_if_new(item)
                if not created:
                    continue

                source_summary["new"] += 1
                if had_existing or self.notify_on_bootstrap:
                    notified = await self.slack_service.send_new_notice(item)
                    if notified:
                        source_summary["notified"] += 1

            summary["sources"][source] = source_summary
            summary["totals"]["fetched"] += source_summary["fetched"]
            summary["totals"]["new"] += source_summary["new"]
            summary["totals"]["notified"] += source_summary["notified"]

        return summary

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
