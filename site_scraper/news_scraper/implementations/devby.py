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


MAIN_URL = "https://devby.io"
NEWS_URL = "https://devby.io/news"


class DevbyScraper(Scraper):
    def __init__(self, depth: int = 5) -> None:
        super().__init__()
        self._urls = None
        self._depth = depth

    def parse_page(self, url: str) -> Article:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, features="html.parser")

        # Title
        title = soup.find('div', {'class': 'article__container'}).find(
            'h1', recursive=False).text.strip()

        # Date
        date = transform_date(
            soup.find('span', {'id': 'publishedAt'}).text.strip().replace(',', ' t'))

        # Author
        author = soup.find(
            'span', {'class': 'article-meta__item'}).text.strip()

        # Text
        text_html = soup.find(
            'div', {'data-article-global-incut-target': 'content'})
        bodies = [b for b in text_html.findChildren(
            recursive=False) if len(b.attrs) == 0]

        paragraphs = []
        for b in bodies:
            paragraphs.append(str(b))

        text_answer = markdownify.markdownify("\n".join(paragraphs), bullets=">+-")

        return Article(title, date, author, url, text_answer)

    def parse_pages(self) -> tp.Generator[Article, None, None]:
        for url in tqdm(self._urls, desc="DEVBY URL PARSER"):
            article = self.parse_page(url)
            if article is not None:
                yield self.parse_page(url)

    def validate_page(self) -> bool:
        pass

    def find_all_urls(self) -> tp.List[str]:
        set_urls = set()
        for index in tqdm(range(self._depth), desc="DEVBY SCRAPER"):
            page_url = NEWS_URL + f"?page={index + 1}"

            r = requests.get(page_url)
            soup = BeautifulSoup(r.text, features="html.parser")

            for link in soup.find_all('a', {'class': 'card__link'}):
                if link.has_attr('href') and link['href'].startswith("/news/"):
                    url: str = link['href']
                    set_urls.add(urljoin(MAIN_URL, url))

        self._urls = list(set_urls)
        return self._urls
