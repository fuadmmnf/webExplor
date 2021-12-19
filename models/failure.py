from models.action import Action
from models.webstate import Webstate

class Failure():
    def __init__(self, text: str, action: Action = None, webstate: Webstate = None):
        self.text = text
        self.action = action
        self.webstate = webstate
        self._hash = hash((self.text, self.action, self.webstate))

    # def __str__(self) -> str:
    #     return f'{self.page_url} -> {self.outer_html}'
    #
    def __str__(self) -> str:
        return f'{self._hash} -> {self.text}'
    
    def __repr__(self) -> str:
        return f'{self._hash} -> {self.text}'

    def __hash__(self):
        return self._hash

    def __eq__(self, other: object) -> bool:
        return self.__hash__() == other.__hash__()

    def __ne__(self, other):
        return not(self == other)