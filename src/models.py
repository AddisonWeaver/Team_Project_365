from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Table,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base

# Jared #2.6 / Avery #10.8: ON DELETE CASCADE so dependent rows are cleaned up when a movie/user is removed
movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.movie_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        Integer,
        ForeignKey("genres.genre_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

movie_actors = Table(
    "movie_actors",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.movie_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "actor_id",
        Integer,
        ForeignKey("actors.actor_id", ondelete="CASCADE"),
        primary_key=True,
    ),
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
    # Jared #2.8 / Anthony #7,#8.5 / Avery #10.5: store release_year for filtering and disambiguation
    release_year = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        # Jared #2.4 / Anthony #8.1 / Avery #9.17: restrict media_type to known values
        CheckConstraint("media_type IN ('movie', 'tv')", name="media_type_valid"),
        # Jared #2.8 / Anthony #7,#8.5 / Avery #10.5: keep release_year in range
        CheckConstraint(
            "release_year IS NULL OR (release_year >= 1888 AND release_year <= 2031)",
            name="release_year_range",
        ),
    )
    genres = relationship("Genre", secondary=movie_genres, back_populates="movies")
    actors = relationship("Actor", secondary=movie_actors, back_populates="movies")
    reviews = relationship(
        "Review", back_populates="movie", cascade="all, delete-orphan"
    )
    ratings = relationship(
        "Rating", back_populates="movie", cascade="all, delete-orphan"
    )
    watch_history = relationship(
        "WatchHistory", back_populates="movie", cascade="all, delete-orphan"
    )


class Genre(Base):
    __tablename__ = "genres"
    genre_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    movies = relationship("Movie", secondary=movie_genres, back_populates="genres")


class Actor(Base):
    __tablename__ = "actors"
    actor_id = Column(Integer, primary_key=True, index=True)
    # Jared #2.5 / Anthony #8.4 / Avery #10.7: enforce uniqueness of actor names to avoid duplicates
    name = Column(String(255), nullable=False, unique=True)
    movies = relationship("Movie", secondary=movie_actors, back_populates="actors")


class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(Integer, primary_key=True, index=True)
    # Jared #2.6 / Avery #10.8: cascade delete + index FK columns used in JOIN/WHERE
    movie_id = Column(
        Integer,
        ForeignKey("movies.movie_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_text = Column(Text, nullable=False)
    contains_spoilers = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        # Jared #2.3 / Avery #9.7,#10.6: one review per user per movie
        UniqueConstraint("user_id", "movie_id", name="uq_reviews_user_movie"),
        # Jared #2.7 / Anthony #8.3 / Avery #9.6: cap review_text length at DB layer too
        CheckConstraint(
            "length(review_text) BETWEEN 1 AND 2000",
            name="review_text_length",
        ),
    )
    movie = relationship("Movie", back_populates="reviews")
    user = relationship("User", back_populates="reviews")


class Rating(Base):
    __tablename__ = "ratings"
    rating_id = Column(Integer, primary_key=True, index=True)
    # Jared #2.6 / Avery #10.8: cascade delete + index FK columns used in JOIN/WHERE
    movie_id = Column(
        Integer,
        ForeignKey("movies.movie_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
        # Jared #2.1 / Anthony #5.4,#8.2 / Avery #9.7,#10.6: one rating per user per movie
        UniqueConstraint("user_id", "movie_id", name="uq_ratings_user_movie"),
    )
    movie = relationship("Movie", back_populates="ratings")
    user = relationship("User", back_populates="ratings")


class WatchHistory(Base):
    __tablename__ = "watch_history"
    watch_history_id = Column(Integer, primary_key=True, index=True)
    # Jared #2.6 / Avery #10.8: cascade delete + index FK columns used in JOIN/WHERE
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    movie_id = Column(
        Integer,
        ForeignKey("movies.movie_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date_watched = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        # Jared #2.2 / Anthony #8.8: one watch_history row per user+movie (Jared and Anthony had different ways of solving this issue)
        # We chose to use unique here so the data model itself prevents duplicates;
        UniqueConstraint("user_id", "movie_id", name="uq_watch_user_movie"),
    )
    user = relationship("User", back_populates="watch_history")
    movie = relationship("Movie", back_populates="watch_history")
