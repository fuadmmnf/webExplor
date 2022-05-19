def get_current_state(self, info):
    current_url = self.driver.get_current_url()

    # remove parameter in url

    for i in range(0, 10):
        current_url = current_url.replace(str(i), "")

    # add page hash

    def detect_input_information(candidates):
        input_with_value = []

        for candidate_pair in candidates:
            candidate, xpath = candidate_pair.get_node(), candidate_pair.get_xpath()
            if candidate.__contains__("textValue") and len(candidate["textValue"]) > 0:
                input_with_value.append(xpath)
                continue
            if candidate.__contains__("inputValue") and len(candidate["inputValue"]) > 0:
                input_with_value.append(xpath)
                continue

            if candidate.__contains__("inputChecked") and candidate["inputChecked"]:
                input_with_value.append(xpath)
                continue

        # omit option for large scale

        # if candidate.__contains__("optionSelected") and candidate["optionSelected"]:

        # input_with_value.append(xpath)

        # continue

        return "".join(input_with_value)

    def build_state_info(url, candidates, other):
        input = detect_input_information(candidates)
        info["hash"] = other
        info["input"] = input
        info["url"] = url

        final_state = url + other + input

        state = url + other

        self.input_state_to_state[final_state] = state

        info["dfa_state"] = state

        return final_state

    def add_as_new_state(url, info):
        page_source = self.driver.get_page_source()

        document = lxml.html.parse(StringIO(page_source))

        tag_seq = self.get_tags(document)

        string = "".join(tag_seq)

        m = hashlib.md5()

        m.update(string.encode(encoding="utf-8"))

        string_hash = str(m.hexdigest())

        state = build_state_info(url,
                                 info["candidate"],
                                 string_hash)

        self.state_dom[state] = tag_seq

        self.states[state] = True

        if self.url_to_state.__contains__(url):

            self.url_to_state[url].append(state)

        else:

            self.url_to_state[url] = [state]

        states = self.url_to_state[url]

        info["state_index"] = str(states.index(state))

        self.state_to_info[state] = info

        return state

    # calculate page hash

    # m = hashlib.md5()

    # m.update((self.driver.get_page_source() + detect_input_information(info["candidate"])).encode(encoding="utf-8"))

    # page_hash = str(m.hexdigest())

    # info["page_change"] = self.prev_page_hash != page_hash

    # check whether hash network update:

    # has_network, has_restful = trace_network(self.driver.driver)

    # info["has_network"] = has_network

    # info["has_restful"] = has_restful

    # if has_network:

    # info["page_change"] = True

    # self.prev_page_hash = page_hash

    if not self.url_to_state.__contains__(current_url):
        return add_as_new_state(current_url,
                                info)

    states = self.url_to_state[current_url]

    page_source = self.driver.get_page_source()

    document = lxml.html.parse(StringIO(page_source))

    current_seq = self.get_tags(document)

    is_new_state = False

    current_state = None

    max_similar = -1

    for state in states:

        tag_seq = self.state_dom[state]

        current_diff = self.structural_similarity(tag_seq,
                                                  current_seq)

        # if current_diff < 1:

        # print(current_diff)

        # if self.similarity_threshold > current_diff:

        # is_new_state = True

        # break

        if self.similarity_threshold < current_diff:
            max_similar = current_diff

            current_state = state

    if max_similar < self.similarity_threshold:
        return add_as_new_state(current_url,
                                info)

    else:
        states = self.url_to_state[current_url]

    input = detect_input_information(info["candidate"])

    info["input"] = input

    info["url"] = current_url

    self.state_to_info[state] = info

    dfa_state = current_state[:len(current_url) + 32]

    new_state = dfa_state + input

    if not states.__contains__(new_state):
        states.append(new_state)

    info["state_index"] = str(states.index(new_state))

    info["dfa_state"] = dfa_state

    self.state_to_info[new_state] = info

    self.state_dom[new_state] = current_seq

    return new_state

    # return get_state_with_input(current_url, current_seq, info)

    # print(current_url)

    # current_state_string = get_state_with_input(current_url, current_seq, info)

    # if current_state != current_state_string:

    # return add_as_new_state(current_url, info)

    # return current_state_string


def get_tags(self, doc):


    tags = list()

    ignore_elements = set()

    for el in doc.getroot().iter():
        if isinstance(el, lxml.html.HtmlElement):
            tags.append(el.tag)

    # current_path = doc.getpath(el)

    # # filter svg

    # if el.tag == "svg":

    # ignore_elements.add(current_path)

    # continue

    # # skip csrf or token input

    # if el.tag == "input" and "type" in el.attrib and el.attrib["type"] == "hidden":

    # ignore_elements.add(current_path)

    # continue

    # if current_path in ignore_elements:

    # # print("ignore", current_path)

    # continue

    # if isinstance(el.getparent(), lxml.html.HtmlElement):

    # parent = el.getparent()

    # parent_path = doc.getpath(parent)

    # if parent_path in ignore_elements:

    # # print("ignore", current_path)

    # ignore_elements.add(current_path)

    # continue

    # tags.append(el.tag)

    # attri = []

    # for key in el.attrib.keys():

    # if key.find("data-v") > -1:

    # continue

    # if key == "aria-describedby":

    # continue

    # if key == "aria-controls":

    # continue

    # if key == "id":

    # continue

    # # if key in ("aria-label", "type", "class", "name"):

    # # attri += el.attrib[key]

    # attri.append(el.attrib[key])

    # for sibling in el.itersiblings():

    # # continue if not the same tag

    # if sibling.tag != el.tag:

    # continue

    # sibling_attri = []

    # for key in sibling.attrib.keys():

    # if key.find("data-v") > -1:

    # continue

    # if key == "aria-describedby":

    # continue

    # if key == "aria-controls":

    # continue

    # if key == "id":

    # continue

    # # if key in ("aria-label", "type", "class", "name"):

    # sibling_attri.append(sibling.attrib[key])

    # diff = self.structural_similarity(attri, sibling_attri)

    # if diff > self.similarity_threshold:

    # xpath = doc.getpath(sibling)

    # ignore_elements.add(xpath)

    # if len(attri) > 0:

    # tags.append("".join(attri))

        elif isinstance(el, lxml.html.HtmlComment):
            tags.append('comment')

        else:
            raise ValueError('Don\'t know what to do with element: {}'.format(el))

    return tags
