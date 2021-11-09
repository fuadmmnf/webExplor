from typing import Optional
import pyppeteer.page
from pyppeteer import launch
from preprocessing import Preprocessing
from models.webstate import Webstate
from pyppeteer.element_handle import ElementHandle


class Crawler:
    def __init__(self, home_url: str):
        self.home_url: str = home_url
        self.browser: Optional[pyppeteer.page.Browser] = None

    async def init_browser(self) -> None:
        if self.browser is None:
            self.browser = await launch(headless=False, devtools=True)

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

        await self._process_action(page, webstate.valid_actions[0])
        await page.waitFor(4000)

    async def _process_action(self, page: pyppeteer.page.Page, valid_action: ElementHandle):
        tag_name = await (await valid_action.getProperty('tagName')).jsonValue()
        if tag_name == 'A':
            link = await (await valid_action.getProperty('href')).jsonValue()
            await page.goto(link.__str__())
        elif tag_name == 'INPUT':
            pass
        elif tag_name == 'BUTTON':
            await valid_action.click()
        else:
            pass

        # button = await (await valid_aciton.getProperty('href')).jsonValue()
