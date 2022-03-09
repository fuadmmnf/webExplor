import random
import os
from faker import Faker

from pyppeteer.element_handle import ElementHandle
from hashlib import md5


class Action(ElementHandle):
    def __init__(self, element_handle: ElementHandle, outer_html: str, page_url: str):
        super().__init__(element_handle._context, element_handle._client, element_handle._remoteObject,
                         element_handle._page, element_handle._frameManager)
        self.outer_html = outer_html
        self.page_url = page_url
        # self.g_iid = -math.log(-math.log(numpy.random.uniform(0.0, 1.0)))
        m = md5()
        for s in tuple(self.outer_html):  # removed url from encoding for duplicate removal
            m.update(s.encode())
        self._hash = int(m.hexdigest(), 16)

    # def __str__(self) -> str:
    #     return f'{self.page_url} -> {self.outer_html}'
    #
    def __str__(self) -> str:
        return f'{self._hash} -> {self.outer_html.split(">")[0]}'

    def __repr__(self) -> str:
        return f'{self._hash} -> {self.outer_html.split(">")[0]}'

    def __hash__(self):
        return self._hash

    def __eq__(self, other: object) -> bool:
        return self.__hash__() == other.__hash__()

    def __ne__(self, other):
        return not (self == other)

    def interact(self):
        tag_name = await (await self.getProperty('tagName')).jsonValue()
        # print('tag name: ' + tag_name)
        if tag_name == 'A':
            # for self page navigation
            link = await (await self.getProperty('href')).jsonValue()
            # if link == 'javascript:void(0)':
            #     self.invalid_actions[valid_action] = True
            #     continue
            #
            # await page.goto(link.__str__())
            #######
            await self.click()

        elif tag_name == 'BUTTON':
            await self.click()
        elif tag_name == 'SELECT':
            options = await self.querySelectorAll('option')
            if len(options) > 0:
                await self.querySelectorEval(
                    'option:nth-child(' + str(random.randint(1, len(options))) + ')',
                    '(node => node.selected = true)')
        elif tag_name == 'INPUT':
            faker: Faker = Faker()
            input_type = await (await self.getProperty('type')).jsonValue()
            # print('input type: ' + input_type)
            if input_type == 'button':
                await self.click()
            elif input_type == 'checkbox':
                await self.click()
            elif input_type == 'color':
                # not working
                # r = lambda: random.randint(0, 255)
                # color = '#%02X%02X%02X' % (r(), r(), r())
                # print(color)
                # await valid_action.type(color)
                pass

            elif input_type == 'date':
                await self.type(faker.date(pattern='%m-%d-%Y'))
            elif input_type == 'datetime-local':
                await self.type(faker.date_time().strftime('%Y-%m-%dT%H:%M%p'))
            elif input_type == 'email':
                await self.type(faker.email())
            elif input_type == 'file':
                file_path = random.choice(os.listdir(os.path.join(os.path.dirname(__file__), 'res/file_types')))
                await self.uploadFile(file_path)
            elif input_type == 'hidden':
                pass
            elif input_type == 'image':
                await self.click()
            elif input_type == 'month':
                await self.type(faker.date_time().strftime('%Y-%m'))
            elif input_type == 'number':
                await self.type(str(random.random() * random.randrange(1000)))
            elif input_type == 'password':
                await self.type(faker.password())
            elif input_type == 'radio':
                await self.click()
            elif input_type == 'range':
                # not working
                # rand_range = str(random.randint(0, 100))
                # print(rand_range)
                # await valid_action.type()
                pass
            elif input_type == 'reset':
                await self.click()
            elif input_type == 'search':  # potential
                await self.type(faker.text())
            elif input_type == 'submit':
                await self.click()
            elif input_type == 'tel':
                await self.type(faker.phone_number())
            elif input_type == 'text':
                await self.type(faker.text())
            elif input_type == 'time':
                await self.type(faker.date_time().strftime('%H:%M%p'))
            elif input_type == 'url':
                await self.type(faker.url())
            elif input_type == 'week':
                await self.type(faker.date_time().strftime('%Y-W%U'))
