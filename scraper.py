# https://devhints.io/xpath

import lxml.html as lh
from lxml.etree import Element
from typing import Iterator
import requests

class Website:
    def __init__(self) -> None:
        self._groups = None
    
    @property
    def groups(self) -> [str]:
        if self._groups:
            return self._groups
        else:
            text = requests.get('https://tildes.net/groups').text
            e = lh.fromstring(text)
            
            self._groups = [c.text[1:] for c in e.xpath('//ol[@class="group-list"]/li/a')]
            return self._groups
    
    def get_group(self, name):
        return GroupIter(name)

class GroupIter:
    def __init__(self, name) -> None:
        self.name = name
        self.last_id = None

        self.page = lh.fromstring(
            requests.get(f'https://tildes.net/~{name}').text
        )
        self.post_iter: Iterator[Element] = iter(self.page.xpath('//*[@class="topic-listing"]//article'))

    def __iter__(self):
        return self

    def __next__(self):
        try:
            art = next(self.post_iter)
        except StopIteration:
            self.next_page()
            art = next(self.post_iter)
        
        assert art.attrib['id'].startswith('topic-')
        id = self.last_id = art.attrib['id'][6:]

        return {
            "title": art.xpath('.//*[@class="topic-title"]//a')[0].text,
            "id": id,
            "votes": art.xpath('.//*[@class="topic-voting-votes"]')[0].text,
            "ctime": art.xpath('.//time')[0].attrib['datetime'],
            "author": art.attrib['data-topic-posted-by']
        }
    
    def next_page(self):
        self.page = lh.fromstring(
            requests.get(f'https://tildes.net/~{self.name}?after={self.last_id}').text
        )
        self.post_iter: Iterator[Element] = iter(self.page.xpath('//*[@class="topic-listing"]//article'))

    @property
    def page_len(self) -> int:
        return len(self.page.xpath('//*[@class="topic-listing"]//article'))
    
class Post:
    def __init__(self, group, id) -> None:
        self.group = group
        self.id = id

        self.page = lh.fromstring(
            requests.get(f'https://tildes.net/~{self.group}/{id}/').text
        )

    @property
    def text(self) -> str:
        return self.page.xpath('//article/*[@class="topic-full-text"]')[0].text_content().strip()

    @property
    def title(self) -> str:
        return self.page.xpath('//article/header//h1')[0].text

    @property
    def author(self) -> str:
        return self.page.xpath('//article/header//*[@class="link-user"]')[0].text

    @property
    def ctime(self) -> str:
        return self.page.xpath('//article/header//time')[0].attrib['datetime']

    @property
    def votes(self) -> int:
        return int(self.page.xpath('//*[@class="topic-voting-votes"]')[0].text)

    @property
    def tags(self) -> [str]:
        return [elt.text for elt in self.page.xpath('//*[@class="topic-full-tags"]//a')]

    # Drum roll...
    @property
    def comments(self):
        return [Comment(elt) for elt in self.page.xpath('//*[@id="comments"]/*/article')]

class Comment:  # Wraps an `article` element representing a comment
    def __init__(self, elt) -> None:
        assert elt.tag == 'article'
        self.elt = elt

    @property
    def text(self) -> str:
        return self.elt.xpath('./*[@class="comment-itself"]//*[@class="comment-text"]')[0].text_content().strip()

    @property
    def author(self) -> str:
        return self.elt.xpath('./*[@class="comment-itself"]//*[@class="link-user"]')[0].text

    @property
    def ctime(self) -> str:
        return self.elt.xpath('./*[@class="comment-itself"]//time')[0].attrib['datetime']

    @property
    def votes(self) -> int:
        return int(self.elt.xpath('./*[@class="comment-itself"]//*[@class="comment-votes"]')[0].text.split()[0])  # `15 votes`

    @property
    def replies(self):
        return [Comment(elt) for elt in self.elt.xpath('./*[contains(@class, "comment-tree-replies")]/*/article')]
