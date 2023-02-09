from .db import Base
from sqlalchemy import String, Boolean, Date, DateTime, ForeignKey, Column, UniqueConstraint, Integer
from sqlalchemy_utils import TSVectorType
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ArticleTag(Base):
    __tablename__ = "article_tag"
    article_id = Column(UUID(as_uuid=True), ForeignKey(
        "article.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tag.id"), primary_key=True)


class FilterTag(Base):
    __tablename__ = "filter_tag"
    filter_id = Column(UUID(as_uuid=True), ForeignKey(
        "filter.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tag.id"), primary_key=True)


class Users(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    password = Column(String)
    is_superuser = Column(Boolean)
    is_active = Column(Boolean)
    created = Column(DateTime)

    article = relationship("Article", back_populates="owner")
    filter = relationship("Filter", back_populates="owner")
    note = relationship("Note", back_populates="owner")
    comment = relationship("Comment", back_populates="owner")


class Note(Base):
    __tablename__ = "note"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    owner = relationship('Users', back_populates="note")
    title = Column(String)
    created = Column(DateTime)
    section = relationship(
        "Section", back_populates="note", order_by="Section.created")


class Section(Base):
    __tablename__ = "section"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    title = Column(String)
    body = Column(String)
    public = Column(Boolean, default=False)
    created = Column(DateTime)
    note_id = Column(UUID(as_uuid=True), ForeignKey('note.id'))
    note = relationship('Note', back_populates="section")


class Article(Base):
    __tablename__ = "article"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    title = Column(String)
    text = Column(String)
    tags = relationship("Tag", secondary="article_tag",
                        back_populates="article")
    approved = Column(Boolean, default=False)
    expiration_date = Column(Date)
    is_expired = Column(Boolean, default=False)
    created = Column(DateTime)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    owner = relationship('Users', back_populates="article")
    vote = relationship('Vote', back_populates='article',
                        cascade="all, delete")
    favourite = relationship(
        'Favourite', back_populates='article', cascade="all, delete")
    comment = relationship(
        "Comment", back_populates="article", order_by="Comment.created")
    votes = Column(Integer, default=0)


class Vote(Base):
    __tablename__ = 'vote'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey(
        'users.id'), primary_key=True)
    article_id = Column(UUID(as_uuid=True), ForeignKey(
        'article.id'), primary_key=True)
    article = relationship('Article', back_populates='vote')
    __table_args__ = (UniqueConstraint("owner_id", "article_id"),)


class Favourite(Base):
    __tablename__ = 'favourite'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey(
        'users.id'), primary_key=True)
    article_id = Column(UUID(as_uuid=True), ForeignKey(
        'article.id'), primary_key=True)
    article = relationship('Article', back_populates='favourite')
    __table_args__ = (UniqueConstraint("owner_id", "article_id"),)


class Comment(Base):
    __tablename__ = 'comment'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    created = Column(DateTime)
    body = Column(String)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    owner = relationship('Users', back_populates="comment")
    article_id = Column(UUID(as_uuid=True), ForeignKey('article.id'))
    article = relationship('Article', back_populates="comment")


class Tag(Base):
    __tablename__ = "tag"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(10), index=True, unique=True)
    article = relationship(
        "Article", secondary="article_tag", back_populates="tags")
    filter = relationship(
        "Filter", secondary="filter_tag", back_populates="tags")
    description = Column(String)


class Filter(Base):
    __tablename__ = "filter"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String)
    created = Column(DateTime)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    owner = relationship('Users', back_populates="filter")
    tags = relationship("Tag", secondary="filter_tag",
                        back_populates="filter")
