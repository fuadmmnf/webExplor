from models.webstate import Webstate


class Preprocessing:
    SIMILARITY_THRESHOLD = 0.8

    def __init__(self) -> None:
        self.webstate_set: set[Webstate] = set()

    def extract_webstate(self, page_url: str, page_html: str) -> tuple[Webstate, list[str]]:
        valid_actions: list[str] = self._retrieveValidElements(page_html)
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

    def _retrieveValidElements(self, page_html: str) -> list[str]:
        pass
