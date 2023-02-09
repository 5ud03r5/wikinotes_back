from db import models, schemas
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from stop_words import get_stop_words
import numpy as np
import re
from db import models
from sqlalchemy.orm import joinedload

stop_words = get_stop_words('polish')
stop_words_en = get_stop_words('english')
stop_words += stop_words_en
stop_words += ['img', 'image', 'px', 'style', 'class', 'src', 'height', 'width', 'nbsp',
               'ckeditor', 'sie', 'wykonal', 'pomoglo', 'png', 'odpalic', 'pozniej', 'profilaktycznie', 'komus', 'moze', 'przyda', 'wyskoczyl'
               'wyszlo', 'opcja', 'no', 'wejsc', 'potem', 'kliknac', 'kiedys', 'guzik', 'ze', 'mowil', 'zrobić', 'bylem', 'wszedlem', 'chyba',
               'br', 'tej', 'trzeba', 'tylko', 'gt', 'wersji', 'wiec', 'zauwazylem', 'miesiac', 'obserwowac', 'odpaleniu', 'przyjac', 'raz', 'starych',
               'ktory', 'wyklikalem', 'wyskoczyl', 'zrobilem', 'you', 'wyszlo', 'wyskoczyl', 'taka', 'utworzylem', 'dajcie', 'jezeli', 'jakie', 'jeżeli',
               'przez', 'gdy', 'ustalic', 'dziala', 'chcialem', 'zadzialalo', 'zadziałało', 'momencie', 'moment', 'napotkalem', 'zrobic', 'zwroci', 'wykonuje',
               'znac', 'wartosci', 'calej', 'lezy', 'moglem', 'widze', 'był', 'nowy', 'nowych', 'bedziecie', 'mieli', 'next', 'ustawien', 'zielony', 'ostatnio']


def siem_subword_tokenizer(tokenizer):
    new_tokenizer = []
    words = ['esm', 'tooling', 'elm', 'tool', 'erc', 'els', 'esl', 'task', 'problem',
             'usuwa', 'alarm', 'proces', 'rozwiaz', 'ustaw', 'zalog', 'log', 'klik', 'issue', 'manage']
    for word in tokenizer:
        found = False
        if word in words:
            new_tokenizer += [word]
            found = True
        else:
            for item in words:
                if word.startswith(item) and word != item:
                    word = item
                    if word in tokenizer or word in new_tokenizer:
                        found = True
                        break
                    else:
                        new_tokenizer += [word]
                        found = True
                        break
        if found == False:
            new_tokenizer += [word]
    return new_tokenizer


def compare_arts(article_id, db):

    article = db.query(models.Article).options(joinedload(models.Article.tags), joinedload(
        models.Article.comment)).filter(models.Article.id == article_id).first()
    articles = db.query(models.Article).options(joinedload(
        models.Article.tags), joinedload(models.Article.comment)).all()
    article_text = [article.text, article.title]

    try:
        vect = CountVectorizer(
            token_pattern=r"(?u)[A-Za-zżźćńółęąśŻŹĆĄŚĘŁÓŃ][A-Za-z0-9żźćńółęąśŻŹĆĄŚĘŁÓŃ]+", stop_words=stop_words, analyzer='word')
        vect.fit(article_text)
        article_text = siem_subword_tokenizer(vect.get_feature_names_out())

    except ValueError:
        context = []

        return context

    def compute_cosine_similarity(text_1, text_2):
        list_text = [str(text_1), str(text_2)]
        vectorizer = TfidfVectorizer(stop_words=stop_words)

        vectorizer.fit_transform(list_text)
        tfidf_text1, tfidf_text2 = vectorizer.transform(
            [list_text[0]]), vectorizer.transform([list_text[1]])

        cs_score = cosine_similarity(tfidf_text1, tfidf_text2)

        return np.round(cs_score[0][0], 2)

    similar_articles = []
    for item in articles:

        try:
            vect = CountVectorizer(
                token_pattern=r"(?u)[A-Za-zżźćńółęąśŻŹĆĄŚĘŁÓŃ][A-Za-z0-9żźćńółęąśŻŹĆĄŚĘŁÓŃ]+", stop_words=stop_words, analyzer='word')
            item_text = [item.text, item.title]
            vect.fit(item_text)
            item_text = siem_subword_tokenizer(vect.get_feature_names_out())
            value = compute_cosine_similarity(article_text, item_text)
            print(item_text, value)
            if value > 0.3 and item.id != article.id:

                similar_articles += [item]

        except ValueError:
            pass

    context = similar_articles
    print(context)
    return context


""" def search_tokenization(db, search=None, articles=None):

    new_articles = []

    search = str(search).lower()
    search = re.split(' |\.|\,|\_|\?|\!', search)
    search = siem_subword_tokenizer(search)
    for item in articles:
        try:
            vect = CountVectorizer(
                token_pattern=r"(?u)[A-Za-zżźćńółęąśŻŹĆĄŚĘŁÓŃ][A-Za-z0-9żźćńółęąśŻŹĆĄŚĘŁÓŃ]+", stop_words=stop_words, analyzer='word')
            item_text = [item.text, item.title]
            vect.fit(item_text)
            item_text = siem_subword_tokenizer(
                vect.get_feature_names_out())
            for search_item in search:
                if search_item in item_text:
                    new_articles += [item]
                    break

        except ValueError:
            pass
    print(new_articles)
    return new_articles """


def search_tokenization(db, search=None, articles=None):
    search = str(search).lower()
    search = re.split(' |\.|\,|\_|\?|\!', search)
    search = siem_subword_tokenizer(search)
    print(search)
    query = articles
    for search_item in search:
        query = query.filter(models.Article.text.ilike(
            f'%{search_item}%') | models.Article.title.ilike(f'%{search_item}%'))

    return query


def return_queries(articles, query, db, user_id, per_page, page, url):
    subquery_fav = db.query(models.Favourite).filter(
        models.Favourite.owner_id == user_id).subquery()
    favs = db.query(subquery_fav).all()
    subquery = db.query(models.Vote).filter(
        models.Vote.owner_id == user_id).subquery()

    votes = db.query(subquery).all()
    for article in articles:
        article.voted = any(vote.article_id ==
                            article.id for vote in votes)
        article.is_favorite = any(
            favorite.article_id == article.id for favorite in favs)

    has_next_page = (len(articles) == per_page)
    has_previous_page = (page > 1)
    total_pages = (query.count() + per_page - 1) // per_page
    next = ""
    previous = ""
    if has_next_page:
        next = url + str(page+1)
    if has_previous_page:
        previous = url + str(page-1)

    return {"articles": articles, "has_next_page": has_next_page, "has_previous_page": has_previous_page, "total_pages": total_pages, "next": next, "previous": previous}


def single_return_query(article, db, user_id):
    
    subquery_fav = db.query(models.Favourite).filter(
        models.Favourite.owner_id == user_id).subquery()
    subquery = db.query(models.Vote).filter(
        models.Vote.owner_id == user_id).subquery()
    votes = db.query(subquery).all()
    favs = db.query(subquery_fav).all()
    article.voted = any(vote.article_id ==
                        article.id for vote in votes)
    article.is_favorite = any(
        favorite.article_id == article.id for favorite in favs)
    if article is not None:
        return article