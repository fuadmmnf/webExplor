from typing import Optional
from random import randint
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

        for valid_action in webstate.valid_actions:
            await _process_action(page, valid_action)
        await page.waitFor(4000)


async def _process_action(page: pyppeteer.page.Page, valid_action: ElementHandle):
    tag_name = await (await valid_action.getProperty('tagName')).jsonValue()
    if tag_name == 'A':
        link = await (await valid_action.getProperty('href')).jsonValue()
        await page.goto(link.__str__())

    elif tag_name == 'BUTTON':
        await valid_action.click()
    elif tag_name == 'SELECT':
        options = await valid_action.querySelectorAll('option')
        if len(options) > 0:
            await valid_action.querySelectorEval('option:nth-child(' + str(randint(1, len(options))) + ')',
                                                 '(node => node.selected = true)')
    elif tag_name == 'INPUT':
        input_type = await (await valid_action.getProperty('type')).jsonValue()
        if input_type == 'button':
            await valid_action.click()
        elif input_type == 'checkbox':
            pass
        elif input_type == 'color':
            pass
        elif input_type == 'date':
            pass
        elif input_type == 'datetime-local':
            pass
        elif input_type == 'email':
            pass
        elif input_type == 'file':
            pass
        elif input_type == 'hidden':
            pass
        elif input_type == 'image':
            pass
        elif input_type == 'month':
            pass
        elif input_type == 'number':
            pass
        elif input_type == 'password':
            pass
        elif input_type == 'radio':
            pass
        elif input_type == 'range':
            pass
        elif input_type == 'reset':
            pass
        elif input_type == 'search':
            pass
        elif input_type == 'submit':
            pass
        elif input_type == 'tel':
            pass
        elif input_type == 'text':
            pass
        elif input_type == 'time':
            pass
        elif input_type == 'url':
            pass
        elif input_type == 'week':
            pass