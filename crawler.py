import asyncio
import logging
import random
import time
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from faker import Faker

import pyppeteer.page
from pyppeteer.dialog import Dialog
from pyppeteer import launch

from models.action import Action
from models.failure import Failure
from models.form_group import FormGroup
from models.webstate import Webstate
from preprocessing import Preprocessing
from qlearning import QLearning

Testcase = list[tuple[Webstate, Optional[Action]]]


class Crawler:
    MAXIMUM_STEPS = 8
    TRACE_SELECTION_INTERVAL = 2
    TIME_BUDGET_MINUTES = 30
    EPSILON = 0.5
    IS_HEADLESS_START = False

    def __init__(self, home_url: str, project_code: str):
        self.qlearning: QLearning = QLearning()
        self.preprocessing: Preprocessing = Preprocessing()
        self.home_url: str = home_url
        self.project_code: str = project_code
        self.home_state = None
        self.browser: Optional[pyppeteer.page.Browser] = None
        self.active_page: Optional[pyppeteer.page.Page] = None
        self.invalid_actions: dict[Action, bool] = defaultdict(lambda: False, {})
        self.webstate_action_exploration_dict: dict[tuple[Webstate, Action], int] = defaultdict(lambda: 0,
                                                                                                {})  # 0 => unexplored, 1 => active, 2 => complete
        self.webstate_form_state_dict: dict[tuple[Webstate, Action], int] = defaultdict(lambda: 0,
                                                                                        {})  # 0 => all fields blank, 1 => some fields filled, 2 => all fields filled
        self.application_failures: list[Failure] = []

        self.root_domain: str = urlparse(self.home_url).netloc
        self.failed_test_cases: list[Testcase] = []
        self.test_case_iterator = 0
        self.start_time: time = time.time()
        self.no_new_state_interval: time = time.time()
        self.last_reporting_time = time.time()

        logging.basicConfig(
            filename=f'res/logs/{self.project_code}_{datetime.now().strftime("%m%d-%H%M%S")}.log',
            filemode='w',
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.WARNING,
            datefmt='%Y-%m-%d %H:%M:%S')

    async def init_browser(self) -> None:

        if self.browser is not None:
            await self.browser.close()
            # self.browser = await launch(headless=False, devtools=True)
        # self.browser = await launch(headless=self.IS_HEADLESS_START, args=['--disable-dev-shm-usage'])
        self.browser = await launch(headless=self.IS_HEADLESS_START, slowMo=0 if self.IS_HEADLESS_START else 3,
                                    userDataDir='/tmp/myChromeSession',
                                    args=['--no-sandbox', '--disable-setuid-sandbox'])
        # self.browser = await launch(headless=self.IS_HEADLESS_START)

    async def _restart_env(self, wait: bool):
        # await self.browser.newPage()
        # await (await self.browser.pages())[0].close()
        await self.init_browser()
        self.active_page = (await self.browser.pages())[0]
        # await self.active_page.setViewport({'width': 1366, 'height': 768})
        await self.active_page.goto(self.home_url, {'waitUntil': 'networkidle0'} if wait else {})
        await self.active_page.setCacheEnabled(True)

        # print('Starting testing from home page\n\n')

        async def handle_request_error(message: pyppeteer.page.ConsoleMessage):
            if message.type == 'error':
                failure: Failure = Failure(message.text, self.active_page.url)
                logging.error("Failure: " + str(len(self.application_failures)) + str(failure))

                if failure not in self.application_failures:
                    self.application_failures.append(failure)
                    # logging.error("Failure: " + str(len(self.application_failures)) + str(failure))

        self.active_page.on('console', lambda message: asyncio.ensure_future(handle_request_error(message)))

        async def handle_dialog(dialog: Dialog):
            if random.uniform(0, 1) > 0.5:
                await dialog.accept(promptText=Faker().text()[: random.randint(0, 50)])
            else:
                await dialog.dismiss()

        self.active_page.on(
            'dialog',
            lambda dialog: asyncio.ensure_future(handle_dialog(dialog))
        )

        await self._initial_setup()

    async def _initial_setup(self):

        if random.uniform(0, 1) > 0.1:
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
                                key=lambda act: ([100, 1000, self.qlearning.calculate_action_weight(
                                    webstate, act)][self.webstate_action_exploration_dict[(webstate, act)]] if not
                                self.invalid_actions[act] else -1,
                                                 random.random()),
                                reverse=True)  # not dfs, dfs + bfs combination

        # sorted_actions = sorted(webstate.valid_actions,
        #                         key=lambda act: (
        #                         [100, 1000, 10][self.webstate_action_exploration_dict[(webstate, act)]] if not
        #                         self.invalid_actions[act] else -1, random.random()),
        #                         reverse=True)  # not dfs, dfs + bfs combination

        return sorted_actions[0]

    async def start(self):
        time_elapsed = (time.time() - self.start_time) / 60

        while time_elapsed <= self.TIME_BUDGET_MINUTES:
            try:
                await self.crawl()  # crawl will close program upon finishing
            except:
                traceback.print_exc()
                pass
            time_elapsed = (time.time() - self.start_time) / 60

        logging.warning(
            "Unique Webstates:" + str(len(self.preprocessing.webstate_set)) + str(self.preprocessing.webstate_set))
        logging.warning('Unique Failures: ' + str(len(self.application_failures)))
        for f in self.application_failures:
            logging.error(str(f))
        await self.browser.close()

    async def crawl(self):
        while True:
            await self._restart_env(True)
            # input()
            prev_webstate: Webstate = (await self._get_page_webstate())[0]
            self.home_state = prev_webstate

            action_sequence = [None]
            testcase: Testcase = [(prev_webstate, None)]
            discovered_states: list[Webstate] = [prev_webstate]
            action_sequence_iterator = 0

            # for duplicate action reduction
            webstate_unique_action_discovered: dict[Webstate, Optional[list[Action, int]]] = defaultdict(
                lambda: None, {})  # webstate non duplicate action list with discovery status
            action_discovered_dict: dict[Action, bool] = defaultdict(lambda: False, {})

            # redo entire process
            rootstate_actions_exploration_left = len([a for a in prev_webstate.valid_actions or [] if
                                                      self.webstate_action_exploration_dict[
                                                          (prev_webstate, a)] < 2 and not self.invalid_actions[a]])
            if rootstate_actions_exploration_left == 0:
                self.webstate_action_exploration_dict.clear()

            # redo entire process

            while True:
                # apply action here check if error rises in current page environemnt: p, failed := env ( p', act),
                # if failed append current_test in failed_test_cases list
                # print('prev url: ', self.active_page.url)
                action: Action = action_sequence.pop(0)
                try:
                    failed = await self._perform_action(prev_webstate, action)
                except:
                    failed = False
                # print('next url: ', self.active_page.url)
                if failed:
                    self.failed_test_cases.append(testcase)

                # s, va = get_webstate(p), get new state after performing action(s)
                w: tuple[
                    Webstate, bool] = await self._get_page_webstate()  # returns webstate and if new state discovered
                next_webstate = w[0]

                # check if stuck for some while
                # if len(action_sequence) == 0 and (
                #         time.time() - self.no_new_state_interval) / 60 > self.TRACE_SELECTION_INTERVAL:
                #     # pass  ### DUE - initiate dfa ###
                #     await self._restart_env(False)
                #     prev_webstate: Webstate = (await self._get_page_webstate())[0]
                #     edges = self.qlearning.generate_most_curious_action_trace(self.home_state)
                #     print('Visit count table for DFA: \n ')
                #     print(self.qlearning.visit_count_table)
                #     print('edges from dfa', edges)
                #     action_sequence = list(map(lambda t: t[1], edges))
                #     action_sequence.insert(0, None)
                #     action_sequence_iterator = 0
                #     print('DFA', action_sequence_iterator, action_sequence)
                #     print('\n')
                #     testcase = [(prev_webstate, None)]  # track resulting webstate and action responsible
                #
                #     no_new_state_interval = time.time()
                #     discovered_states = [prev_webstate]
                #     continue
                # elif w[1]:
                #     # print('new state found', next_webstate)
                #     # input("press to pass")
                #     self.no_new_state_interval = time.time()

                # calculate curiosity for transition s`, a, s

                if urlparse(next_webstate.url).netloc != self.root_domain:  # action is useless for testing
                    print('invalid action detected', action)
                    self.invalid_actions[action] = True
                    break

                # steps after visiting a state
                self.qlearning.visit_state(prev_webstate, action, next_webstate)  # track count of state visit

                is_next_state_new_in_execution_trace = webstate_unique_action_discovered[
                                                           next_webstate] is None
                if is_next_state_new_in_execution_trace:
                    non_duplicate_actions = [a for a in next_webstate.valid_actions if
                                             not action_discovered_dict[
                                                 a]]  # state actions - discovered actions
                    webstate_unique_action_discovered[next_webstate] = non_duplicate_actions

                    for a in non_duplicate_actions:  # make actions found
                        action_discovered_dict[a] = True

                next_webstate.valid_actions = [a for a in webstate_unique_action_discovered[
                    next_webstate] if not self.invalid_actions[
                    a]]  # what if new action found for similar state???

                # if "owners/" in next_webstate.url:
                #     logging.info(f'exploration dict:  {self.webstate_action_exploration_dict}')

                # self.qlearning.calculate_curiosity(prev_webstate, action, new_webstate)

                # train policy for state
                # self.qlearning.update_q_function(prev_webstate, action, False)

                if next_webstate not in discovered_states and next_webstate != prev_webstate:
                    self.qlearning.update_q_function(prev_webstate, action, False)
                    discovered_states.append(next_webstate)
                else:
                    self.qlearning.update_q_function(prev_webstate, action, True)

                # TO-DO need to define formula for form interaction exploration completeness
                if type(action) is FormGroup:
                    self.webstate_form_state_dict[(prev_webstate, action)] = self.webstate_form_state_dict[(
                        prev_webstate,
                        action)] + 1
                    self.webstate_action_exploration_dict[
                        (prev_webstate,
                         action)] = 1 if self.webstate_form_state_dict[(prev_webstate, action)] < 2 else 2
                else:
                    nextstate_actions_exploration_left = len([a for a in next_webstate.valid_actions or [] if
                                                              self.webstate_action_exploration_dict[
                                                                  (next_webstate, a)] < 2])
                    self.webstate_action_exploration_dict[
                        (prev_webstate,
                         action)] = 1 if nextstate_actions_exploration_left > 0 and discovered_states.index(
                        prev_webstate) < discovered_states.index(next_webstate) else 2
                    # if discovered_states.index(
                    #     prev_webstate) < discovered_states.index(next_webstate):
                    #     self.invalid_actions[action] = True # experimental
                # append action action to test_case
                for s in action.interaction_sequence if action is not None else [None]:
                    testcase.append((next_webstate, s))

                # update available_actions with actions(sorted) of updated state
                if not len(next_webstate.valid_actions or []):
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
                print(f'{prev_webstate}, {action}, {next_webstate}, {next_webstate.url}')
                # print('url s: ', prev_webstate.url, next_webstate.url)
                for a in next_webstate.valid_actions:
                    print(f'{a}, {self.qlearning.q_table[(next_webstate, a)] if not self.invalid_actions[a] else -1}')
                print('\n\n')
                # current_page = p, current_state = s
                prev_webstate = next_webstate

                #################
                action_sequence_iterator = action_sequence_iterator + 1
                if action_sequence_iterator > self.MAXIMUM_STEPS:
                    break

            test_case_iterator = self.test_case_iterator + 1
            time_elapsed = (time.time() - self.start_time) / 60

            if time_elapsed > self.TIME_BUDGET_MINUTES:
                break

        return

    # return self.failed_test_cases

    async def _get_page_webstate(self) -> tuple[Webstate, bool]:
        # await self.active_page.waitFor(50)
        webstate: tuple[Webstate, bool] = await self.preprocessing.extract_webstate_and_is_new_state(self.active_page)
        return webstate

    async def _perform_action(self, webstate: Webstate, valid_action: Optional[Action]) -> bool:
        is_failing = False
        # Get page error events for action
        ## DUE ##

        # Apply action(s) to page
        # print('valid action:', valid_action)
        if valid_action is None:
            return is_failing
        tag = await valid_action.interact(self.webstate_form_state_dict[(webstate, valid_action)])
        if tag == "A":
            await self.active_page.waitForNavigation({'timeout': 500})

        return is_failing
