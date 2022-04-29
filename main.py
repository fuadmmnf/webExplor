import asyncio
from crawler import Crawler
import shutil
import os
import sys, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--project', help='Mention project code, for example: trello')
args = parser.parse_args()


async def main():
    # if os.path.isdir('/tmp/myChromeSession'):
    #     shutil.rmtree("/tmp/myChromeSession")
    #

    websites = [
        ("http://localhost:8080", 'petclinic'), ("http://localhost:3000/pagekit/index.php/admin/", 'pagekit'),
        ("http://localhost:4000", 'trello'),
        ("http://localhost:4001", 'retroboard'), ("http://localhost:4200", 'splittypie'),
        ("http://localhost:3001", 'dimeshift')
    ]

    if args.project is not None:
        tups = [item for item in websites if item[1] == args.project]
        if len(tups) == 0:
            print('Invalid project code')
            sys.exit(1)
        website = tups[0]
    else:
        website = websites[2]

    crawler: Crawler = Crawler(website[0], website[1])
    loop = asyncio.get_event_loop()
    loop.run_until_complete(await crawler.start())


if __name__ == '__main__':
    asyncio.run(main())
    sys.exit(0)
