import typing as tp
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

import requests

import datetime

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


MAIN_URL = "https://www.ixbt.com/news/"
NEWS_URL = "https://www.ixbt.com/news/"


class IXBTScraper(Scraper):
    def __init__(self, depth: int = 5) -> None:
        super().__init__()
        self._urls = None
        self._depth = depth

    def parse_page(self, url: str) -> Article:
        # print(url)
        r = requests.get(url)
        soup = BeautifulSoup(r.text, features="html.parser")

        # Title
        title_html = soup.find('meta', {'itemprop': 'headline'})
        if title_html is None:
            return None
        title = title_html['content'].strip()

        # Date
        date_html = soup.find('p', {'class': 'date'})
        if date_html is None:
            return None
        date = transform_date(date_html.text.strip())

        # Author
        author = soup.find('span', {'itemprop': 'name'}).text.strip()

        # Text
        text_html = soup.find('div', {'class': 'b-article__content'})

        text_answer = ""
        for t in text_html.find_all('p'):
            text_answer += markdownify.markdownify(
                str(t),
                heading_style='ATX', bullets=">+-"
            ).strip() + "\n"

        return Article(title, date, author, url, text_answer)

    def parse_pages(self) -> tp.Generator[Article, None, None]:
        for url in tqdm(self._urls, desc="IXBT URL PARSER"):
            article = self.parse_page(url)
            if article is not None:
                yield self.parse_page(url)

    def validate_page(self) -> bool:
        pass

    def find_all_urls(self) -> tp.List[str]:
        now = datetime.datetime.now()

        set_urls = set()
        for _ in tqdm(range(self._depth), desc="IXBT SCRAPER"):
            day_url = NEWS_URL + \
                "/{}/{:02}/{:02}/".format(now.year, now.month, now.day)

            r = requests.get(day_url)
            soup = BeautifulSoup(r.text, features="html.parser")
            links = soup.find_all('a', {'class': 'item__text--title'})
            for link in links:
                if link.has_attr('href'):
                    set_urls.add(urljoin(MAIN_URL, link['href']))

            now -= datetime.timedelta(days=1)

        self._urls = list(set_urls)
        return self._urls
