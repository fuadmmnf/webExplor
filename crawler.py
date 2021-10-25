from typing import Optional
import pyppeteer.page
from pyppeteer import launch


class Crawler:
    def __init__(self, home_url: str):
        self.home_url: str = home_url
        self.browser: Optional[pyppeteer.page.Browser] = None

    async def init_browser(self) -> None:
        self.browser = None if self.browser is not None else await launch()

    async def crawl(self) -> None:
        await self.init_browser()
        await self.get_page(self.home_url)  # testing
        await self.browser.close()

    async def get_page(self, url: str) -> None:
        page = await self.browser.newPage()
        await page.goto(url)
        await page.screenshot({'path': 'example.png'})


