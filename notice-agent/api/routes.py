import os

from fastapi import APIRouter, Header, HTTPException, Query

from services.monitor_service import NoticeMonitorService
from services.mongo_service import MongoService
from services.slack_service import SlackService

router = APIRouter()

mongo_service = MongoService()
slack_service = SlackService()
monitor_service = NoticeMonitorService(mongo_service, slack_service)
notice_agent_token = os.getenv("NOTICE_AGENT_TOKEN", "").strip()


def verify_notice_token(x_notice_token: str | None):
    if notice_agent_token and x_notice_token != notice_agent_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/notices/run-once")
async def run_notices_once(x_notice_token: str | None = Header(default=None)):
    verify_notice_token(x_notice_token)
    return await monitor_service.crawl_once()


@router.get("/notices/recent")
async def list_recent_notices(
    limit: int = Query(default=20, ge=1, le=100),
    source: str | None = Query(default=None, pattern="^(SH|LH)$"),
    x_notice_token: str | None = Header(default=None),
):
    verify_notice_token(x_notice_token)
    return await mongo_service.list_recent_notices(limit=limit, source=source)
