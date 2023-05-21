import sys
sys.path.append('/root/diploma')

from site_scraper.news_scraper.news import Article
import typing as tp

from datetime import datetime, timedelta
import psycopg2 as pg


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
                        cluster_id as cluster_id,
                        MIN(article_id) as title_article,
                        COUNT(*) as cnt
                    FROM cluster_entry
                    GROUP BY
                        cluster_id
                ) as A
                INNER JOIN clusters as B ON A.cluster_id = B.id
                INNER JOIN articles as C ON A.title_article = C.id
            WHERE B.min_ts > %s
            ORDER BY A.cnt DESC, B.min_ts DESC;
        ''', (int((datetime.now() - timedelta(days=14)).timestamp()), ))
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

    # def get_film_stat(self, chat_id: str):
    #     cursor = self.connection.cursor().execute(
    #         f"SELECT title, COUNT(*) FROM history WHERE chat_id = {chat_id} GROUP BY chat_id, title")

    #     return cursor.fetchall()

    # def get_history(self, chat_id: str):
    #     cursor = self.connection.cursor().execute(
    #         f"SELECT query FROM history WHERE chat_id = {chat_id}")

    #     return cursor.fetchall()
