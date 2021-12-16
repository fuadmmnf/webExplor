from pyppeteer.element_handle import ElementHandle


class Action(ElementHandle):
    def __init__(self, element_handle: ElementHandle, outer_html: str, page_url: str):
        super().__init__(element_handle._context, element_handle._client, element_handle._remoteObject,
                         element_handle._page, element_handle._frameManager)
        self.outer_html = outer_html
        self.page_url = page_url

    def __str__(self) -> str:
        return f'{self.page_url} -> {self.outer_html}'

    def __hash__(self):
        return hash((self.page_url, self.outer_html))

    def __eq__(self, other: object) -> bool:
        return (self.page_url, self.outer_html) == (other.page_url, other.outer_html)

    def __ne__(self, other):
        return not(self == other)