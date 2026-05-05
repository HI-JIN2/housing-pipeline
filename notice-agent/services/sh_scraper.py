from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from models import NoticeItem


DEFAULT_SH_NOTICE_URL = "https://www.i-sh.co.kr/app/lay2/program/S48T561C563/www/brd/m_247/list.do?multi_itm_seq=2"


class ShScraper:
    def __init__(self, source_url: str = DEFAULT_SH_NOTICE_URL):
        self.source_url = source_url

    async def fetch_items(self) -> list[NoticeItem]:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "housing-pipeline-notice-agent/1.0"},
        ) as client:
            response = await client.get(self.source_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        notices: list[NoticeItem] = []

        for row in soup.select("tr"):
            cells = row.select("td")
            if len(cells) < 4:
                continue

            row_number = cells[0].get_text(" ", strip=True)
            if not row_number.isdigit():
                continue

            title_anchor = row.find("a", href=True)
            title = title_anchor.get_text(" ", strip=True) if title_anchor else cells[1].get_text(" ", strip=True)
            url = urljoin(self.source_url, title_anchor["href"]) if title_anchor and title_anchor.get("href") else self.source_url

            notices.append(
                NoticeItem(
                    source="SH",
                    external_id=row_number,
                    title=title,
                    url=url,
                    department=cells[-3].get_text(" ", strip=True),
                    published_at=cells[-2].get_text(" ", strip=True),
                    views=cells[-1].get_text(" ", strip=True),
                    category="주택임대",
                    raw={"row_number": row_number},
                )
            )

        return notices
