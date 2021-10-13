class Webstate:
    def __init__(self, url, html):
        self.url = url
        self.html = html
        self.state = None
        self.valid_actions = []

