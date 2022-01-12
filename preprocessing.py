from typing import Optional
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import pyppeteer.page
from pyppeteer.element_handle import ElementHandle
from models.webstate import Webstate
from models.action import Action


async def _retrieve_webstate(page: pyppeteer.page.Page, page_html: str, page_url: str) -> Webstate:
    parser = BeautifulSoup(page_html, "html.parser")
    # elements = BeautifulSoup(page_html, "html.parser").findAll()sequences of lines of text,
    # body_elements: list[bs4.Tag] = .find('body').findChildren(recursive=False)
    action_element_htmls: list[str] = list(
        map(lambda x: f'{x.name} ' + str({k: v for k, v in x.attrs.items() if v}), parser.select('input, a, button, select > option')))
    element_handles: list[ElementHandle] = await page.querySelectorAll(
        'input, a, button, select')

    actionable_elements: tuple[Optional[Action]] = tuple(
        [None if await e.boundingBox() is None else Action(e, s, page_url) for (e, s) in
         zip(element_handles, action_element_htmls)])
    actionable_elements: tuple[Action] = tuple(list(filter(None, actionable_elements)))  # filtering hidden actions
    tags = [hash(f'{tag.name} ' + str({k: v for k, v in tag.attrs.items() if v})) for tag in parser()]

    # tags = tags + [f'{k}="{v}"' for k, v in tag.attrs.items()]
    # tags = [str(t) for t in parser.find('body').findChildren(recursive=False)]
    # for tag in parser.find('body').findChildren(recursive=True):
    #     tags = tags + [f'{tag.name} {k} {v}' for k, v in tag.attrs.items()]

    # print(tags)
    # quit()
    # for tag_name in tags:
    #     print("{name}:{attrs}".format(name=tag_name, attrs=",".join(tags[tag_name])))
    return Webstate(page_url, page_html, actionable_elements, tuple(tags))


class Preprocessing:
    SIMILARITY_THRESHOLD = 0.8

    def __init__(self) -> None:
        self.webstate_set: set[Webstate] = set()

    async def extract_webstate_and_is_new_state(self, page: pyppeteer.page.Page) -> tuple[Webstate, bool]:
        page_url, page_html = page.url, await page.content()
        webstate = await _retrieve_webstate(page, page_html, page_url)
        for prev_webstate in self.webstate_set:
            if prev_webstate.url.rstrip('/') != page_url.rstrip('/'):
                continue
            if self._is_similar_state(webstate, prev_webstate):
                return (Webstate(prev_webstate.url, prev_webstate.html,
                                 webstate.valid_actions, prev_webstate.tags),
                        False)  # return previous webstate due to similarity
        self.webstate_set.add(webstate)  # update webstate set records
        # print(self.webstate_set)
        return webstate, True

    def _lcsubstring_length(self, a, b):
        table = {}
        l = 0
        for i, ca in enumerate(a, 1):
            for j, cb in enumerate(b, 1):
                if ca == cb:
                    table[i, j] = table.get((i - 1, j - 1), 0) + 1
                    if table[i, j] > l:
                        l = table[i, j]
        return l

    def _is_similar_state(self, webstate1: Webstate, webstate2: Webstate) -> bool:
        # calculate using gestalt pattern matching from difflib package

        similarity = (2 * self._lcsubstring_length(webstate1.tags, webstate2.tags)) / (
                len(webstate1.tags) + len(webstate2.tags))
        # similarity = SequenceMatcher(None, webstate1.tags, webstate2.tags).ratio()
        # print(webstate1.tags)
        # print(webstate2.tags)
        print('similarity: ' + str(similarity) + ' urls: ' + webstate1.url + ' -> ' + webstate2.url)
        return similarity >= self.SIMILARITY_THRESHOLD
