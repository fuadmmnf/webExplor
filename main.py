import asyncio
from crawler import Crawler


def explore_webpage(url: str) -> None:
    # get webpage content
    crawler: Crawler = Crawler(url)
    asyncio.get_event_loop().run_until_complete(crawler.start())


if __name__ == '__main__':
    websites = ["http://localhost:8080"]  # petclinic
    # websites = ["http://localhost:3000/pagekit/index.php/admin/"] # pagekit
    # websites = ["http://localhost:4000"] #  trello
    # websites = ["http://localhost:4000"]  # retroboard
    for website in websites:
        explore_webpage(website)
