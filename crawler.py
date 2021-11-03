from typing import Optional
import pyppeteer.page
from pyppeteer import launch
from preprocessing import Preprocessing
from models.webstate import Webstate


class Crawler:
    def __init__(self, home_url: str):
        self.home_url: str = home_url
        self.browser: Optional[pyppeteer.page.Browser] = None

    async def init_browser(self) -> None:
        if self.browser is None:
            self.browser = await launch(headless=False)

    async def crawl(self) -> None:
        await self.init_browser()

        # generate webstate for each page
        await self._get_page_webstate(self.home_url)  # testing

        await self.browser.close()

    async def _get_page_webstate(self, url: str):
        page: pyppeteer.page.Page = await self.browser.newPage()
        await page.goto(url, {'waitUntil': 'networkidle0'})
        # await page.waitFor(5500)
        dom_content: str = await page.content()
        preprocessing: Preprocessing = Preprocessing(page)
        webstate: Webstate = await preprocessing.extract_webstate(self.home_url, dom_content)
        print(len(webstate.valid_actions))