from typing import Optional
import pyppeteer.page
from pyppeteer import launch
from preprocessing import Preprocessing


class Crawler:
    def __init__(self, home_url: str):
        self.home_url: str = home_url
        self.browser: Optional[pyppeteer.page.Browser] = None

    async def init_browser(self) -> None:
        if self.browser is None:
            self.browser = await launch()

    async def crawl(self) -> None:
        await self.init_browser()

        # generate webstate for each page
        dom_content: str = await self.get_page(self.home_url)  # testing
        preprocessing: Preprocessing = Preprocessing()
        preprocessing.extract_webstate(self.home_url, dom_content)

        await self.browser.close()

    async def get_page(self, url: str) -> str:
        page: pyppeteer.page.Page = await self.browser.newPage()
        await page.goto(url)
        return await page.content()
