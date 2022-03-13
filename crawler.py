import sys
import time
import traceback
from collections import defaultdict
from urllib.parse import urlparse
from typing import Optional

import pyppeteer.page
from pyppeteer import launch
from preprocessing import Preprocessing
from qlearning import QLearning
from models.webstate import Webstate
from models.action import Action
from models.form_group import FormGroup
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
        sorted_actions = sorted(webstate.valid_actions,
                                key=lambda act: [1000, 100, self.qlearning.calculate_action_weight(
                                    webstate, act)][self.webstate_action_exploration_dict[(webstate, act)]] if not
                                self.invalid_actions[act] else -1,
                                reverse=True)  # not dfs, dfs + bfs combination

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
                webstate_unique_action_discovered: dict[Webstate, Optional[list[Action, int]]] = defaultdict(
                    lambda: None, {})  # webstate non duplicate action list with discovery status
                action_discovered_dict: dict[Action, bool] = defaultdict(lambda: False, {})

                while True:
                    try:
                        # apply action here check if error rises in current page environemnt: p, failed := env ( p', act),
                        # if failed append current_test in failed_test_cases list
                        # print('prev url: ', self.active_page.url)
                        action: Action = action_sequence.pop(0)
                        failed = await self._perform_action(prev_webstate, action)
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
                            testcase = [(prev_webstate, None)]  # track resulting webstate and action responsible

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

                        next_webstate.valid_actions = webstate_unique_action_discovered[
                            next_webstate]  # what if new action found for similar state???

                        # TO-DO need to define formula for form interaction exploration completeness
                        if type(action) is FormGroup:
                            self.webstate_form_state_dict[(prev_webstate, action)] = max(2,
                                                                                         self.webstate_form_state_dict[(
                                                                                         prev_webstate, action)] + 1)
                            self.webstate_action_exploration_dict[
                                (prev_webstate,
                                 action)] = 1 if self.webstate_form_state_dict[(prev_webstate, action)] < 2 else 2
                        else:
                            nextstate_actions_exploration_left = len([a for a in next_webstate.valid_actions or [] if
                                                                      self.webstate_action_exploration_dict[
                                                                          (next_webstate, a)] < 2])
                            self.webstate_action_exploration_dict[
                                (prev_webstate,
                                 action)] = 1 if nextstate_actions_exploration_left > 0 and not is_next_state_new_in_execution_trace else 2

                        print('valid actions: ', next_webstate.valid_actions)
                        # print(self.webstate_action_exploration_dict, end='\n\n')

                        # self.qlearning.calculate_curiosity(prev_webstate, action, new_webstate)

                        # train policy for state
                        # self.qlearning.update_q_function(prev_webstate, action, False)

                        if next_webstate not in discovered_states and next_webstate != prev_webstate:
                            self.qlearning.update_q_function(prev_webstate, action, False)
                            discovered_states.append(next_webstate)
                        else:
                            self.qlearning.update_q_function(prev_webstate, action, True)

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
                        print(prev_webstate, action, next_webstate, next_webstate.url, end='\n\n')
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
                        traceback.print_exc()
                        sys.exit(1)
                        return
                        # return await self.crawl()
            except Exception as e:
                traceback.print_exc()
                sys.exit(1)
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

    async def _perform_action(self, webstate: Webstate, valid_action: Optional[Action]) -> bool:
        is_failing = False
        # Get page error events for action
        ## DUE ##

        # Apply action(s) to page
        # print('valid action:', valid_action)
        try:
            if valid_action is None:
                return is_failing
            await valid_action.interact(self.webstate_form_state_dict[(webstate, valid_action)])



        except:
            # self.invalid_actions[valid_action] = True
            pass

        await self.active_page.waitFor(50)
        # await page.waitForNavigation({'waitUntil': 'networkidle0'})

        return is_failing
