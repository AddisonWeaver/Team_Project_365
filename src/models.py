from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Table, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base

movie_genres = Table(
    "movie_genres", Base.metadata,
    Column("movie_id", Integer, ForeignKey(
        "movies.movie_id"), primary_key=True),
    Column("genre_id", Integer, ForeignKey(
        "genres.genre_id"), primary_key=True),
)

movie_actors = Table(
    "movie_actors", Base.metadata,
    Column("movie_id", Integer, ForeignKey(
        "movies.movie_id"), primary_key=True),
    Column("actor_id", Integer, ForeignKey(
        "actors.actor_id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviews = relationship("Review", back_populates="user")
    ratings = relationship("Rating", back_populates="user")
    watch_history = relationship("WatchHistory", back_populates="user")


class Movie(Base):
    __tablename__ = "movies"
    movie_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    media_type = Column(String(10), nullable=False, default="movie")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    genres = relationship("Genre", secondary=movie_genres,
                          back_populates="movies")
    actors = relationship("Actor", secondary=movie_actors,
                          back_populates="movies")
    reviews = relationship("Review", back_populates="movie")
    ratings = relationship("Rating", back_populates="movie")
    watch_history = relationship("WatchHistory", back_populates="movie")


class Genre(Base):
    __tablename__ = "genres"
    genre_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    movies = relationship("Movie", secondary=movie_genres,
                          back_populates="genres")


class Actor(Base):
    __tablename__ = "actors"
    actor_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    movies = relationship("Movie", secondary=movie_actors,
                          back_populates="movies")


class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.movie_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    review_text = Column(Text, nullable=False)
    contains_spoilers = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    movie = relationship("Movie", back_populates="reviews")
    user = relationship("User", back_populates="reviews")


class Rating(Base):
    __tablename__ = "ratings"
    rating_id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.movie_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint(
        "rating >= 1 AND rating <= 5", name="rating_range"),)
    movie = relationship("Movie", back_populates="ratings")
    user = relationship("User", back_populates="ratings")


class WatchHistory(Base):
    __tablename__ = "watch_history"
    watch_history_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.movie_id"), nullable=False)
    date_watched = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="watch_history")
    movie = relationship("Movie", back_populates="watch_history")
