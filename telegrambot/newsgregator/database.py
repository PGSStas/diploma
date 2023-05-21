from site_scraper.news_scraper.news import Article
import typing as tp

from datetime import datetime, timedelta
import psycopg2 as pg

import sys
sys.path.append('/root/diploma')


class Database:
    def __init__(self, pg_password: str) -> None:
        try:
            conn = pg.connect(
                host='localhost',
                database='postgres',
                port=5555,
                user='admin',
                password=pg_password
            )

            cursor = conn.cursor()
            print("Connection established.")

        except Exception as err:
            print("Something went wrong.")
            print(err)

        self.connection = conn
        self.cursor = cursor

    def get_cluster_titles(self) -> tp.List[tp.Tuple[int, int, int, str, int]]:
        self.cursor.execute('''
            SELECT
                A.cluster_id as cluster_id,
                A.title_article as title_article,
                B.min_ts as ts,
                C.title as title,
                A.cnt as cnt
            FROM (
                    SELECT
                        A.cluster_id as cluster_id,
                        MIN(A.title_article) as title_article,
                        COUNT(*) as number_of_websites,
                        SUM(A.cnt) as cnt
                    FROM (
                            SELECT
                                cluster_id as cluster_id,
                                MIN(article_id) as title_article,
                                COUNT(*) as cnt
                            FROM cluster_entry as A
                                INNER JOIN articles as B ON A.article_id = B.id
                            GROUP BY
                                A.cluster_id,
                                B.origin_website
                        ) AS A
                    GROUP BY cluster_id
                ) as A
                INNER JOIN clusters as B ON A.cluster_id = B.id
                INNER JOIN articles as C ON A.title_article = C.id
            WHERE B.avg_ts > %s
            ORDER BY A.cnt * A.number_of_websites DESC, B.min_ts DESC;
        ''', (int((datetime.now() - timedelta(hours=36)).timestamp()), ))
        return self.cursor.fetchall()

    def get_cluster_by_id(self, id: int) -> tp.List[tp.Tuple[int, str, Article]]:
        self.cursor.execute('''
        SELECT B.*
        FROM (
                SELECT article_id
                FROM cluster_entry
                WHERE
                    cluster_id = %s
            ) as A
            INNER JOIN articles as B ON A.article_id = B.id;
        ''', (id, ))

        articles = []
        for entry in self.cursor.fetchall():
            articles.append((entry[0], entry[1], Article(
                title=entry[2], date=entry[3], author=entry[4], url=entry[5], text=entry[6])))
        return articles

