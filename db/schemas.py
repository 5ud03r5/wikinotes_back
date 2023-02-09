from pydantic import BaseModel
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
import datetime


class NoteBase(BaseModel):
    title: Optional[str]
    section: Optional[List[UUID]]


class Note(NoteBase):
    title: Optional[str]
    section: Optional[List[UUID]]


class SectionBase(BaseModel):
    title: Optional[str]
    body: Optional[str]
    note_id: UUID


class Section(SectionBase):
    title: Optional[str]
    body: Optional[str]


class CommentBase(BaseModel):
    body: str
    article_id: Optional[UUID]
    owner_id: Optional[UUID]


class Comment(CommentBase):
    body: str
    article_id = UUID


class UpdateComment(CommentBase):
    body: str


class UpdateSection(SectionBase):
    title: Optional[str]
    body: Optional[str]
    note_id: Optional[UUID]
    public: Optional[bool]


class TagBase(BaseModel):
    name: Optional[str]
    description: Optional[str]
    # id: UUID


class TagCreate(TagBase):
    name: str
    description: str


class Tag(TagBase):
    name: Optional[str]
    description: Optional[str]
    id: UUID


class TagOut(TagBase):
    name: Optional[str]
    description: Optional[str]
    id: UUID

    class Config:
        orm_mode = True


class FilterBase(BaseModel):
    # owner: UUID
    name: str
    tag: List[UUID]
    # created: datetime.datetime
    # id: UUID


class FilterCreate(FilterBase):
    name: str
    tag: List[UUID]


class Filter(FilterBase):
    name: str
    tag: List[UUID]


class UserBase(BaseModel):
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    password: str
    is_active: Optional[bool]
    is_superuser: bool


class CreateUser(UserBase):
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    password: str
    is_active: Optional[bool]
    is_superuser: bool


class VoteBase(BaseModel):
    article_id: UUID


class Vote(VoteBase):
    article_id: UUID


class FavouriteBase(BaseModel):
    article_id: UUID


class Favourite(FavouriteBase):
    article_id: UUID


class UpdateUser(UserBase):
    username: Optional[str]
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    password: Optional[str]
    is_active: Optional[bool]
    is_superuser: Optional[bool]


class ArticleBase(BaseModel):
    owner_id: Optional[UUID]
    title: str
    text: Optional[str]
    tag: List[UUID]
    approved: Optional[bool]
    expiration_date: Optional[datetime.date]
    is_expired: Optional[bool]


class ArticleUpdate(ArticleBase):
    owner_id: Optional[UUID]
    title: str
    text: Optional[str]
    tag: List[UUID]
    approved: Optional[bool]
    expiration_date: Optional[datetime.date]
    is_expired: Optional[bool]


class Article(ArticleBase):
    owner_id: Optional[UUID]
    title: Optional[str]
    text: Optional[str]
    tag: Optional[List[UUID]]
    approved: Optional[bool]
    expiration_date: Optional[datetime.date]
    is_expired: Optional[bool]


class ArticleOut(ArticleBase):
    owner_id: Optional[UUID]
    title: str
    text: Optional[str]
    tag: List[TagOut]
    approved: Optional[bool]
    expiration_date: Optional[datetime.date]
    is_expired: Optional[bool]

    class Config:
        orm_mode = True
