
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import pyppeteer.page
from pyppeteer.element_handle import ElementHandle
from models.webstate import Webstate
from models.action import Action


class Preprocessing:
    SIMILARITY_THRESHOLD = 0.8

    def __init__(self, page: pyppeteer.page.Page) -> None:
        self.page: pyppeteer.page.Page = page
        self.webstate_set: set[Webstate] = set()

    async def extract_webstate(self, page_url: str, page_html: str) -> Webstate:
        valid_actions: tuple[Action] = await self._retrieve_valid_elements(page_html, page_url)
        webstate = Webstate(page_url, page_html, valid_actions)  # temporary current page webstate
        for prev_webstate in self.webstate_set:
            if prev_webstate.url != page_url:
                continue
            if self._is_similar_state(webstate, prev_webstate):
                return Webstate(prev_webstate.url, prev_webstate.html,
                                valid_actions)  # return previous webstate due to similarity

        self.webstate_set.add(webstate)  # update webstate set records
        return webstate

    def _is_similar_state(self, webstate1: Webstate, webstate2: Webstate) -> bool:
        # calculate using gestalt pattern matching from difflib package
        soup1, soup2 = BeautifulSoup(webstate1.html, "html.parser"), BeautifulSoup(webstate2.html, "html.parser")
        tags1, tags2 = [str(tag) for tag in soup1.find_all()], [str(tag) for tag in soup2.find_all()]

        return SequenceMatcher(None, tags1, tags2).ratio() >= self.SIMILARITY_THRESHOLD

    async def _retrieve_valid_elements(self, page_html: str, page_url: str) -> tuple[Action]:
        parser = BeautifulSoup(page_html, "html.parser")
        # elements = BeautifulSoup(page_html, "html.parser").findAll()sequences of lines of text,
        # body_elements: list[bs4.Tag] = .find('body').findChildren(recursive=False)
        action_element_htmls: list[str] = list(map(lambda x: str(x), parser.select('input, a, button, select > option')))
        element_handles: list[ElementHandle] = await self.page.querySelectorAll(
            'input, a, button, select')
        # print(len(action_element_htmls), len(element_handles))
        actionable_elements: tuple[Action] = tuple([Action(e, s, page_url) for (e, s) in zip(element_handles, action_element_htmls)])
        return actionable_elements
