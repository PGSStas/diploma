import datetime
import typing as tp
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

import requests

from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import markdownify

from news import Article
from scraper import Scraper
from .utils import transform_date

import json


MAIN_URL = "https://vgtimes.ru"
NEWS_URL = "https://vgtimes.ru/news/"


class VGTimes(Scraper):
    def __init__(self, depth: int = 5) -> None:
        super().__init__()
        self._urls = None
        self._depth = depth

    def parse_page(self, url: str) -> Article:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, features="html.parser")


        # Title
        title_txt = soup.find('h1', {'class': 'news_item_title'})
        if title_txt is None:
            return None
        title = title_txt.text.strip()

        # Date
        date = json.loads(soup.find('script', {'type': 'application/ld+json'}).text)['dateModified']
        dt = datetime.datetime.strptime(date.split('+')[0], "%Y-%m-%dMSK%H:%M:%S")
        date = "{:02}.{:02}.{} {}:{}:{} (Europe/Moscow)".format(
            dt.day, dt.month, dt.year, dt.hour, dt.minute, dt.second)

        # Author
        # author = soup.find(
        #     'a', {'itemprop': 'author'}).text.strip()

        # Text
        text_html = soup.find('div', {'class': 'text_block'})

        paragraphs = []
        for b in text_html.find_all('div', {'class': 'article_block a_text'}, recursive=False):
            for t in b.find_all():
                if t.name in ['script',]:
                    t.extract()
            paragraphs.append(str(b))

        text_answer = markdownify.markdownify("\n".join(paragraphs), bullets=">+-")

        return Article(title, date, "VGTIMES", url, text_answer)

    def parse_pages(self) -> tp.Generator[Article, None, None]:
        for url in tqdm(self._urls, desc="3DNEWS URL PARSER"):
            article = self.parse_page(url)
            if article is not None:
                yield self.parse_page(url)

    def validate_page(self) -> bool:
        pass

    def find_all_urls(self) -> tp.List[str]:
        set_urls = set()
        for index in tqdm(range(self._depth), desc="VGTIMES SCRAPER"):
            page_url = NEWS_URL + f"page/{index + 1}/"

            r = requests.get(page_url)
            soup = BeautifulSoup(r.text, features="html.parser")
            body = soup.find('ul', {'class': 'list-items'})

            for link in body.find_all('li'):
                name = link.find('div', {'class': 'item-name'}).find('a')
                if name.has_attr('href'):
                    url: str = name['href']
                    set_urls.add(urljoin(MAIN_URL, url))

        self._urls = list(set_urls)
        return self._urls
