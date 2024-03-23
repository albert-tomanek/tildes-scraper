# https://devhints.io/xpath

import lxml.html as lh
from lxml.etree import Element
from typing import Iterator
import requests
import datetime

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
    
    def get_group(self, name=None):
        return GroupIter(name)

class GroupIter:
    def __init__(self, name=None) -> None:
        self.name = name
        self.last_id = None

        self.page = lh.fromstring(
            requests.get(f'https://tildes.net/~{name}' if name else 'https://tildes.net/').text
        )
        self.post_iter: Iterator[Element] = iter(self.page.xpath('//*[@class="topic-listing"]//article'))

    def __iter__(self):
        return self

    def __next__(self):
        try:
            print(self.name)
            art = next(self.post_iter)
        except StopIteration:
            self.next_page()
            art = next(self.post_iter)
        
        assert art.attrib['id'].startswith('topic-')
        id = self.last_id = art.attrib['id'][6:]

        item = PostItem(self)
        item.title = art.xpath('.//*[@class="topic-title"]//a')[0].text
        item.url = art.xpath('.//*[@class="topic-title"]//a')[0].attrib['href']
        item.id = id
        item.votes = art.xpath('.//*[@class="topic-voting-votes"]')[0].text
        item.ctime = datetime.datetime.fromisoformat(art.xpath('.//time')[0].attrib['datetime'])
        item.author = art.attrib['data-topic-posted-by']
        item.ncomments = int(art.xpath('.//*[@class="topic-info-comments"]//a')[0].text_content().split()[0])
        comments_link = art.xpath('.//*[@class="topic-info-comments"]//a')[0].attrib['href']
        item.is_selfpost = (item.url == comments_link)

        return item
    
    def next_page(self):
        self.page = lh.fromstring(
            requests.get(f'https://tildes.net/~{self.name}?after={self.last_id}').text
        )
        self.post_iter: Iterator[Element] = iter(self.page.xpath('//*[@class="topic-listing"]//article'))

    @property
    def page_len(self) -> int:
        return len(self.page.xpath('//*[@class="topic-listing"]//article'))

class PostItem:
    def __init__(self, grp) -> None:
        self.grp = grp

        self.title = None
        self.url = None
        self.id = None
        self.votes = None
        self.ctime = None
        self.author = None
        self.ncomments = None
        self.is_selfpost = None

    def get_post(self):
        return Post(self.grp.name, self.id)

class Post:
    def __init__(self, group, id) -> None:
        self.group = group
        self.id = id

        self.page = lh.fromstring(
            requests.get(f'https://tildes.net/~{self.group}/{id}/').text
        )

    @property
    def text(self) -> str:
        try:
            return self.page.xpath('//article/*[@class="topic-full-text"]')[0].text_content().strip()
        except IndexError:
            return None

    @property
    def url(self) -> str:
        try:
            return self.page.xpath('//article/*[@class="topic-full-link"]//a')[0].attrib['href']
        except IndexError:
            return None

    @property
    def title(self) -> str:
        return self.page.xpath('//article/header//h1')[0].text

    @property
    def author(self) -> str:
        return self.page.xpath('//article/header//*[@class="link-user"]')[0].text

    @property
    def ctime(self):
        return datetime.datetime.fromisoformat(self.page.xpath('//article/header//time')[0].attrib['datetime'])

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

class Comment:
    def __init__(self, elt) -> None:
        self.elt = elt  # The `article` HTML element that this comment wraps
        assert elt.tag == 'article'

    @property
    def text(self) -> str:
        return self.elt.xpath('./*[@class="comment-itself"]//*[@class="comment-text"]')[0].text_content().strip()

    @property
    def author(self) -> str:
        return self.elt.xpath('./*[@class="comment-itself"]//*[@class="link-user"]')[0].text

    @property
    def ctime(self) -> str:
        return datetime.datetime.fromisoformat(self.elt.xpath('./*[@class="comment-itself"]//time')[0].attrib['datetime'])

    @property
    def votes(self) -> int:
        return int(self.elt.xpath('./*[@class="comment-itself"]//*[@class="comment-votes"]')[0].text.split()[0])  # `15 votes`
    
    @property
    def is_op(self) -> bool:
        return ('is-comment-by-op' in self.elt.attrib['class'].split())

    @property
    def is_exemplary(self) -> bool:
        return ('is-comment-exemplary' in self.elt.attrib['class'].split())

    @property
    def replies(self):
        return [Comment(elt) for elt in self.elt.xpath('./*[contains(@class, "comment-tree-replies")]/*/article')]
