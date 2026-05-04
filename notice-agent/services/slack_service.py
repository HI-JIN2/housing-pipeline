import logging
import os

import httpx

from models import NoticeItem


class SlackService:
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()

    async def send_new_notice(self, notice: NoticeItem) -> bool:
        if not self.webhook_url:
            logging.warning("SLACK_WEBHOOK_URL is not configured. Slack notification skipped.")
            return False

        lines = [
            f"[{notice.source}] 새 공고가 등록되었습니다.",
            f"제목: {notice.title}",
            f"공고 링크: {notice.url}",
        ]
        if notice.published_at:
            lines.append(f"게시일: {notice.published_at}")
        if notice.deadline_at:
            lines.append(f"마감일: {notice.deadline_at}")
        if notice.region:
            lines.append(f"지역: {notice.region}")
        if notice.department:
            lines.append(f"부서: {notice.department}")
        if notice.status:
            lines.append(f"상태: {notice.status}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.webhook_url, json={"text": "\n".join(lines)})
            response.raise_for_status()
        return True
