import random
import os
import logging
import sys
import time
import asyncio
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse
from typing import Optional
from util import merge_intervals
import numpy.random
from faker import Faker
import pyppeteer.page
import pyppeteer.network_manager
from pyppeteer import launch
from preprocessing import Preprocessing
from qlearning import QLearning
from models.webstate import Webstate
from models.action import Action
from models.failure import Failure

Testcase = list[tuple[Webstate, Optional[Action]]]


class Crawler:
    MAXIMUM_STEPS = 8
    TRACE_SELECTION_INTERVAL = 2
    TIME_BUDGET_MINUTES = 30
    EPSILON = 0.5
    IS_HEADLESS_START = True

    def __init__(self, home_url: str, project_code: str):
        self.qlearning: QLearning = QLearning()
        self.preprocessing: Preprocessing = Preprocessing()
        self.home_url: str = home_url
        self.project_code: str = project_code
        self.home_state = None
        self.is_failing = False
        self.browser: Optional[pyppeteer.page.Browser] = None
        self.active_page: Optional[pyppeteer.page.Page] = None
        self.invalid_actions: dict[Action, bool] = defaultdict(lambda: False, {})
        self.application_failures: list[Failure] = []
        self.coverage_dict: dict[str, list[tuple[int, int]]] = defaultdict(lambda: [],
                                                                           {})  # js script to list of executed ranges

        self.root_domain: str = urlparse(self.home_url).netloc
        self.failed_test_cases: list[Testcase] = []
        self.test_case_iterator = 0
        self.start_time: time = time.time()
        self.no_new_state_interval: time = time.time()
        self.last_reporting_time = time.time()

        logging.basicConfig(
            filename=f'res/logs/webExplor/{self.project_code}_{datetime.now().strftime("%m%d-%H%M%S")}.log',
            filemode='w',
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.WARNING,
            datefmt='%Y-%m-%d %H:%M:%S')

    async def init_browser(self) -> None:
        if self.browser is not None:
            await self.browser.close()
            # self.browser = await launch(headless=False, devtools=True)
        # self.browser = await launch(headless=self.IS_HEADLESS_START, args=['--disable-dev-shm-usage'])
        self.browser = await launch(headless=self.IS_HEADLESS_START,
                                    userDataDir='/tmp/myChromeSession',
                                    args=['--no-sandbox', '--disable-setuid-sandbox'])
        # self.browser = await launch(headless=self.IS_HEADLESS_START)

    async def _restart_env(self, wait: bool):
        # await self.browser.newPage()
        # await (await self.browser.pages())[0].close()
        await self.init_browser()
        self.active_page = (await self.browser.pages())[0]
        # await self.active_page.setViewport({'width': 1366, 'height': 768})
        await self.active_page.coverage.startJSCoverage()

        await self.active_page.goto(self.home_url, {'waitUntil': 'networkidle0'} if wait else {})
        await self.active_page.setCacheEnabled(True)

        # print('Starting testing from home page\n\n')
        this = self

        async def handle_console_error(message: pyppeteer.page.ConsoleMessage):
            if message.type == 'error':
                self.is_failing = True
                failure: Failure = Failure(message.text, this.active_page.url)
                logging.error("Failure: " + str(failure))

                if failure not in this.application_failures:
                    this.application_failures.append(failure)
                    # logging.error("Failure: " + str(len(self.application_failures)) + str(failure))

        self.active_page.on('console', lambda message: asyncio.ensure_future(handle_console_error(message)))

        async def handle_request_error(http_request: pyppeteer.network_manager.Request):
            failing = False
            failure = None
            req_failure = http_request.failure()
            res = http_request.response
            if req_failure is not None:
                failing = True
                failure = Failure(req_failure["errorText"], this.active_page.url)
            if res is not None:
                if 400 <= res.status < 600:
                    failing = True
                    failure = Failure(f'status code({res.status}) -> {await res.text()}', this.active_page.url)

            if failing:
                logging.error("Failure: " + str(failure))
                if failure not in this.application_failures:
                    this.application_failures.append(failure)
                    # logging.error("Failure: " + str(len(self.application_failures)) + str(failure))

        self.active_page.on('requestfailed', lambda request: asyncio.ensure_future(handle_request_error(request)))
        self.active_page.on('requestfinished', lambda request: asyncio.ensure_future(handle_request_error(request)))

        await self._initial_setup(wait)

    async def _initial_setup(self, is_random):

        if not is_random or random.uniform(0, 1) > 0.1:
            if self.project_code == 'trello' and self.active_page.url == 'http://localhost:4000/sign_in':
                signin_button = await self.active_page.querySelector('button[type="submit"]')
                await signin_button.click()
                await self.active_page.waitForSelector('#authentication_container')

            elif self.project_code == 'pagekit':
                username_input = await self.active_page.querySelector('input[type="text"]')
                await username_input.type('admin')

                password_input = await self.active_page.querySelector('input[type="password"]')
                await password_input.type('asdfghjkl123')

                login_button = await self.active_page.querySelector('button')
                await login_button.click()

    def _select_epsilon_greedy_action(self, webstate) -> Action:
        sorted_actions = sorted(webstate.valid_actions,
                                key=lambda act: self.qlearning.calculate_action_weight(
                                    webstate, act) if not self.invalid_actions[act] else -1, reverse=True)

        return sorted_actions[0]

    async def save_code_coverage(self):
        jsCoverage = await self.active_page.coverage.stopJSCoverage()

        totalBytes = 0
        usedBytes = 0
        for entry in jsCoverage:
            # totalBytes += len(entry['text'])
            for range in entry['ranges']:
                self.coverage_dict[entry['text']].append((range['start'], range['end']))
                # usedBytes += range['end'] - range['start'] - 1

        # print('Bytes used: {}%'.format(usedBytes / totalBytes * 100))

    def report_statistics(self):
        total_bytes = 0
        used_bytes = 0
        coverages = {k: merge_intervals(v) for (k, v) in self.coverage_dict.items()}
        for script in coverages.keys():
            total_bytes += len(script)
            for r in coverages[script]:
                used_bytes += r[1] - r[0] - 1

        percentage = (used_bytes / total_bytes) * 100
        logging.warning(f'(Failure Count, Coverage Percentage) : ({len(self.application_failures)}, {percentage})')

    async def start(self):
        logging.warning("Starting")
        time_elapsed = (time.time() - self.start_time) / 60

        while time_elapsed <= self.TIME_BUDGET_MINUTES:
            try:
                await self.crawl()  # crawl will close program upon finishing
            except:
                pass
            await self.save_code_coverage()
            time_elapsed = (time.time() - self.start_time) / 60

            if (time.time() - self.last_reporting_time) / 60 >= 1:
                self.report_statistics()
                self.last_reporting_time = time.time()


        logging.warning("Finished")
        self.report_statistics()
        logging.warning(
            "Unique Webstates:" + str(len(self.preprocessing.webstate_set)) + str(self.preprocessing.webstate_set))
        logging.warning('Unique Failures: ' + str(len(self.application_failures)))
        for f in self.application_failures:
            logging.error(str(f))

        logging.warning("\nTest cases: ")
        for test in self.failed_test_cases:
            logging.error(" => ".join(iter([f'{str(t1[1])}' for t1 in test])))
        if self.browser is not None:
            await self.browser.close()

    async def crawl(self):
        try:
            await self._restart_env(True)
            # input()
            prev_webstate: Webstate = (await self._get_page_webstate())[0]
            self.home_state = prev_webstate

            action_sequence = [None]
            testcase: Testcase = []
            discovered_states: list[Webstate] = [prev_webstate]
            action_sequence_iterator = 0

            while True:
                # apply action here check if error rises in current page environemnt: p, failed := env ( p', act),
                # if failed append current_test in failed_test_cases list
                # print('prev url: ', self.active_page.url)
                action: Action = action_sequence.pop(0)
                try:
                    self.is_failing = False
                    await self._perform_action(action)
                except:
                    pass
                # append action action to test_case
                testcase.append((prev_webstate, action))
                # print('next url: ', self.active_page.url)
                if self.is_failing:
                    self.failed_test_cases.append(testcase)

                # s, va = get_webstate(p), get new state after performing action(s)
                w: tuple[
                    Webstate, bool] = await self._get_page_webstate()  # returns webstate and if new state discovered
                next_webstate = w[0]

                # check if stuck for some while
                if (time.time() - self.no_new_state_interval) / 60 > self.TRACE_SELECTION_INTERVAL:
                    await self.save_code_coverage()
                    await self._restart_env(False)
                    prev_webstate: Webstate = (await self._get_page_webstate())[0]
                    edges = self.qlearning.generate_most_curious_action_trace(self.home_state)
                    # print('Visit count table for DFA: \n ')
                    print('edges from dfa', edges)
                    action_sequence = list(map(lambda t: t[1], edges))
                    action_sequence.insert(0, None)
                    action_sequence_iterator = len(action_sequence)
                    # print('DFA', action_sequence_iterator, action_sequence)
                    # print('\n')
                    testcase = [(prev_webstate, None)]

                    self.no_new_state_interval = time.time()
                    discovered_states = [prev_webstate]
                    continue
                elif w[1]:
                    # print('new state found', next_webstate)
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
            # traceback.print_exc()
            return
            # return await self.crawl()

        test_case_iterator = self.test_case_iterator + 1

    async def _get_page_webstate(self) -> tuple[Webstate, bool]:

        webstate: tuple[Webstate, bool] = await self.preprocessing.extract_webstate_and_is_new_state(self.active_page)
        return webstate

    async def _perform_action(self, valid_action: Optional[Action]):

        # Apply action(s) to page
        # print('valid action:', valid_action)
        if valid_action is None:
            return
        tag = await valid_action.interact()
        if tag == "A":
            await self.active_page.waitForNavigation({'timeout': 500})

        return
