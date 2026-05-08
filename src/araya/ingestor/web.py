import re
import logging
from typing import Optional, Dict, Any

import httpx

from araya.ingestor.models import ResearchObject, SourceType

logger = logging.getLogger(__name__)


class WebIngestor:
    def __init__(self):
        self._playwright_available = False
        try:
            import playwright
            self._playwright_available = True
        except ImportError:
            logger.info("Playwright not installed. Web ingestion will use HTTP fallback.")

    async def ingest(self, url: str, metadata: Optional[dict] = None) -> ResearchObject:
        content = None

        if self._playwright_available:
            try:
                content = await self._fetch_with_playwright(url)
            except Exception as e:
                logger.warning(f"Playwright fetch failed for {url}: {e}. Falling back to HTTP.")

        if content is None:
            content = await self._fetch_simple(url)

        obj_metadata = {
            "source_url": url,
        }
        if metadata:
            obj_metadata.update(metadata)

        return ResearchObject(
            id=f"web_{hash(url)}",
            source_type=SourceType.WEB,
            content=content or "",
            metadata=obj_metadata,
            elements=[]
        )

    async def _fetch_with_playwright(self, url: str) -> str:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            html_content = await page.content()
            await browser.close()

        try:
            from markdownify import markdownify
            return markdownify(html_content)
        except ImportError:
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

    async def _fetch_simple(self, url: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()

            text = re.sub(r'<[^>]+>', ' ', response.text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
