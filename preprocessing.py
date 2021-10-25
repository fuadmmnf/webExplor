from models.webstate import Webstate


class Preprocessing:
    SIMILARITY_THRESHOLD = 0.8

    def extract_webstate(self, page_url: str, page_html: str) -> Webstate:

        pass

    def is_similar_state(self, webstate1: Webstate, webstate2: Webstate) -> bool:
        # calculate using gestalt pattern matching from difflib package
        pass
