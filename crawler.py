import random
import os
from typing import Optional
from faker import Faker
import pyppeteer.page
from pyppeteer import launch
from preprocessing import Preprocessing
from qlearning import QLearning
from models.webstate import Webstate
from pyppeteer.element_handle import ElementHandle

Testcase = list[tuple[Webstate, Optional[ElementHandle]]]


class Crawler:
    MAXIMUM_STEPS = 8
    TRACE_SELECTION_INTERVAL = 5
    TIME_BUDGET_MINUTES = 30

    def __init__(self, home_url: str):
        self.home_url: str = home_url
        self.browser: Optional[pyppeteer.page.Browser] = None
        self.active_page: Optional[pyppeteer.page.Page] = None

    async def init_browser(self) -> None:
        if self.browser is None:
            # self.browser = await launch(headless=False, devtools=True)
            self.browser = await launch(headless=False)

    async def crawl(self) -> list[Testcase]:
        qlearning: QLearning = QLearning()
        await self.init_browser()
        #################
        self.active_page = await self.browser.pages()[-1]
        ################
        await self.active_page.goto(self.home_url, {'waitUntil': 'networkidle0'})

        failed_test_cases: list[Testcase] = []
        while True:
            action_sequence: list[Optional[ElementHandle]] = [None]
            prev_webstate: Webstate = await self._get_page_webstate()
            testcase: Testcase = [(prev_webstate, None)]
            while True:
                # apply action here check if error rises in current page environemnt: p, failed := env ( p', act), if failed append current_test in failed_test_cases list
                failed = await _perform_action(self.active_page, action_sequence)
                if failed:
                    failed_test_cases.append(testcase)
                # s, va = get_webstate(p), get new state after performing action(s)
                new_webstate: Webstate = await self._get_page_webstate()

                # check if stuck for some while

                # calculate curiosity for each eaction in state s`, a, s
                action = action_sequence[-1]
                curiosity: float = qlearning.calculate_curiosity(prev_webstate, action, new_webstate)
                # train policy for state
                # update dfa
                # append action action to test_case
                testcase.append((new_webstate, action))
                # update available_actions with actions(sorted) of updated state

                # current_page = p, current_state = s
                prev_webstate = new_webstate
                break
            break

        await self.browser.close()
        return failed_test_cases

    async def _get_page_webstate(self) -> Webstate:
        preprocessing: Preprocessing = Preprocessing(self.active_page)
        return await preprocessing.extract_webstate(self.active_page.url, await self.active_page.content())


async def _perform_action(page: pyppeteer.page.Page, valid_actions: list[Optional[ElementHandle]]) -> bool:
    is_failing = False

    for valid_action in valid_actions:
        if valid_action is None:
            continue

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

    return is_failing
