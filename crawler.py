import asyncio
from pyppeteer import launch


class Crawler:
    def __init__(self, home_url: str):
        self.home_url = home_url

    async def get_browser(self):
        return await launch()

    async def get_page(self, browser, url: str):
        page = await browser.newPage()
        await page.goto(url)
        return page

    def crawl(self):
        pass
