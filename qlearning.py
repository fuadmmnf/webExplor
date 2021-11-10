import math
from collections import defaultdict
from pyppeteer.element_handle import ElementHandle

from models.webstate import Webstate


class QLearning:
    DISCOUNT_FACTOR = 0.95
    GUMBEL_SOFTMAX_TAU = 1
    GUMBEL_SOFTMAX_IID = 1


    def __init__(self) -> None:
        self.visit_count_table: dict[tuple[
                                         Webstate, ElementHandle, Webstate], int] = defaultdict(lambda: 1,
                                                                                      {})  # track count of (s`, a, s) each time action a taken + update key if new state found
        self.q_table: dict[tuple[Webstate, ElementHandle]] = defaultdict(lambda: 1, {})  # state-action pair count recursively

    def _update_q_function(self, visit_tuple: tuple[Webstate, ElementHandle, Webstate]):
        pass

    def visit_state(self, from_state: Webstate, action, to_state: Webstate) -> None:
        visit_tuple: tuple[Webstate, ElementHandle, Webstate] = (from_state, action, to_state)
        self.visit_count_table[visit_tuple] = self.visit_count_table[visit_tuple] + 1
        # self._update_q_function(visit_tuple)

    def _get_action_count(self, from_state: Webstate, action, to_state: Webstate = None) -> int:
        return self.q_table[(from_state, action)] if to_state is None else self.visit_count_table[
            (from_state, action, to_state)]

    def calculate_curiosity(self, from_state: Webstate, action, to_state: Webstate = None) -> float:
        return 1.0 / math.sqrt(self._get_action_count(from_state, action, to_state))

    def calculate_action_weight(self, state: Webstate, action) -> float:
        def __calc(s, a):
            return math.exp((self.calculate_curiosity(s, a) + self.GUMBEL_SOFTMAX_IID) / self.GUMBEL_SOFTMAX_TAU)

        return __calc(state, action) / sum(map(lambda a: __calc(state, a), state.valid_actions))
