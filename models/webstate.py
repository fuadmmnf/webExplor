class Webstate:
    def __init__(self, url, html, valid_actions=None):

        self.url = url
        self.html = html
        self.state = None
        if valid_actions is None:
            self.valid_actions = []

