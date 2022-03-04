
from pyppeteer.element_handle import ElementHandle
from hashlib import md5


class Action(ElementHandle):
    def __init__(self, element_handle: ElementHandle, outer_html: str, page_url: str):
        super().__init__(element_handle._context, element_handle._client, element_handle._remoteObject,
                         element_handle._page, element_handle._frameManager)
        self.outer_html = outer_html
        self.page_url = page_url
        # self.g_iid = -math.log(-math.log(numpy.random.uniform(0.0, 1.0)))
        m = md5()
        for s in (self.page_url, self.outer_html):
            m.update(s.encode())
        self._hash = int(m.hexdigest(), 16)

    # def __str__(self) -> str:
    #     return f'{self.page_url} -> {self.outer_html}'
    #
    def __str__(self) -> str:
        return f'{self._hash} -> {self.outer_html.split(">")[0]}'
    
    def __repr__(self) -> str:
        return f'{self._hash} -> {self.outer_html.split(">")[0]}'

    def __hash__(self):
        return self._hash

    def __eq__(self, other: object) -> bool:
        return self.__hash__() == other.__hash__()

    def __ne__(self, other):
        return not(self == other)