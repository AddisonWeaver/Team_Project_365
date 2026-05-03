from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from src.database import get_db
from src.models import User, Movie, WatchHistory, Rating, Review

router = APIRouter(prefix="/users", tags=["users"])


class WatchHistoryCreate(BaseModel):
    movie_id: int
    date_watched: str


@router.post("/{user_id}/watch-history")
def add_to_watch_history(
    user_id: int,
    body: WatchHistoryCreate,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    movie = db.query(Movie).filter(Movie.movie_id == body.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    try:
        date_watched = datetime.fromisoformat(body.date_watched)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    entry = WatchHistory(
        user_id=user_id,
        movie_id=body.movie_id,
        date_watched=date_watched,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "watch_history_id": entry.watch_history_id,
        "message": "Movie added to watch history successfully",
    }


@router.get("/{user_id}/watch-history")
def get_watch_history(
    user_id: int,
    media_type: Optional[str] = Query(None),
    limit: int = Query(10),
    sort: Optional[str] = Query("recent"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = (
        db.query(WatchHistory)
        .filter(WatchHistory.user_id == user_id)
        .join(WatchHistory.movie)
    )

    if media_type:
        query = query.filter(Movie.media_type == media_type)

    if sort == "recent":
        query = query.order_by(WatchHistory.date_watched.desc())
    elif sort == "title":
        query = query.order_by(Movie.title.asc())

    entries = query.limit(limit).all()

    results = []
    for entry in entries:
        m = entry.movie
        avg = db.query(func.avg(Rating.rating)).filter(
            Rating.movie_id == m.movie_id).scalar()
        count = db.query(func.count(Review.review_id)).filter(
            Review.movie_id == m.movie_id).scalar()
        results.append({
            "movie_id": m.movie_id,
            "title": m.title,
            "media_type": m.media_type,
            "genre": [g.name for g in m.genres],
            "average_rating": round(float(avg), 2) if avg else None,
            "number_of_reviews": count,
            "actors": [a.name for a in m.actors],
            "date_watched": entry.date_watched.date().isoformat(),
        })

    return results
