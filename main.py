import asyncio
from crawler import Crawler


if __name__ == '__main__':
    website = ("http://localhost:8080", 'petclinic')  # petclinic
    # website = ("http://localhost:3000/pagekit/index.php/admin/", 'pagekit')  # pagekit
    # website = ("http://localhost:4000", 'trello')  # trello
    # website = ("http://localhost:4000", 'retroboard')  # retroboard
    crawler: Crawler = Crawler(website[0], website[1])
    asyncio.get_event_loop().run_until_complete(crawler.start())
