from multiprocessing import Pool
import os
import time
import requests
from bs4 import BeautifulSoup
import numpy as np
import typing as tp
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

from constants import FIRSTK_BASE, FIRSTK_TARGET_CATEGORIES

from PIL import Image

BASEURL = "https://1k.by"
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


def get_1k_categories(base_url: str) -> np.ndarray:
    r = requests.get(base_url, headers=HEADERS)
    soup = BeautifulSoup(r.text, features="html.parser")

    needed_links = []
    total_slash_count = base_url.count("/")
    for link in soup.find_all('a'):
        if link.has_attr('href') and "news.1k" not in link['href'] and "review.1k" not in link['href'] and "users.1k" not in link['href']:
            # url = urljoin(before_nth_occurance(link['href'], total_slash_count + 1), "/")
            url: str = link['href']
            if url.endswith('.html'):
                continue
            url = remove_all_parameters(url)
            if (url.startswith('/')):
                url = urljoin(base_url, url)
            needed_links.append(url)

    return np.unique(needed_links).tolist()


def parse_category(category: str) -> np.ndarray:
    r = requests.get(category, headers=HEADERS)
    soup = BeautifulSoup(r.text, features="html.parser")

    domain = "https://" + urlparse(category).netloc

    needed_links = []
    while True:
        for link in soup.find_all('a'):
            if link.has_attr('href'):
                url: str = link['href']
                url = remove_all_parameters(url)
                if (url.startswith('/')):
                    url = urljoin(domain, url)
                if not url.startswith(category) or not url.endswith('.html'):
                    continue
                needed_links.append(url)

        next_link = soup.find_all('a', {'class': 'paging__next'})
        if len(next_link) == 0:
            break
        next_link = next_link[0]
        r = requests.get(urljoin(domain, next_link['href']), headers=HEADERS)
        soup = BeautifulSoup(r.text, features="html.parser")
    print("Done ", category)
    return np.unique(needed_links)


def thread_pool_categories(categories):
    with Pool() as pool:
        results = pool.map(parse_category, categories)
    with open(f"1k_pages.txt", 'wb') as f:
        np.save(f, np.asarray(results))
    return results


def parse_1k_page(page_link: str):
    r = requests.get(page_link, headers=HEADERS)
    soup = BeautifulSoup(r.text, features="html.parser")

    title = soup.find('span', {'class': 'crumbs__current'})
    if title is None:
        return None
    title = title.text
    img = soup.find('img', {'class': 'spec-about__img'})
    file_name = "imgs/" + '|'.join(page_link.split('/')[-3:]).split('.')[0] + ".jpg"
    
    if img is not None:
        src = img['src']
        if not (src.endswith('.jpg') or src.endswith('.jpeg')):
            return None
        r = requests.get(src, stream=True)
        with open(file_name, 'wb') as f:
            for chunk in r:
                f.write(chunk)
        im = Image.open(file_name)
        im = im.resize((224, 224))
        im = im.convert('RGB')
        im.save(file_name)
    else:
        return None
    return title, file_name, page_link


def parse_1k_pages(page_links: tp.List["np.array[str]"]) -> tp.List[tp.Tuple[str, str]]:
    answer = []
    for category in page_links:
        temp = []
        with Pool() as p:
            temp = list(tqdm(p.imap(parse_1k_page, category), total=len(category), position=0, leave=True))
        temp = [t for t in temp if t is not None]
        if 400 < len(temp) < 2000:
            answer.append([t for t in temp if t is not None])

    with open(f"filter_categories_1k.txt", 'wb') as f:
        np.save(f, np.asarray(answer))
    
    return answer


def main():
    targets = []
    len_total = 0
    with open("1k_pages.txt", 'rb') as f:
        t = np.load(f, allow_pickle=True)
        for element in t[1:]:
            if len(element) > 450 and len(element) < 2000 and (len_total < 100000 or any([j in element[0] for j in FIRSTK_TARGET_CATEGORIES])):
                if '/_' in element[0]:
                    continue
                len_total += len(element)
                print(len_total, element[0])
                targets.append(element)
    parse_1k_pages(targets)


if __name__ == "__main__":
    main()
