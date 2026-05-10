from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel

from src.database import get_db
from src.models import Movie, Genre, Actor, Review, Rating, WatchHistory

router = APIRouter(prefix="/movies", tags=["movies"])


def movie_to_dict(movie: Movie, user_id: Optional[int] = None, db: Session = None):
    avg_rating = (
        db.query(func.avg(Rating.rating))
        .filter(Rating.movie_id == movie.movie_id)
        .scalar()
    )
    num_reviews = (
        db.query(func.count(Review.review_id))
        .filter(Review.movie_id == movie.movie_id)
        .scalar()
    )
    watched = False
    if user_id and db:
        watched = (
            db.query(WatchHistory)
            .filter(WatchHistory.movie_id == movie.movie_id,
                    WatchHistory.user_id == user_id)
            .first() is not None
        )
    return {
        "movie_id": movie.movie_id,
        "title": movie.title,
        "media_type": movie.media_type,
        "genre": [g.name for g in movie.genres],
        "average_rating": round(float(avg_rating), 2) if avg_rating else None,
        "number_of_reviews": num_reviews,
        "actors": [a.name for a in movie.actors],
        "watched": watched,
    }


@router.get("/search")
def search_movie(
    title: str = Query(..., description="Title of the movie to search for"),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    movie = (
        db.query(Movie)
        .filter(Movie.title.ilike(f"%{title}%"))
        .first()
    )
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie_to_dict(movie, user_id=user_id, db=db)


@router.get("/filter/genre")
def filter_by_genre(
    genre: str = Query(...),
    user_id: Optional[int] = Query(None),
    limit: Optional[int] = Query(10),
    db: Session = Depends(get_db),
):
    movies = (
        db.query(Movie)
        .join(Movie.genres)
        .filter(Genre.name.ilike(f"%{genre}%"))
        .limit(limit)
        .all()
    )
    return [movie_to_dict(m, user_id=user_id, db=db) for m in movies]


@router.get("/recommendations/popular")
def popular_recommendations(
    limit: int = Query(10),
    genre: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    exclude_watched: bool = Query(False),
    db: Session = Depends(get_db),
):
    import math
    query = db.query(Movie)
    if genre:
        query = query.join(Movie.genres).filter(Genre.name.ilike(f"%{genre}%"))
    movies = query.all()
    results = []
    for m in movies:
        if exclude_watched and user_id:
            already = (
                db.query(WatchHistory)
                .filter(WatchHistory.movie_id == m.movie_id,
                        WatchHistory.user_id == user_id)
                .first()
            )
            if already:
                continue
        avg = db.query(func.avg(Rating.rating)).filter(
            Rating.movie_id == m.movie_id).scalar()
        count = db.query(func.count(Review.review_id)).filter(
            Review.movie_id == m.movie_id).scalar()
        score = round(float(avg) * math.log1p(count) *
                      10, 1) if avg and count else 0.0
        d = movie_to_dict(m, user_id=user_id, db=db)
        d["popularity_score"] = score
        results.append(d)
    results.sort(key=lambda x: x["popularity_score"], reverse=True)
    return results[:limit]


@router.get("/recommendations/by-actor")
def recommendations_by_actor(
    actor: str = Query(...),
    limit: int = Query(10),
    user_id: Optional[int] = Query(None),
    exclude_watched: bool = Query(False),
    db: Session = Depends(get_db),
):
    import math
    movies = (
        db.query(Movie)
        .join(Movie.actors)
        .filter(Actor.name.ilike(f"%{actor}%"))
        .all()
    )
    results = []
    for m in movies:
        if exclude_watched and user_id:
            already = (
                db.query(WatchHistory)
                .filter(WatchHistory.movie_id == m.movie_id,
                        WatchHistory.user_id == user_id)
                .first()
            )
            if already:
                continue
        avg = db.query(func.avg(Rating.rating)).filter(
            Rating.movie_id == m.movie_id).scalar()
        count = db.query(func.count(Review.review_id)).filter(
            Review.movie_id == m.movie_id).scalar()
        score = round(float(avg) * math.log1p(count) *
                      10, 1) if avg and count else 0.0
        d = movie_to_dict(m, user_id=user_id, db=db)
        d["popularity_score"] = score
        results.append(d)
    results.sort(key=lambda x: x["popularity_score"], reverse=True)
    return results[:limit]
