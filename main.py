from typing import List
from fastapi import Request, UploadFile, File
from auth.auth import get_password_hash, authenticate_user
from sqlalchemy.orm import joinedload, subqueryload
from uuid import UUID, uuid4
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
# from fastapi_pagination import Page, add_pagination
from sqlalchemy import exc
from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi import Depends, FastAPI, Response, BackgroundTasks
from sqlalchemy.orm import Session
from db import models, schemas
from db.db import SessionLocal, engine
import datetime
from fastapi.exceptions import HTTPException
from fastapi_jwt_auth import AuthJWT
import jwt
from config import settings
from fastapi.responses import JSONResponse
from utils import compare_arts, search_tokenization, return_queries, single_return_query
from sqlalchemy import asc, desc
from auth import oauth2
import time
from apscheduler.schedulers.background import BackgroundScheduler
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


models.Base.metadata.create_all(bind=engine)


app = FastAPI(debug=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


origins = [
    'http://127.0.0.1:3000',

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_token_from_headers(request: Request):
    if "Authorization" not in request.headers:
        raise HTTPException(
            status_code=400, detail="Authorization not in headers")
    auth_header = request.headers["Authorization"]
    token = auth_header.split(" ")[1]
    return token


def check_expired_articles(job):

    db = SessionLocal()
    today = datetime.datetime.now().date()
    expired_articles = db.query(models.Article).filter(
        models.Article.expiration_date == today, models.Article.is_expired == False).all()
    for article in expired_articles:
        article.is_expired = True
        db.commit()
    db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(check_expired_articles, 'interval',
                  minutes=1440, args=[scheduler])
scheduler.start()


@app.get("/api/articles/")
async def read_articles(
    background_tasks: BackgroundTasks,
    expired: bool = False,
    my_articles: bool = False,
    filter: str = None,
    search: str = None,
    tag: str = None,
    not_approved: bool = False,
    compare: UUID = None,
    page: int = 1,
    per_page: int = 5,
    token: str = Depends(get_token_from_headers),
    db: Session = Depends(get_db),
):

    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    user_id = users.id

    background_tasks.add_task(check_expired_articles, db)
    query = db.query(models.Article).options(joinedload(models.Article.tags), joinedload(
        models.Article.comment), subqueryload(models.Article.vote))
    """ query = db.query(models.Article).options(joinedload(models.Article.tags), joinedload(
        models.Article.comment)) """
    url = "http://127.0.0.1:8000/api/articles/?page="

    if search is not None and filter is None:
        query = query.filter(models.Article.approved == True).order_by(
            asc(models.Article.created))
        query = search_tokenization(db, search, query)
        articles = query.offset((page - 1) * per_page).limit(per_page).all()
        return return_queries(articles, query, db, user_id, per_page, page, url)

    elif expired:
        user_id = users.id
        articles = query.filter(models.Article.is_expired == True).filter(
            models.Article.approved == True).order_by(asc(models.Article.created)).all()
        subquery = db.query(models.Vote).filter(
            models.Vote.owner_id == user_id).subquery()
        votes = db.query(subquery).all()
        for article in articles:
            article.voted = any(vote.article_id ==
                                article.id for vote in votes)
        return articles
    elif compare is not None:
        return compare_arts(compare, db)

    elif not_approved:
        user_id = users.id
        articles = query.filter(models.Article.approved == False).order_by(
            asc(models.Article.created)).all()
        subquery = db.query(models.Vote).filter(
            models.Vote.owner_id == user_id).subquery()
        votes = db.query(subquery).all()
        for article in articles:
            article.voted = any(vote.article_id ==
                                article.id for vote in votes)
        return articles

    elif tag is not None:
        query = query.filter(models.Article.approved == True, models.Article.tags.any(
            models.Tag.name == tag))
        articles = query.offset((page - 1) * per_page).limit(per_page).all()
        return return_queries(articles, query, db, user_id, per_page, page, url)

    elif filter is not None and search is not None:
        filter = filter.split(",")
        for tag in filter:
            query = query.filter(models.Article.tags.any(models.Tag.id == tag))
        query = search_tokenization(db, search, query)
        articles = query.offset((page - 1) * per_page).limit(per_page).all()
        return return_queries(articles, query, db, user_id, per_page, page, url)

    elif filter is not None and search is None:
        filter = filter.split(",")
        for tag in filter:
            query = query.filter(models.Article.tags.any(models.Tag.id == tag)).filter(
                models.Article.approved == True)
        articles = query.offset((page - 1) * per_page).limit(per_page).all()
        return return_queries(articles, query, db, user_id, per_page, page, url)

    else:
        query = query.filter(models.Article.approved == True).order_by(
            desc(models.Article.created))
        articles = query.offset((page - 1) * per_page).limit(per_page).all()
        return return_queries(articles, query, db, user_id, per_page, page, url)


@app.get('/api/my_articles/')
async def read_article(db: Session = Depends(get_db), token: str = Depends(get_token_from_headers), page: int = 1,
    per_page: int = 5):
    url = "http://127.0.0.1:8000/api/my_articles/?page="
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()

    query = db.query(models.Article).options(joinedload(models.Article.comment), joinedload(
        models.Article.tags), subqueryload(models.Article.vote)).filter(models.Article.owner_id == users.id).order_by(asc(models.Article.created))
    user_id = users.id
    
    articles = query.offset((page - 1) * per_page).limit(per_page).all()
    return return_queries(articles, query, db, user_id, per_page, page, url)


@app.get('/api/favorite/')
async def read_favorite_articles(db: Session = Depends(get_db), token: str = Depends(get_token_from_headers), page: int = 1,
                                 per_page: int = 5):

    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    user_id = users.id
    url = "http://127.0.0.1:8000/api/favorite/?page="
    query = db.query(models.Article).options(joinedload(models.Article.comment), joinedload(
        models.Article.tags), subqueryload(models.Article.vote), subqueryload(models.Article.favourite)).filter(models.Favourite.owner_id == user_id).filter(models.Article.id == models.Favourite.article_id).order_by(asc(models.Article.created))
    articles = query.offset((page - 1) * per_page).limit(per_page).all()

    return return_queries(articles, query, db, user_id, per_page, page, url)


@app.post('/api/favorite/{article_id}')
async def add_vote(article_id: UUID, favorite: schemas.Favourite, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    user_id = users.id
    favorite_model = models.Favourite()
    favorite_model.id = uuid4()
    favorite_model.article_id = article_id
    favorite_model.owner_id = users.id

    try:
        db.add(favorite_model)
        db.flush()
        db.commit()
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="It is already your favorite article.")
    article = db.query(models.Article).filter(
        models.Article.id == article_id).options(joinedload(models.Article.comment), joinedload(models.Article.tags), subqueryload(models.Article.vote)).first()
    return single_return_query(article, db, user_id)


@app.delete('/api/favorite/{article_id}')
async def delete_vote(article_id: UUID, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    user_id = users.id
    favorite = db.query(models.Favourite).filter(models.Favourite.article_id ==
                                                 article_id).filter(models.Favourite.owner_id == users.id).first()
    db.query(models.Favourite).filter(models.Favourite.article_id == article_id).filter(
        models.Favourite.owner_id == users.id).delete()
    db.commit()
    article = db.query(models.Article).filter(
        models.Article.id == article_id).options(joinedload(models.Article.comment), joinedload(models.Article.tags), subqueryload(models.Article.vote)).first()
    return single_return_query(article, db, user_id)


@app.post('/api/vote/{article_id}')
async def add_vote(article_id: UUID, vote: schemas.Vote, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    user_id = users.id
    vote_model = models.Vote()
    vote_model.id = uuid4()
    vote_model.article_id = article_id
    vote_model.owner_id = users.id

    try:
        db.add(vote_model)
        db.flush()
        db.query(models.Article).filter(models.Article.id == vote.article_id).update(
            {models.Article.votes: models.Article.votes + 1})
        db.commit()
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="You already voted for this article.")

    article = db.query(models.Article).filter(
        models.Article.id == article_id).options(joinedload(models.Article.comment), joinedload(models.Article.tags), subqueryload(models.Article.vote)).first()

    return single_return_query(article, db, user_id)


@app.delete('/api/vote/{article_id}')
async def delete_vote(article_id: UUID, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    user_id = users.id

    vote = db.query(models.Vote).filter(models.Vote.article_id ==
                                        article_id).filter(models.Vote.owner_id == users.id).first()
    db.query(models.Article).filter(models.Article.id == vote.article_id).update(
        {models.Article.votes: models.Article.votes - 1})
    db.query(models.Vote).filter(models.Vote.article_id == article_id).filter(
        models.Vote.owner_id == users.id).delete()
    db.commit()

    article = db.query(models.Article).filter(
        models.Article.id == article_id).options(joinedload(models.Article.comment), joinedload(models.Article.tags), subqueryload(models.Article.vote)).first()
    return single_return_query(article, db, user_id)


@app.post('/api/comment')
async def create_comment(comment: schemas.Comment, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):

    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()

    comment_model = models.Comment()
    if users is not None:

        comment_model.owner_id = users.id
    comment_model.created = datetime.datetime.now()
    comment_model.id = uuid4()
    comment_model.body = comment.body
    comment_model.article_id = comment.article_id
    db.add(comment_model)
    db.commit()

    article = db.query(models.Article).filter(
        models.Article.id == comment.article_id).options(joinedload(models.Article.comment), joinedload(models.Article.tags), subqueryload(models.Article.vote)).first()
    user_id = users.id
    return single_return_query(article, db, user_id)


@app.get('/api/comment/{article_id}')
async def get_comments(article_id: UUID, db: Session = Depends(get_db)):
    article_comments = db.query(models.Comment).filter(
        models.Comment.article_id == article_id).all()
    return article_comments


@app.put('/api/comment/{comment_id}')
async def update_comment(comment_id: UUID, comment: schemas.UpdateComment, db: Session = Depends(get_db)):
    comment_model = db.query(models.Comment).filter(
        models.Comment.id == comment_id).first()
    comment_model.body = comment.body
    db.add(comment_model)
    db.commit()
    db.refresh(comment_model)
    return successful_response(200)


@app.delete('/api/comment/{comment_id}')
async def delete_comment(comment_id: UUID, db: Session = Depends(get_db)):
    comment_model = db.query(models.Comment).filter(
        models.Comment.id == comment_id).first()
    if comment_model is None:
        raise http_exception()

    db.query(models.Comment).filter(models.Comment.id == comment_id).delete()
    db.commit()


@app.post("/api/articles/")
async def create_article(article: schemas.Article, db: Session = Depends(get_db), Authorize: AuthJWT = Depends(), token: str = Depends(get_token_from_headers)):

    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()

    article_model = models.Article()
    if users is not None:
        article_model.owner_id = users.id
    article_model.text = article.text
    article_model.title = article.title
    article_model.approved = False
    article_model.expiration_date = datetime.date.today() + datetime.timedelta(days=180)
    article_model.is_expired = False
    article_model.created = datetime.datetime.now()
    article_model.id = uuid4()
    if db.query(models.Article).filter(models.Article.id == article_model.id).first() == None:
        db.add(article_model)
        db.commit()
    for tag_id in article.tag:
        tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
        if tag:
            article_tag = models.ArticleTag()
            article_tag.article_id = article_model.id
            article_tag.tag_id = tag.id
            db.add(article_tag)
            db.commit()
        else:
            return JSONResponse(content={"detail": "Tag with this ID not exists"})
    return db.query(models.Article).filter(models.Article.id == article_model.id).options(joinedload(models.Article.comment), joinedload(models.Article.tags)).first()


@app.put("/api/articles/{article_id}")
async def update_article(article_id: UUID, article: schemas.Article, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    article_model = db.query(models.Article).filter(
        models.Article.id == article_id).first()
    update_article_dict = article.dict(exclude_unset=True)
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    user_id = users.id
    if article_model is None:
        raise http_exception()
    if 'title' in update_article_dict:
        article_model.title = article.title
    if 'text' in update_article_dict:
        article_model.text = article.text
    if 'approved' in update_article_dict:
        article_model.approved = article.approved
    if 'is_expired' in update_article_dict:
        if article.is_expired == False:
            article_model.expiration_date = datetime.date.today() + datetime.timedelta(days=180)
        article_model.is_expired = article.is_expired

    # update tags

    if 'tag' in update_article_dict:
        article_model.tags.clear()
        for tag_id in article.tag:
            tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
            if not tag:
                raise HTTPException(status_code=404, detail="Tag not found")
            article_model.tags.append(tag)

    db.add(article_model)
    db.commit()
    article = db.query(models.Article).filter(
        models.Article.id == article_id).options(joinedload(models.Article.comment), joinedload(models.Article.tags), subqueryload(models.Article.vote)).first()

    return single_return_query(article, db, user_id)


@app.get("/api/articles/{article_id}")
async def get_article(article_id: UUID, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']

    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    user_id = users.id
    article = db.query(models.Article).filter(
        models.Article.id == article_id).options(joinedload(models.Article.comment), joinedload(models.Article.tags), subqueryload(models.Article.vote)).first()

    return single_return_query(article, db, user_id)


@app.delete("/api/articles/{article_id}")
async def delete_article(article_id: UUID, db: Session = Depends(get_db)):
    article_model = db.query(models.Article).filter(
        models.Article.id == article_id).first()

    db.query(models.Comment).filter(
        models.Comment.article_id == article_id).delete()
    db.query(models.ArticleTag).filter(
        models.ArticleTag.article_id == article_id).delete()
    db.query(models.Vote).filter(models.Vote.article_id == article_id).delete()
    db.query(models.Favourite).filter(
        models.Favourite.article_id == article_id).delete()

    if article_model is None:
        raise http_exception()

    db.query(models.Article).filter(models.Article.id == article_id).delete()
    db.commit()

    return successful_response(200)


@app.post("/api/users/")
async def create_new_user(create_user: schemas.CreateUser, db: Session = Depends(get_db)):
    create_user_model = models.Users()
    create_user_model.id = uuid4()
    create_user_model.created = datetime.datetime.now()
    create_user_model.email = create_user.email
    create_user_model.username = create_user.username
    create_user_model.last_name = create_user.last_name
    create_user_model.first_name = create_user.first_name

    hash_password = get_password_hash(create_user.password)
    create_user_model.password = hash_password
    create_user_model.is_active = True
    create_user_model.is_superuser = create_user.is_superuser

    db.add(create_user_model)
    db.commit()
    db.refresh(create_user_model)
    return create_user_model


@app.get("/api/users/")
async def read_users(db: Session = Depends(get_db)):
    return db.query(models.Users).all()


@app.put("/api/users/{user_id}")
async def create_new_user(user_id: UUID, update_user: schemas.UpdateUser, db: Session = Depends(get_db)):
    update_user_model = db.query(models.Users).filter(
        models.Users.id == user_id).first()
    update_user_dict = update_user.dict(exclude_unset=True)

    if 'username' in update_user_dict:
        update_user_model.username = update_user.username
    if 'last_name' in update_user_dict:
        update_user_model.last_name = update_user.last_name
    if 'first_name' in update_user_dict:
        update_user_model.first_name = update_user.first_name
    if 'email' in update_user_dict:
        update_user_model.email = update_user.email
    if 'is_superuser' in update_user_dict:
        update_user_model.is_superuser = update_user.is_superuser
    if 'password' in update_user_dict:

        hash_password = get_password_hash(
            update_user_dict['password'])
        update_user_model.password = hash_password

    db.add(update_user_model)
    db.commit()
    db.refresh(update_user_model)
    return update_user_model


@app.post('/api/token/')
async def login_for_access_token(response: Response, Authorize: AuthJWT = Depends(), form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        return HTTPException(status_code=404, detail="User not found")

    claims = {'username': user.username,
              'superuser': user.is_superuser, 'id': str(user.id)}
    # Create access token
    access_token = Authorize.create_access_token(
        subject=user.username, user_claims=claims)
    refresh_token = Authorize.create_refresh_token(
        subject=user.username, user_claims=claims)

    # Set the JWT cookies in the ilv
    # Authorize.set_access_cookies(access_token)
    # Authorize.set_refresh_cookies(refresh_token)
    return {'access_token': access_token, 'refresh_token': refresh_token}


@app.post('/api/token/refresh')
async def get_refresh_token(request: Request, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    refresh_token = (await request.json())

    Authorize.jwt_refresh_token_required(refresh_token)

    current_user = jwt.decode(refresh_token, verify=False)
    current_user = current_user['sub']
    if current_user is None:
        return http_exception()
    user = db.query(models.Users).filter(
        models.Users.username == current_user).first()
    claims = {'username': user.username,
              'superuser': user.is_superuser, 'id': str(user.id)}
    new_access_token = Authorize.create_access_token(
        subject=current_user, user_claims=claims)
    # Set the JWT cookies in the response
    return {'access_token': new_access_token}


@app.get("/api/tags/")
async def read_tags(db: Session = Depends(get_db)):
    return db.query(models.Tag).all()


@app.post("/api/tags/")
async def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    if len(tag.name) > 10 or len(tag.name) == 0 or len(tag.description) == 0:
        raise HTTPException(
            status_code=400, detail='Tag name too long or empty tag name or empty tag description')

    tag_model = models.Tag()
    tag_model.id = uuid4()

    tag_model.name = tag.name.lower()
    tag_model.description = tag.description

    tag_model.created = datetime.datetime.now()

    db.add(tag_model)
    db.commit()

    return successful_response(201)


@app.delete("/api/tags/{tag_id}")
async def delete_tag(tag_id: UUID, db: Session = Depends(get_db)):
    tag_model = db.query(models.Tag).filter(
        models.Tag.id == tag_id).first()

    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if tag is None:
        raise http_exception()

    db.query(models.ArticleTag).filter(
        models.ArticleTag.tag_id == tag_id).delete()
    db.query(models.FilterTag).filter(
        models.FilterTag.tag_id == tag_id).delete()

    db.commit()

    if tag_model is None:
        raise http_exception()

    db.query(models.Tag).filter(models.Tag.id == tag_id).delete()
    db.commit()

    return successful_response(200)


@app.get("/api/filter/")
async def read_filters(db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()
    return db.query(models.Filter).options(joinedload(models.Filter.tags)).filter(models.Filter.owner_id == users.id).all()


@app.post("/api/filter/")
async def create_filter(filter: schemas.Filter, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):

    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()

    filter_model = models.Filter()
    filter_model.id = uuid4()
    if users is not None:
        filter_model.owner_id = users.id
    filter_model.name = filter.name
    filter_model.created = datetime.datetime.now()
    if db.query(models.Filter).filter(models.Filter.id == filter_model.id).first() == None:
        db.add(filter_model)
        db.commit()

    for tag_id in filter.tag:
        tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
        if tag:
            filter_tag = models.FilterTag()
            filter_tag.filter_id = filter_model.id
            filter_tag.tag_id = tag.id
            db.add(filter_tag)
            db.commit()
        else:
            return JSONResponse(content={"detail": "Tag with this ID not exists"})

    return successful_response(201)


@app.delete("/api/filter/{filter_id}")
async def delete_filter(filter_id: UUID, db: Session = Depends(get_db)):
    filter_model = db.query(models.Filter).filter(
        models.Filter.id == filter_id).first()

    if filter_model is None:
        raise http_exception()
    db.query(models.FilterTag).filter(
        models.FilterTag.filter_id == filter_id).delete()
    db.query(models.Filter).filter(models.Filter.id == filter_id).delete()
    db.commit()

    return successful_response(200)


@app.get('/api/notes/')
async def read_notes(db: Session = Depends(get_db)):
    return db.query(models.Section).filter(models.Section.public == True).order_by(asc(models.Section.created)).all()


@app.get("/api/my_notes/")
async def read_my_notes(db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()

    return db.query(models.Note).options(joinedload(models.Note.section)).filter(models.Note.owner_id == users.id).order_by(asc(models.Note.created)).all()


@app.post("/api/notes/")
async def create_note(note: schemas.Note, db: Session = Depends(get_db), token: str = Depends(get_token_from_headers)):
    current_user = jwt.decode(token, verify=False)
    current_user = current_user['id']
    users = db.query(models.Users).filter(
        models.Users.id == current_user).first()

    note_model = models.Note()
    note_model.id = uuid4()
    if users is not None:
        note_model.owner_id = users.id
    note_model.created = datetime.datetime.now()
    note_model.title = "New note"

    db.add(note_model)
    db.commit()

    new_section = models.Section(
        title="New section", body="", note_id=note_model.id, id=uuid4(), created=datetime.datetime.now())
    db.add(new_section)
    db.commit()
    return db.query(models.Note).options(joinedload(models.Note.section)).filter(models.Note.id == note_model.id).first()


@app.put("/api/notes/{note_id}")
async def update_note(note_id: UUID, update_note: schemas.Note, db: Session = Depends(get_db)):
    update_note_model = db.query(models.Note).filter(
        models.Note.id == note_id).first()
    update_note_dict = update_note.dict(exclude_unset=True)

    if 'title' in update_note_dict:
        update_note_model.title = update_note.ttile

    db.add(update_note_model)
    db.commit()
    db.refresh(update_note_model)
    return update_note_model


@app.delete("/api/notes/{note_id}")
async def delete_filter(note_id: UUID, db: Session = Depends(get_db)):
    note_model = db.query(models.Note).filter(
        models.Note.id == note_id).first()

    if note_model is None:
        raise http_exception()
    db.query(models.Section).filter(
        models.Section.note_id == note_id).delete()
    db.query(models.Note).filter(models.Note.id == note_id).delete()
    db.commit()

    return successful_response(200)


@app.post('/api/sections')
async def create_section(section: schemas.Section, db: Session = Depends(get_db)):
    section_model = models.Section()
    section_model.id = uuid4()
    section_model.created = datetime.datetime.now()
    section_model.title = "New section"
    section_model.body = ""
    section_model.note_id = section.note_id
    db.add(section_model)
    db.commit()
    return db.query(models.Note).options(joinedload(models.Note.section)).filter(models.Note.id == section.note_id).first()


@app.get('/api/sections/')
async def read_sections(db: Session = Depends(get_db)):
    return db.query(models.Section).filter(models.Section.public == True).order_by(asc(models.Section.created)).all()


@app.put('/api/sections/{section_id}')
async def update_section(section_id: UUID, update_section: schemas.UpdateSection, db: Session = Depends(get_db)):
    update_section_model = db.query(models.Section).filter(
        models.Section.id == section_id).first()
    update_section_dict = update_section.dict(exclude_unset=True)

    if 'title' in update_section_dict:
        update_section_model.title = update_section.title
    if 'body' in update_section_dict:
        update_section_model.body = update_section.body
    if 'public' in update_section_dict:
        update_section_model.public = update_section.public

    db.add(update_section_model)
    db.commit()
    db.refresh(update_section_model)
    return db.query(models.Note).options(joinedload(models.Note.section)).filter(models.Note.id == update_section_model.note_id).first()


@app.delete('/api/sections/{section_id}')
async def delete_section(section_id: UUID, db: Session = Depends(get_db)):
    section = db.query(models.Section).filter(
        models.Section.id == section_id).first()
    if section:
        note = section.note
        note.section.remove(section)
        db.delete(section)
        if not note.section:
            db.delete(note)
        db.commit()
        return db.query(models.Note).options(joinedload(models.Note.section)).filter(models.Note.id == section.note_id).first()


def http_exception():
    return HTTPException(status_code=404, detail="object not found")


def successful_response(status_code: int):
    return {
        'status': status_code,
        'transaction': 'Successful'
    }


add_pagination(app)
