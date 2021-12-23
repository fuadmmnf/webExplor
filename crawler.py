import random
import os
import time
from collections import defaultdict
from urllib.parse import urlparse
from typing import Optional
from faker import Faker
import pyppeteer.page
from pyppeteer import launch
from preprocessing import Preprocessing
from qlearning import QLearning
from models.webstate import Webstate
from models.action import Action
from models.failure import Failure

Testcase = list[tuple[Webstate, Optional[Action]]]


class Crawler:
    MAXIMUM_STEPS = 8
    TRACE_SELECTION_INTERVAL = 5
    TIME_BUDGET_MINUTES = 30

    def __init__(self, home_url: str):
        self.qlearning: QLearning = QLearning()
        self.preprocessing: Preprocessing = Preprocessing()
        self.home_url: str = home_url
        self.browser: Optional[pyppeteer.page.Browser] = None
        self.active_page: Optional[pyppeteer.page.Page] = None
        self.invalid_actions: dict[Action, bool] = defaultdict(lambda: False, {})
        self.application_failures: list[Failure] = []

    async def init_browser(self) -> None:
        if self.browser is None:
            # self.browser = await launch(headless=False, devtools=True)
            self.browser = await launch(headless=False)

    async def crawl(self) -> list[Testcase]:

        await self.init_browser()
        root_domain: str = urlparse(self.home_url).netloc
        #################
        self.active_page = (await self.browser.pages())[-1]
        # @self.active_page.on('error')
        # def handle_error(message):
        #     print(message)
        #
        # @self.active_page.on('pageerror')
        # def handle_page_error(message):
        #     print(message)

        # @self.active_page.on('requestfailed')
        # def handle_request_error(message: Request):
        #     print(message.failure())

        @self.active_page.on('console')
        def handle_request_error(message: pyppeteer.page.ConsoleMessage):
            if message.type == 'error':
                failure: Failure = Failure(message.text, self.active_page.url)
                if failure not in self.application_failures:
                    self.application_failures.append(failure)

        #################

        failed_test_cases: list[Testcase] = []
        test_case_iterator = 0
        start_time: time = time.time()
        while True:
            await self.active_page.goto(self.home_url, {'waitUntil': 'networkidle0'})

            prev_webstate: Webstate = (await self._get_page_webstate())[0]
            action_sequence: list[Optional[Action]] = [sorted(prev_webstate.valid_actions,
                                                              key=lambda act: self.qlearning.calculate_action_weight(
                                                                  prev_webstate, act) if not self.invalid_actions[
                                                                  act] else -1,
                                                              reverse=True)[0]]
            no_new_state_interval: time = time.time()
            testcase: Testcase = [(prev_webstate, action_sequence[0])]
            action_sequence_iterator = 0
            print('Starting testing from home page\n\n')
            while True:

                # apply action here check if error rises in current page environemnt: p, failed := env ( p', act),
                # if failed append current_test in failed_test_cases list
                failed = await self._perform_action(self.active_page, action_sequence)
                if failed:
                    failed_test_cases.append(testcase)

                # s, va = get_webstate(p), get new state after performing action(s)
                w: tuple[
                    Webstate, bool] = await self._get_page_webstate()  # returns webstate and if new state discovered
                next_webstate = w[0]
                # check if stuck for some while
                if not w[1] and (time.time() - no_new_state_interval) / 60.0 > 2:
                    pass  ### DUE - initiate dfa ###
                else:
                    no_new_state_interval = time.time()

                # calculate curiosity for transition s`, a, s
                action: Action = action_sequence[0]
                if urlparse(next_webstate.url).netloc != root_domain:
                    self.invalid_actions[action] = True
                    break

                self.qlearning.visit_state(prev_webstate, action, next_webstate)  # track count of state visit
                # self.qlearning.calculate_curiosity(prev_webstate, action, new_webstate)

                # train policy for state
                if next_webstate is not prev_webstate:
                    self.qlearning.update_q_function(prev_webstate, action)

                # update dfa
                ## DUE ##

                # append action action to test_case
                testcase.append((next_webstate, action))

                # update available_actions with actions(sorted) of updated state
                action_sequence = [sorted(next_webstate.valid_actions,
                                          key=lambda act: self.qlearning.calculate_action_weight(
                                              next_webstate, act) if not self.invalid_actions[act] else -1,
                                          reverse=True)[0]]

                ########testing q-values#########
                # print(self.qlearning.visit_count_table)
                # print(self.qlearning.state_action_count)
                # print(self.qlearning.q_table)
                # print(self.qlearning.transition_table)

                # for k, v in self.qlearning.visit_count_table.items():
                #     print(k, v)
                print(prev_webstate, action, next_webstate)
                for a in next_webstate.valid_actions:
                    print(a, self.qlearning.q_table[(
                                              next_webstate, a)] if not self.invalid_actions[a] else -1)

                print('\n\n')

                # current_page = p, current_state = s
                prev_webstate = next_webstate

                #################
                action_sequence_iterator = action_sequence_iterator + 1
                if action_sequence_iterator > self.MAXIMUM_STEPS:
                    break
            test_case_iterator = test_case_iterator + 1
            if (time.time() - start_time) / 60.0 > 30:
                break

        await self.browser.close()
        return failed_test_cases

    async def _get_page_webstate(self) -> tuple[Webstate, bool]:

        webstate: tuple[Webstate, bool] = await self.preprocessing.extract_webstate_and_is_new_state(self.active_page)
        # print(webstate.valid_actions[0])
        return webstate


    async def _perform_action(self, page: pyppeteer.page.Page, valid_actions: list[Optional[Action]]) -> bool:
        is_failing = False
        # Get page error events for action
        ## DUE ##

        # Apply action(s) to page
        for valid_action in valid_actions:

            if valid_action is None:
                continue

            tag_name = await (await valid_action.getProperty('tagName')).jsonValue()
            # print('tag name: ' + tag_name)
            if tag_name == 'A':
                # for self page navigation
                # link = await (await valid_action.getProperty('href')).jsonValue()
                # if link == 'javascript:void(0)':
                #     self.invalid_actions[valid_action] = True
                #     continue
                #
                # await page.goto(link.__str__())
                #######
                await valid_action.click()
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
                # print('input type: ' + input_type)
                if input_type == 'button':
                    await valid_action.click()
                elif input_type == 'checkbox':
                    await valid_action.click()
                elif input_type == 'color':
                    # not working
                    # r = lambda: random.randint(0, 255)
                    # color = '#%02X%02X%02X' % (r(), r(), r())
                    # print(color)
                    # await valid_action.type(color)
                    pass

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
                    # not working
                    # rand_range = str(random.randint(0, 100))
                    # print(rand_range)
                    # await valid_action.type()
                    pass
                elif input_type == 'reset':
                    await valid_action.click()
                elif input_type == 'search':  # potential
                    await valid_action.type(faker.text())
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

        # Remove page error events for action
        ## DUE ##

        # await page.waitForNavigation({'waitUntil': 'networkidle0'})
        return is_failing
