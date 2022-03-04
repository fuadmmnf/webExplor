from pyppeteer.element_handle import ElementHandle
from hashlib import md5

from models.action import Action


class Webstate:
    def __init__(self, url: str, html: str, valid_actions: tuple[Action] = None, tags: tuple = None):
        self.url: str = url
        self.html: str = html
        self.valid_actions: tuple[Action] = [] if valid_actions is None else valid_actions
        self.tags: tuple = [] if tags is None else tags

        m = md5()
        for s in tuple(self.url) + self.tags:
            m.update(str(s).encode())
        self._hash = int(m.hexdigest(), 16)

    def __repr__(self) -> str:
        return f'{self._hash}'

    def __hash__(self):
        return self._hash

    def __eq__(self, other: object) -> bool:
        return self.__hash__() == other.__hash__()

    def __ne__(self, other):
        return not (self == other)
