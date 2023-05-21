import glob
import os
import re
from datetime import datetime, timedelta

import click
import nltk
import numpy as np
import psycopg2 as pg
import sklearn
import spacy
import torch
from bs4 import BeautifulSoup
from joblib import dump, load
from markdown import markdown
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer, XLMRobertaTokenizerFast

PG_PASSWORD = os.environ['PG_PASSWORD']
nltk.download('stopwords')
STOP_WORDS = set(nltk.corpus.stopwords.words('russian'))
NLP = spacy.load('ru_core_news_sm')
BATCH_SIZE = 16



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


def lemmatize(text: str) -> str:
    # text = PATTERN.sub('', text)
    text = " ".join([token.lemma_ for token in NLP(text)
                    if token.lemma_ not in STOP_WORDS])
    return text


def tfidf_vectorize(data, retrain):
    if retrain:
        nltk.download('stopwords')

        news_folder = '/root/diploma/news_data/our_data_txt/'
        filenames = list(glob.glob(news_folder + '**/*.txt', recursive=True))

        vectorizer = TfidfVectorizer(
            input="filename",
            preprocessor=lemmatize,
            min_df=2,
            max_df=0.9
        )
        articles = vectorizer.fit_transform(tqdm(filenames, "TFIDF TRAIN"))
        dump(vectorizer, 'latest_vectorizer.model')
        pca = PCA(n_components=300, svd_solver='auto')
        reduced_data = pca.fit_transform(articles.toarray())
        dump(pca, 'latest_pca.model')

    vectorizer: TfidfVectorizer = load('latest_vectorizer.model')
    pca: PCA = load('latest_pca.model')
    vectorizer.input = "content"

    article_vectors = vectorizer.transform(tqdm(data))
    reduced_article_vectors = pca.transform(article_vectors.toarray())

    return reduced_article_vectors


# Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    # First element of model_output contains all token embeddings
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(
        -1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask


def bert_vectorize(data, model_version):
    # Load AutoModel from huggingface model repository
    tokenizer = AutoTokenizer.from_pretrained(model_version)
    model = AutoModel.from_pretrained(model_version)

    ans = []
    for batch in tqdm(range((len(data) + BATCH_SIZE - 1) // BATCH_SIZE), "BATCH PROCESS"):
        sentences = data[batch * BATCH_SIZE:min((batch + 1) * BATCH_SIZE, len(data))]
        # Tokenize sentences
        encoded_input = tokenizer(
            sentences, padding=True, truncation=True, return_tensors='pt')

        # Compute token embeddings
        with torch.no_grad():
            model_output = model(**encoded_input)

        # Perform pooling. In this case, mean pooling
        sentence_embeddings = mean_pooling(
            model_output, encoded_input['attention_mask'])

        ans += sentence_embeddings.tolist()

    print(len(ans))
    return ans


@click.command()
@click.option('--retrain', '-r', is_flag=True)
def main(retrain):

    ts = (datetime.now() - timedelta(hours=48)).timestamp()

    conn, cursor = create_cursor()

    # Step 1. Get all news for last 48 hours

    cursor.execute(
        "SELECT id, title, article_text, origin_website, ts FROM articles WHERE ts > %s", (int(ts), ))
    ids, titles, texts, sources, ts = zip(*cursor.fetchall())
    normal_texts = list(map(markdown_to_text, texts))
    title_with_texts = [titles[i] + "\n\n" + normal_texts[i]
                        for i in range(len(titles))]
    ids = np.asarray(ids)
    sources = np.asarray(sources)
    titles = np.asarray(titles)
    ts = np.asarray(ts)

    # Step 2. Recieve vectors

    # reduced_article_vectors = tfidf_vectorize(title_with_texts, retrain)
    reduced_article_vectors = bert_vectorize(
        title_with_texts, 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

    # Step 3. Clusterization

    dbscan = AgglomerativeClustering(
        affinity='cosine', distance_threshold=0.19, linkage='complete', n_clusters=None)
    predicted = dbscan.fit_predict(reduced_article_vectors)

    # Step 4. Print clusters

    lens = []
    alone_titles = []
    sm = 0
    for t in np.unique(predicted):
        l = len(ids[predicted == t])
        if l > 1:
            lens.append((t, l))
            sm += l
            print("FOR ", t, ":", tuple(ids[predicted == t]), " FROM ", tuple(
                np.unique(sources[predicted == t])))
            print(" -------------------------- ")
            print(titles[predicted == t])
            print("============================================")
        else:
            alone_titles += list(titles[predicted == t])
    print("SUM:", sm)

    # Step 5. Put them into table

    for t in np.unique(predicted):
        l = len(ids[predicted == t])
        if l == 1:
            continue
        cluster_ids = tuple(ids[predicted == t].tolist())

        cursor.execute(
            "SELECT id, cluster_id, article_id FROM cluster_entry WHERE article_id IN %s", (cluster_ids, ))
        articles = list(cursor.fetchall())
        print(articles)

        cluster_id = -1
        found_article_ids = []

        if len(articles) == 0:
            cursor.execute('''INSERT INTO clusters (min_ts) 
                            VALUES (%s) RETURNING id''', (int(np.min(ts[predicted == t])), ))
            cluster_id = cursor.fetchone()[0]
            conn.commit()
        else:
            _, found_cluster_ids, found_article_ids = zip(*articles)
            if len(np.unique(found_cluster_ids)) > 1:
                print("Cant add to two clusters!")
                continue
            else:
                cluster_id = int(np.unique(found_cluster_ids)[0])

        for article_id in cluster_ids:
            if article_id in found_article_ids:
                continue
            cursor.execute('''INSERT INTO cluster_entry (cluster_id, article_id) 
                            VALUES (%s, %s)''', (int(cluster_id), int(article_id)))
            conn.commit()

    # Step 6. Update TS

    cursor.execute('''
    UPDATE clusters AS cl
    SET 
        max_ts = A.max_ts,
        min_ts = A.min_ts,
        avg_ts = A.avg_ts
    FROM (
            SELECT
                A.cluster_id as id,
                MIN(B.ts) as min_ts,
                MAX(B.ts) as max_ts,
                CAST(AVG(B.ts) as INT) as avg_ts
            FROM cluster_entry as A
                INNER JOIN articles as B ON A.article_id = B.id
            GROUP BY
                cluster_id
        ) as A
    WHERE cl.id = A.id;
    ''')
    conn.commit()


if __name__ == '__main__':
    main()
