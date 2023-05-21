import datetime
import requests

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tqdm import tqdm

from implementations import (
    DTFScraper,
    VCScraper,
    IXBTScraper,
    OnlinerScraper,
    DevbyScraper,
    ThreeDNews,
    VGTimes
)

import numpy as np

import psycopg2 as pg

import os

from scraper import Scraper


PG_PASSWORD = os.environ['PG_PASSWORD']


def create_cursor():
    try:
        conn = pg.connect(
            host='localhost',
            database='postgres',
            port=5555,
            user='admin',
            password=PG_PASSWORD
        )

        cursor = conn.cursor()
        print("Connection established.")

    except Exception as err:
        print("Something went wrong.")
        print(err)

    return conn, cursor


def filter_scraper(scraper, found_urls):
    filter_len = len(scraper._urls)
    scraper._urls = list(filter(lambda x: x not in found_urls, scraper._urls))
    print(f"FILTERED {filter_len - len(scraper._urls)} URLS")


def parse_and_add(conn, cursor, scraper: Scraper, name: str) -> None:
    scraper.find_all_urls()
    cursor.execute(
        'SELECT url FROM articles WHERE origin_website = %s', (name,))
    already_download_urls = [i[0] for i in cursor.fetchall()]
    filter_scraper(scraper, already_download_urls)

    for page in scraper.parse_pages():
        cursor.execute('''INSERT INTO articles (origin_website, title, date, author, url, article_text, ts) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)''', (name, page.title, page.date, page.author, page.url, page.text, date_to_ts(page.date)))
        conn.commit()


def date_to_ts(date: str) -> int:
    d = date.split()
    days = d[0].split('.')
    hours = d[1].split(':')
    date_time = datetime.datetime(int(days[2]), int(days[1]), int(
        days[0]), int(hours[0]), int(hours[1]), int(hours[2]))
    return int(date_time.timestamp())


def update_train_data(conn, cursor):
    cursor.execute(
        'SELECT id, origin_website, article_text, title FROM articles')
    for t in tqdm(cursor.fetchall(), "UPDATE TRAIN DATA"):
        from bs4 import BeautifulSoup
        from markdown import markdown
        import re

        def markdown_to_text(markdown_string):
            """ Converts a markdown string to plaintext """

            # md -> html -> text since BeautifulSoup can extract text cleanly
            html = markdown(markdown_string)

            # remove code snippets
            html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
            html = re.sub(r'<code>(.*?)</code >', ' ', html)

            # extract text
            soup = BeautifulSoup(html, "html.parser")
            text = ''.join(soup.findAll(string=True))

            return text

        output_path = os.path.join('/root/diploma/news_data/our_data_txt/', str(t[1]) + "_" + str(t[0]) + ".txt")
        with open(output_path, 'w') as f:
            f.write(t[3] + "\n\n")
            f.write(markdown_to_text(t[2]))


def update_news_host(conn, cursor, scraper: Scraper, type: str):
    cursor.execute(
        'SELECT id, url FROM articles WHERE origin_website = %s', (type, ))

    for entry in tqdm(cursor.fetchall(), f"UPDATE {type}"):
        article = scraper.parse_page(entry[1])

        cursor.execute('UPDATE articles SET title = %s, article_text = %s WHERE id = %s',
                       (article.title, article.text, entry[0]))
        conn.commit()


def main():
    conn, cursor = create_cursor()
    parse_and_add(conn, cursor, DTFScraper(10), "DTF")
    parse_and_add(conn, cursor, VCScraper(10), "VC.RU")
    parse_and_add(conn, cursor, IXBTScraper(5), "IXBT")
    parse_and_add(conn, cursor, OnlinerScraper(5), "ONLINER")
    parse_and_add(conn, cursor, DevbyScraper(15), "DEVBY")
    parse_and_add(conn, cursor, ThreeDNews(30), "3DNEWS")
    parse_and_add(conn, cursor, VGTimes(15), "VGTimes")
    update_train_data(conn, cursor)


if __name__ == '__main__':
    main()
