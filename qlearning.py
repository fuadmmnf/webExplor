from math import sqrt

from models.webstate import Webstate


class QLearning:
    def __init__(self) -> None:
        self.visit_count_table: dict[tuple[
                                         Webstate, str, Webstate], int] = dict()  # track count of (s`, a, s) each time action a taken + update key if new state found

    def _add_new_state(self, visit_tuple: tuple[Webstate, str, Webstate]) -> None:
        self.visit_count_table[visit_tuple] = 1

    def visit_state(self, from_state: Webstate, action, to_state: Webstate) -> None:
        visit_tuple: tuple[Webstate, str, Webstate] = (from_state, action, to_state)
        if visit_tuple not in self.visit_count_table:
            self._add_new_state(visit_tuple)

        self.visit_count_table[visit_tuple] = self.visit_count_table[visit_tuple] + 1

    def _get_visit_count(self, from_state: Webstate, action, to_state: Webstate) -> int:
        return self.visit_count_table[(from_state, action, to_state)]

    def calculate_curiosity(self, from_state: Webstate, action, to_state: Webstate) -> float:
        return 1.0 / sqrt(self._get_visit_count(from_state, action, to_state))
