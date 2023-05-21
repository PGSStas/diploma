from multiprocessing import Pool
import os
import time
import requests
import typing as tp

from bs4 import BeautifulSoup
import numpy as np
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from constants import ONLINER_TARGET_CATEGORIES


BASEURL = "https://catalog.onliner.by"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
}


def before_nth_occurance(text: str, count: int, template: str = '/') -> str:
    """
    Return string, that contains all symbols before template string occured
    count times
    """
    t = text.split(template)
    return template.join(t[:min(len(t), count)])


def remove_all_parameters(url: str) -> str:
    """
    Return url without any query parameters
    """
    return urljoin(url, urlparse(url).path)


def get_onliner_categories() -> np.ndarray:
    r = requests.get(BASEURL, headers=HEADERS)
    soup = BeautifulSoup(r.text, features="html.parser")

    needed_links = []
    for link in soup.find_all('a'):
        if link.has_attr('href') and link['href'].startswith('https://catalog.onliner.by/'):
            url = before_nth_occurance(link['href'], 4)
            url = remove_all_parameters(url)
            needed_links.append(url)

    return np.unique(needed_links)


def parse_onliner_category_selenium(category: str):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    driver = webdriver.Firefox(options=options)
    driver.get(category)

    ans = []
    previous = ''
    print(category)
    while True:
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.ID, "schema-pagination")))
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        if previous == driver.current_url:
            break
        previous = driver.current_url

        needed_links = []
        s = set()
        for link in soup.find_all('a'):
            if link.has_attr('href') and link['href'].startswith(category):
                url = remove_all_parameters(link['href'])
                s.add(url)
                url = before_nth_occurance(url, 6)
                if len(url.split('/')) != 6:
                    continue
                needed_links.append(url)

        need_break = True
        for url in needed_links:
            if url + "/prices" in s:
                ans.append(url)
                need_break = False
        if need_break:
            break

        next = driver.find_element(By.ID, 'schema-pagination')
        if next.is_displayed() and next.is_enabled():
            next.click()
    print(f"DONE ON {previous}")
    driver.quit()
    return np.unique(ans)


def thread_pool_categories(categories):
    STEP = os.cpu_count() * 10
    print(STEP)
    for i in range(0, len(categories), STEP):
        print(f"ITERATION #{i}")
        s = categories[i:min(i + STEP, len(categories))]
        with Pool() as pool:
            results = pool.map(parse_onliner_category_selenium, s)
        if os.path.getsize('pages.txt') != 0:
            with open("pages.txt", 'rb') as f:
                results = list(np.load(f, allow_pickle=True)) + results
        with open(f"pages.txt", 'wb') as f:
            np.save(f, np.asarray(results))
        time.sleep(40)
    return results


def parse_onliner_page(page_link: str):
    r = requests.get(page_link, headers=HEADERS)
    soup = BeautifulSoup(r.text, features="html.parser")

    title = soup.find(
        'h1', {'class': 'catalog-masthead__title js-nav-header'}).text.strip()
    # print(title)
    return title, page_link


def parse_onliner_pages(page_links: tp.List["np.array[str]"]) -> tp.List[tp.Tuple[str, str]]:
    answer = []
    for category in page_links:
        with Pool() as p:
            answer.append(list(tqdm(p.imap(parse_onliner_page, category), total=len(category))))

    with open(f"filter_categories_onliner.txt", 'wb') as f:
        np.save(f, np.asarray(answer))
    
    return answer


def main():
    targets = []
    with open("pages.txt", 'rb') as f:
        t = np.load(f, allow_pickle=True)
        for element in t[1:]:
            if len(element) > 0 and any([j in element[0] for j in ONLINER_TARGET_CATEGORIES]):
                print(element[0])
                targets.append(element)
    parse_onliner_pages(targets)


if __name__ == "__main__":
    main()
