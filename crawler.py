import random
import os
import sys
import time
import traceback
from collections import defaultdict
from urllib.parse import urlparse
from typing import Optional

import numpy.random
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
    MAXIMUM_STEPS = 9
    TRACE_SELECTION_INTERVAL = 2
    TIME_BUDGET_MINUTES = 30
    EPSILON = 0.5
    IS_HEADLESS_START = False

    def __init__(self, home_url: str):
        self.qlearning: QLearning = QLearning()
        self.preprocessing: Preprocessing = Preprocessing()
        self.home_url: str = home_url
        self.home_state = None
        self.browser: Optional[pyppeteer.page.Browser] = None
        self.active_page: Optional[pyppeteer.page.Page] = None
        self.invalid_actions: dict[Action, bool] = defaultdict(lambda: False, {})
        self.application_failures: list[Failure] = []

        self.root_domain: str = urlparse(self.home_url).netloc
        self.failed_test_cases: list[Testcase] = []
        self.test_case_iterator = 0
        self.start_time: time = time.time()
        self.no_new_state_interval: time = time.time()

    async def init_browser(self) -> None:

        if self.browser is not None:
            await self.browser.close()
            # self.browser = await launch(headless=False, devtools=True)
        self.browser = await launch(headless=self.IS_HEADLESS_START, args=['--disable-dev-shm-usage'])

    async def _restart_env(self, wait: bool):
        # await self.browser.newPage()
        # await (await self.browser.pages())[0].close()
        self.active_page = (await self.browser.pages())[0]
        # await self.active_page.setViewport({'width': 1366, 'height': 768})
        try:
            await self.active_page.goto(self.home_url, {'waitUntil': 'networkidle0'} if wait else {})
        except Exception as e:
            return await self.crawl()

        # print('Starting testing from home page\n\n')

        @self.active_page.on('console')
        def handle_request_error(message: pyppeteer.page.ConsoleMessage):
            if message.type == 'error':
                failure: Failure = Failure(message.text, self.active_page.url)
                if failure not in self.application_failures:
                    self.application_failures.append(failure)
                    print("Failure: ", len(self.application_failures), failure)

    def _select_epsilon_greedy_action(self, webstate) -> Action:
        sorted_actions = []

        sorted_actions = sorted(webstate.valid_actions,
                                key=lambda act: self.qlearning.calculate_action_weight(
                                    webstate, act) if not self.invalid_actions[act] else -1, reverse=True)

        return sorted_actions[0]

    async def start(self):
        while True:
            await self.crawl()  # crawl will close program upon finishing

    async def crawl(self) -> list[Testcase]:

        await self.init_browser()

        while True:
            try:
                await self._restart_env(True)
                # input()
                prev_webstate: Webstate = (await self._get_page_webstate())[0]
                self.home_state = prev_webstate

                action_sequence = [None]
                testcase: Testcase = [(prev_webstate, None)]
                discovered_states: list[Webstate] = [prev_webstate]
                action_sequence_iterator = 0

                # for duplicate action reduction
                webstate_unique_action_discovered: dict[Webstate, list[Action]] = defaultdict(lambda: [], {})
                action_discovered_dict: dict[Action, bool] = defaultdict(lambda: False, {})

                while True:
                    try:
                        # apply action here check if error rises in current page environemnt: p, failed := env ( p', act),
                        # if failed append current_test in failed_test_cases list
                        # print('prev url: ', self.active_page.url)
                        action: Action = action_sequence.pop(0)
                        failed = await self._perform_action(self.active_page, action)
                        # print('next url: ', self.active_page.url)
                        if failed:
                            self.failed_test_cases.append(testcase)

                        # s, va = get_webstate(p), get new state after performing action(s)
                        w: tuple[
                            Webstate, bool] = await self._get_page_webstate()  # returns webstate and if new state discovered
                        next_webstate = w[0]

                        # check if stuck for some while
                        if len(action_sequence) == 0 and (
                                time.time() - self.no_new_state_interval) / 60 > self.TRACE_SELECTION_INTERVAL:
                            # pass  ### DUE - initiate dfa ###
                            await self._restart_env(False)
                            prev_webstate: Webstate = (await self._get_page_webstate())[0]
                            edges = self.qlearning.generate_most_curious_action_trace(self.home_state)
                            print('Visit count table for DFA: \n ')
                            print(self.qlearning.visit_count_table)
                            print('edges from dfa', edges)
                            action_sequence = list(map(lambda t: t[1], edges))
                            action_sequence.insert(0, None)
                            action_sequence_iterator = 0
                            print('DFA', action_sequence_iterator, action_sequence)
                            print('\n')
                            testcase = [(prev_webstate, None)]

                            no_new_state_interval = time.time()
                            discovered_states = [prev_webstate]
                            continue
                        elif w[1]:
                            # print('new state found', next_webstate)
                            # input("press to pass")
                            self.no_new_state_interval = time.time()

                        # calculate curiosity for transition s`, a, s

                        if urlparse(next_webstate.url).netloc != self.root_domain:
                            self.invalid_actions[action] = True
                            break


                        self.qlearning.visit_state(prev_webstate, action, next_webstate)  # track count of state visit

                        # self.qlearning.calculate_curiosity(prev_webstate, action, new_webstate)

                        # train policy for state
                        # self.qlearning.update_q_function(prev_webstate, action, False)

                        if next_webstate not in discovered_states and next_webstate != prev_webstate:
                            self.qlearning.update_q_function(prev_webstate, action, False)
                            discovered_states.append(next_webstate)
                        else:
                            self.qlearning.update_q_function(prev_webstate, action, True)

                        # append action action to test_case
                        testcase.append((next_webstate, action))

                        # update available_actions with actions(sorted) of updated state
                        if not len(next_webstate.valid_actions):
                            break

                        if len(action_sequence) == 0:
                            action_sequence = [self._select_epsilon_greedy_action(next_webstate)]

                        ########testing q-values#########
                        # print(self.qlearning.visit_count_table)
                        # print(self.qlearning.state_action_count)
                        # print(self.qlearning.q_table)
                        # print(self.qlearning.transition_table)

                        # for k, v in self.qlearning.visit_count_table.items():
                        #     print(k, v)
                        # w: tuple[
                        #     Webstate, bool] = await self._get_page_webstate()  # returns webstate and if new state discovered
                        # demo_webstate = w[0]
                        print(prev_webstate, action, next_webstate, next_webstate.url)
                        # print('url s: ', prev_webstate.url, next_webstate.url)
                        # for a in next_webstate.valid_actions:
                        #     print(a, self.qlearning.q_table[(
                        #         next_webstate, a)] if not self.invalid_actions[a] else -1)

                        # print('\n\n\n\n')

                        # current_page = p, current_state = s
                        prev_webstate = next_webstate

                        #################
                        action_sequence_iterator = action_sequence_iterator + 1
                        if action_sequence_iterator > self.MAXIMUM_STEPS:
                            break
                    except Exception as e:
                        # print('the error was: ', e)
                        # traceback.print_exc()
                        return
                        # return await self.crawl()
            except Exception as e:
                # traceback.print_exc()
                return
                # return await self.crawl()

            test_case_iterator = self.test_case_iterator + 1
            if (time.time() - self.start_time) / 60.0 > self.TIME_BUDGET_MINUTES:
                break
        print("Unique Webstates:", len(self.preprocessing.webstate_set), self.preprocessing.webstate_set)
        print('Failures: ')
        print(len(self.application_failures), self.application_failures)
        await self.browser.close()

        sys.exit(0)
        # return self.failed_test_cases

    async def _get_page_webstate(self) -> tuple[Webstate, bool]:

        webstate: tuple[Webstate, bool] = await self.preprocessing.extract_webstate_and_is_new_state(self.active_page)
        return webstate

    async def _perform_action(self, page: pyppeteer.page.Page, valid_action: Optional[Action]) -> bool:
        is_failing = False
        # Get page error events for action
        ## DUE ##

        # Apply action(s) to page
        # print('valid action:', valid_action)
        try:
            if valid_action is None:
                return

            tag_name = await (await valid_action.getProperty('tagName')).jsonValue()
            # print('tag name: ' + tag_name)
            if tag_name == 'A':
                # for self page navigation
                link = await (await valid_action.getProperty('href')).jsonValue()
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
                    await valid_action.querySelectorEval(
                        'option:nth-child(' + str(random.randint(1, len(options))) + ')',
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

        except:
            self.invalid_actions[valid_action] = True

        # Remove page error events for action
        ## DUE ##
        await self.active_page.waitFor(50)
        # await page.waitForNavigation({'waitUntil': 'networkidle0'})

        return is_failing
