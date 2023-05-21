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


MAIN_URL = "https://tech.onliner.by"


class OnlinerScraper(Scraper):
    def __init__(self, depth: int = 5) -> None:
        super().__init__()
        self._urls = None
        self._depth = depth

    def parse_page(self, url: str) -> Article:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, features="html.parser")

        # Title
        title = soup.find('div', {'class': 'news-header__title'}).text.strip()

        # Date
        date = transform_date(
            soup.find('div', {'class': 'news-header__time'}).text.strip())

        # Author
        author = soup.find(
            'div', {'class': 'news-header__author news-helpers_hide_mobile'}).text.strip()

        # Text
        text_html = soup.find('div', {'class': 'news-text'})

        paragraphs = []
        for t in text_html.findAll(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'hr'])[1:]:
            if 'Конец статьи для измерения' in str(t):
                epilogue = str(t).split('<div id="news-text-end"></div>', 1)
                if epilogue is not None and len(epilogue) > 0:
                    paragraphs.append(epilogue[0] + "</p>")
                break
            if not t.has_attr('style'):
                paragraphs.append(str(t))

        text_answer = markdownify.markdownify("\n".join(paragraphs), bullets=">+-")

        return Article(title, date, author, url, text_answer)

    def parse_pages(self) -> tp.Generator[Article, None, None]:
        for url in tqdm(self._urls, desc="ONLINER URL PARSER"):
            article = self.parse_page(url)
            if article is not None:
                yield self.parse_page(url)

    def validate_page(self) -> bool:
        pass

    def find_all_urls(self) -> tp.List[str]:
        now = datetime.datetime.now()

        set_urls = set()
        for _ in tqdm(range(self._depth), desc="ONLINER SCRAPER"):
            day_url = MAIN_URL + \
                "/{}/{:02}/{:02}/".format(now.year, now.month, now.day)
            now -= datetime.timedelta(days=1)

            r = requests.get(day_url)
            soup = BeautifulSoup(r.text, features="html.parser")
            link_div = soup.find('div', {'class': 'news-tidings__list'})

            if link_div is None:
                continue

            for link in link_div.find_all('div', {'class': 'news-tidings__item'}, recursive=False):
                if link.has_attr('data-post-date'):
                    url: str = link.find('a')['href']
                    set_urls.add(urljoin(MAIN_URL, url))

        self._urls = list(set_urls)
        return self._urls
