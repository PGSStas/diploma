import time
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


MAIN_URL = "https://dtf.ru/popular"


class DTFScraper(Scraper):
    def __init__(self, depth: int = 5) -> None:
        super().__init__()
        self._options = Options()
        self._options.add_argument("--headless")
        self._options.add_argument("--log-level=3")
        self._driver = webdriver.Firefox(options=self._options)
        self._driver.get(MAIN_URL)

        self._urls = None
        self._depth = depth

    def parse_page(self, url: str) -> Article:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, features="html.parser")

        # Title
        title = soup.find('h1', {'class': 'content-title'}).find(string=True, recursive=False).strip() + " " + \
            soup.find('span', {'class': 'content-title__last-word'}
                      ).find(string=True, recursive=False).strip()

        # Date
        date = soup.find('time', {'class': 'time'})['title']

        # Author
        author = soup.find(
            'a', {'class': 'content-header-author__name'}).text.strip()

        # Text
        text_html = soup.find('div', {'class': 'content content--full'})

        paragraphs = []
        for t in text_html.find_all(['div', 'figure'], {'class': 'l-island-a'}, recursive=False):
            if len(t['class']) == 1 and t['class'][0] in ['l-island-a']:
                paragraphs.append(markdownify.markdownify(
                    str(t),
                    heading_style='ATX', bullets=">+-"
                ).strip())

        text_answer = "\n\n".join(paragraphs[:-1])

        return Article(title, date, author, url, text_answer)

    def parse_pages(self) -> tp.Generator[Article, None, None]:
        for url in tqdm(self._urls, desc="DTF URL PARSER"):
            article = self.parse_page(url)
            if article is not None:
                yield self.parse_page(url)

    def validate_page(self) -> bool:
        pass

    def find_all_urls(self) -> tp.List[str]:
        for _ in tqdm(range(self._depth), desc="DTF SCRAPER"):
            WebDriverWait(self._driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "news-widget__load-more.t-link")))

            next = self._driver.find_element(
                By.CLASS_NAME, "news-widget__load-more.t-link")
            
            if next.is_displayed() and next.is_enabled():
                self._driver.execute_script("arguments[0].click();", next)
                # next.click()
            WebDriverWait(self._driver, 0.2)


        soup = BeautifulSoup(self._driver.page_source, features="html.parser")
        link_div = soup.find('div', {'class': 'news-widget__content__inner'})

        set_urls = set()
        for link in link_div.find_all('a'):
            if link.has_attr('href'):
                url: str = link['href']
                set_urls.add(urljoin(url, urlparse(url).path))
        self._urls = list(set_urls)
        self._driver.quit()
