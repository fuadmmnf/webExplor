import random
import os
from typing import Optional
from faker import Faker
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
            # self.browser = await launch(headless=False, devtools=True)
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
            await valid_action.querySelectorEval('option:nth-child(' + str(random.randint(1, len(options))) + ')',
                                                 '(node => node.selected = true)')
    elif tag_name == 'INPUT':
        faker: Faker = Faker()
        input_type = await (await valid_action.getProperty('type')).jsonValue()
        if input_type == 'button':
            await valid_action.click()
        elif input_type == 'checkbox':
            await valid_action.click()
        elif input_type == 'color':
            r = lambda: random.randint(0, 255)
            await valid_action.type('#%02X%02X%02X' % (r(), r(), r()))
        elif input_type == 'date':
            await valid_action.type(faker.date(pattern='%m-%d-%Y'))
        elif input_type == 'datetime-local':
            await valid_action.type(faker.date_time().strftime('%Y-%m-%dT%H:%M%p'))
        elif input_type == 'email':
            await valid_action.type(faker.email())
        elif input_type == 'file':
            file_path = random.choice(os.listdir(os.path.join(os.path.dirname(__file__), 'res/file_types')))
            await valid_action.uploadFile(file_path)
        elif input_type == 'hidden':
            pass
        elif input_type == 'image':
            await valid_action.click()
        elif input_type == 'month':
            await valid_action.type(faker.date_time().strftime('%Y-%m'))
        elif input_type == 'number':
            await valid_action.type(str(random.random() * random.randrange(1000)))
        elif input_type == 'password':
            await valid_action.type(faker.password())
        elif input_type == 'radio':
            await valid_action.click()
        elif input_type == 'range':
            await valid_action.type(str(random.randint(0, 100)))
        elif input_type == 'reset':
            await valid_action.click()
        elif input_type == 'search':
            pass
        elif input_type == 'submit':
            await valid_action.click()
        elif input_type == 'tel':
            await valid_action.type(faker.phone_number())
        elif input_type == 'text':
            await valid_action.type(faker.text())
        elif input_type == 'time':
            await valid_action.type(faker.date_time().strftime('%H:%M%p'))
        elif input_type == 'url':
            await valid_action.type(faker.url())
        elif input_type == 'week':
            await valid_action.type(faker.date_time().strftime('%Y-W%U'))
