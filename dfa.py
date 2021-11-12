from dijkstar import Graph, find_path


class DFA:
    current_state = None

    def __init__(self, states, actions, transition_function, start_state, accept_states):
        self.states = states
        self.actions = actions
        self.transition_function = transition_function
        self.start_state = start_state
        self.accept_states = accept_states
        self.current_state = start_state
        self.graph = Graph()

    def update_transition_function(self, key, value):
        self.transition_function[key] = value
        self.graph.add_edge(key[0], value, (key[0], value, key[1]))  # to match with table from qlearning (s, a, s`)

    def transition_to_state_with_input(self, input_value):
        if (self.current_state, input_value) not in self.transition_function.keys():
            self.current_state = None
            return
        self.current_state = self.transition_function[(self.current_state, input_value)]

    def find_shortest_trace(self, key, value):
        return find_path(self.graph, key[0], value, cost_func=lambda a, b, c, d: 1).edges

    def in_accept_state(self):
        return self.current_state in self.accept_states

    def go_to_initial_state(self):
        self.current_state = self.start_state

    def run_with_input_list(self, input_list):
        self.go_to_initial_state()
        for inp in input_list:
            self.transition_to_state_with_input(inp)
        return self.in_accept_state()
