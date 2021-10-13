from models.webstate import Webstate


class Preprocessing:
    def __init__(self, similarity_threshold):
        self.webstate_similarity_threshold = similarity_threshold

    def extract_webstate(self, page_url: str, page_html: str) -> Webstate:
        pass

    def is_similar_state(self, webstate1: Webstate, webstate2: Webstate) -> bool:
        # calculate using gestalt pattern matching from difflib package
        pass
