import sys

from bs4 import BeautifulSoup
import pyppeteer.page
import pyppeteer.element_handle
from models.webstate import Webstate


class Preprocessing:
    SIMILARITY_THRESHOLD = 0.8

    def __init__(self, page: pyppeteer.page.Page) -> None:
        self.page: pyppeteer.page.Page = page
        self.webstate_set: set[Webstate] = set()

    async def extract_webstate(self, page_url: str, page_html: str) -> tuple[Webstate, list[pyppeteer.element_handle.ElementHandle]]:
        valid_actions: list[pyppeteer.element_handle.ElementHandle] = await self._retrieveValidElements(page_html)
        webstate = Webstate(page_url, page_html)  # temporary current page webstate
        for prev_webstate in self.webstate_set:
            if prev_webstate.url != page_url:
                continue
            if self._is_similar_state(webstate, prev_webstate):
                return prev_webstate, valid_actions  # return previous webstate due to similarity

        self.webstate_set.add(webstate)  # update webstate set records
        return webstate, valid_actions

    def _is_similar_state(self, webstate1: Webstate, webstate2: Webstate) -> bool:
        # calculate using gestalt pattern matching from difflib package
        pass

    async def _retrieveValidElements(self, page_html: str) -> list[pyppeteer.element_handle.ElementHandle]:
        # parser = BeautifulSoup(page_html, "html.parser")
        # elements = BeautifulSoup(page_html, "html.parser").findAll()
        # body_elements: list[bs4.Tag] = .find('body').findChildren(recursive=False)
        # action_elements2: list[str] = list(map(lambda x: str(x), parser.select('input, a, button, select > option')))
        action_elements = await self.page.querySelectorAll('input, a, button, select > option')
        print(len(action_elements))
        return action_elements
