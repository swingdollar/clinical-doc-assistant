"""
Web Scraper Module using Playwright
Renders JavaScript-heavy pages and extracts structured data.
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, Playwright


@dataclass
class ScrapeResult:
    url: str
    success: bool
    data: Optional[List[str]] = None
    html: Optional[str] = None
    error: Optional[str] = None


class WebScraper:
    def __init__(
        self,
        timeout: int = 30000,
        headless: bool = True,
        user_agent: Optional[str] = None
    ):
        self.timeout = timeout
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self._browser: Optional[Browser] = None
        self._playwright: Optional[Playwright] = None

    async def _get_browser(self) -> Browser:
        if not self._browser:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
        return self._browser

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def scrape(
        self,
        url: str,
        selectors: Optional[Dict[str, str]] = None,
        wait_for: Optional[str] = None
    ) -> ScrapeResult:
        try:
            browser = await self._get_browser()
            page = await browser.new_page()

            if self.user_agent:
                await page.set_extra_http_headers({"User-Agent": self.user_agent})

            await page.goto(url, wait_until="networkidle", timeout=self.timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=self.timeout)

            html = await page.content()
            await page.close()

            soup = BeautifulSoup(html, 'html.parser')

            data = {}
            if selectors:
                for name, selector in selectors.items():
                    elements = soup.select(selector)
                    data[name] = [el.text.strip() for el in elements]

            return ScrapeResult(
                url=url,
                success=True,
                data=data.get("results") if "results" in data else list(data.values())[0] if data else [],
                html=html
            )

        except Exception as e:
            return ScrapeResult(url=url, success=False, error=str(e))

    async def scrape_jobs(self, url: str, job_selector: str = ".job-title") -> ScrapeResult:
        return await self.scrape(url, selectors={"results": job_selector})


async def scrape_target(url: str, selectors: Optional[Dict[str, str]] = None) -> ScrapeResult:
    scraper = WebScraper()
    try:
        return await scraper.scrape(url, selectors)
    finally:
        await scraper.close()


if __name__ == "__main__":
    async def main():
        result = await scrape_target("https://example.com", {"titles": "h1, h2"})
        print(f"Success: {result.success}")
        if result.data:
            print(f"Data: {result.data[:5]}")

    asyncio.run(main())