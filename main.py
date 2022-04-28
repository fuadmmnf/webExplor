import asyncio
from crawler import Crawler
import shutil
import os


if __name__ == '__main__':
    if os.path.isdir('/tmp/myChromeSession'):
        shutil.rmtree("/tmp/myChromeSession")
    # website = ("http://localhost:8080", 'petclinic')  # petclinic
    # website = ("http://localhost:3000/pagekit/index.php/admin/", 'pagekit')  # pagekit
    website = ("http://localhost:4000", 'trello')  # trello
    # website = ("http://localhost:4000", 'retroboard')  # retroboard
    # website = ("http://localhost:4200", 'splittypie')
    crawler: Crawler = Crawler(website[0], website[1])
    asyncio.get_event_loop().run_until_complete(crawler.start())