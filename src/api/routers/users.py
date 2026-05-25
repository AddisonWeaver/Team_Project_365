from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field

from src.database import get_db
from src.models import User, Movie, WatchHistory, Rating, Review, Genre, Actor

router = APIRouter(prefix="/users", tags=["users"])

# Jared #1.19 & #1.20: define allowed values so invalid input gets rejected up front
ALLOWED_SORT = {"recent", "title", "rating"}
ALLOWED_MEDIA_TYPE = {"movie", "tv"}


class WatchHistoryCreate(BaseModel):
    movie_id: int
    # Anthony #5.11: date_watched defaults to today when omitted
    date_watched: Optional[str] = None


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

    # Anthony #5.11: default to today; reject dates in the future
    if body.date_watched is None:
        date_watched = datetime.utcnow()
    else:
        try:
            date_watched = datetime.fromisoformat(body.date_watched)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
            )
    if date_watched.date() > datetime.utcnow().date():
        raise HTTPException(
            status_code=400, detail="date_watched cannot be in the future"
        )

    # Jared #1.16 / Anthony #8.8 / Avery #9.8: prevent duplicate watch history per (user, movie); update date instead
    existing = (
        db.query(WatchHistory)
        .filter(WatchHistory.user_id == user_id, WatchHistory.movie_id == body.movie_id)
        .first()
    )
    try:
        if existing:
            existing.date_watched = date_watched
            db.commit()
            db.refresh(existing)
            return {
                "watch_history_id": existing.watch_history_id,
                "message": "Watch history updated successfully",
            }
        entry = WatchHistory(
            user_id=user_id,
            movie_id=body.movie_id,
            date_watched=date_watched,
        )
        db.add(entry)
        db.commit()  # Jared #1.17 / Avery #9.13: wrap commit in try/except for clearer errors
        db.refresh(entry)
        return {
            "watch_history_id": entry.watch_history_id,
            "message": "Movie added to watch history successfully",
        }
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not save watch history")


@router.get("/{user_id}/watch-history")
def get_watch_history(
    user_id: int,
    media_type: Optional[str] = Query(None),
    # Jared #1.18 / Anthony #8.12: cap limit
    limit: int = Query(10, ge=1, le=100),
    sort: Optional[str] = Query("recent"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Jared #1.19: reject invalid sort values
    if sort not in ALLOWED_SORT:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort value. Allowed: {sorted(ALLOWED_SORT)}",
        )
    # Jared #1.20: reject invalid media_type values
    if media_type is not None and media_type not in ALLOWED_MEDIA_TYPE:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media_type. Allowed: {sorted(ALLOWED_MEDIA_TYPE)}",
        )

    # Jared #1.16 / Anthony #8.8 / Avery #11: dedupe watch history one row per movie,
    # showing the most recent date_watched.
    latest_subq = (
        db.query(
            WatchHistory.movie_id.label("movie_id"),
            func.max(WatchHistory.date_watched).label("date_watched"),
        )
        .filter(WatchHistory.user_id == user_id)
        .group_by(WatchHistory.movie_id)
        .subquery()
    )

    query = db.query(Movie, latest_subq.c.date_watched).join(
        latest_subq, Movie.movie_id == latest_subq.c.movie_id
    )

    if media_type:
        query = query.filter(Movie.media_type == media_type)

    if sort == "recent":
        query = query.order_by(latest_subq.c.date_watched.desc())
    elif sort == "title":
        query = query.order_by(Movie.title.asc())
    elif sort == "rating":
        # Avery #10.12 / #9.14: sort=rating now implemented (highest avg first)
        rating_subq = (
            db.query(Rating.movie_id, func.avg(Rating.rating).label("avg_r"))
            .group_by(Rating.movie_id)
            .subquery()
        )
        query = query.outerjoin(
            rating_subq, rating_subq.c.movie_id == Movie.movie_id
        ).order_by(rating_subq.c.avg_r.desc().nullslast())

    rows = query.limit(limit).all()

    # Jared #1.21: create querry's for batches rather than by single movie
    movie_ids = [m.movie_id for m, _ in rows]
    rating_rows = (
        (
            db.query(Rating.movie_id, func.avg(Rating.rating).label("avg_r"))
            .filter(Rating.movie_id.in_(movie_ids))
            .group_by(Rating.movie_id)
            .all()
        )
        if movie_ids
        else []
    )
    rating_map = {r.movie_id: float(r.avg_r) for r in rating_rows}

    review_rows = (
        (
            db.query(Review.movie_id, func.count(Review.review_id).label("c"))
            .filter(Review.movie_id.in_(movie_ids))
            .group_by(Review.movie_id)
            .all()
        )
        if movie_ids
        else []
    )
    review_map = {r.movie_id: int(r.c) for r in review_rows}

    results = []
    for m, date_watched in rows:
        avg = rating_map.get(m.movie_id)
        results.append(
            {
                "movie_id": m.movie_id,
                "title": m.title,
                "media_type": m.media_type,
                "genre": [g.name for g in m.genres],
                "average_rating": round(avg, 2) if avg is not None else None,
                "number_of_reviews": review_map.get(m.movie_id, 0),
                "actors": [a.name for a in m.actors],
                "date_watched": date_watched.date().isoformat(),
            }
        )

    return results


# Anthony #8.11: account creation + user search endpoints
class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)


@router.post("")
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter((User.username == body.username) | (User.email == body.email))
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already in use")
    user = User(username=body.username, email=body.email)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email already in use")
    return {"user_id": user.user_id, "username": user.username, "email": user.email}


@router.get("/search")
def search_users(
    username: str = Query(
        ..., min_length=1, description="Partial username to search for"
    ),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    users = (
        db.query(User).filter(User.username.ilike(f"%{username}%")).limit(limit).all()
    )
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    return [{"user_id": u.user_id, "username": u.username} for u in users]


# Anthony #7.1: list a specific user's reviews / ratings
@router.get("/{user_id}/reviews")
def user_reviews(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    rows = (
        db.query(Review, Movie.title, Rating.rating)
        .join(Movie, Movie.movie_id == Review.movie_id)
        .outerjoin(
            Rating,
            (Rating.movie_id == Review.movie_id) & (Rating.user_id == Review.user_id),
        )
        .filter(Review.user_id == user_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return [
        {
            "movie_id": r.movie_id,
            "title": title,
            "review_text": r.review_text,
            "contains_spoilers": r.contains_spoilers,
            "rating": rating,
            "created_at": r.created_at,
        }
        for r, title, rating in rows
    ]


@router.get("/{user_id}/ratings")
def user_ratings(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    rows = (
        db.query(Rating, Movie.title)
        .join(Movie, Movie.movie_id == Rating.movie_id)
        .filter(Rating.user_id == user_id)
        .order_by(Rating.created_at.desc())
        .all()
    )
    return [
        {
            "movie_id": r.movie_id,
            "title": title,
            "rating": r.rating,
            "created_at": r.created_at,
        }
        for r, title in rows
    ]


# COMPLEX ENDPOINT #2: /users/{user_id}/stats/dashboard
# Avery #12 product idea #1)
# Aggregates a user's activity into a single dashboard that the client would have had to compute themselves by paging through watch history,
# ratings, and reviews. Combines: totals, top genres with share-of-watch, top actors, recent activity (joined with the user's own ratings), and watch streaks.
DASHBOARD_PERIODS = {
    "all": None,
    "year": timedelta(days=365),
    "month": timedelta(days=30),
}


@router.get("/{user_id}/stats/dashboard")
def user_stats_dashboard(
    user_id: int,
    period: str = Query("all", description="all | year | month"),
    media_type: Optional[str] = Query(None, description="Optional movie/tv filter"),
    top_n: int = Query(
        5, ge=1, le=20, description="How many top genres/actors to return"
    ),
    recent_n: int = Query(
        5, ge=1, le=20, description="How many recent activity entries"
    ),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if period not in DASHBOARD_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Allowed: {sorted(DASHBOARD_PERIODS.keys())}",
        )
    if media_type is not None and media_type not in ALLOWED_MEDIA_TYPE:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media_type. Allowed: {sorted(ALLOWED_MEDIA_TYPE)}",
        )

    delta = DASHBOARD_PERIODS[period]
    cutoff = datetime.now(timezone.utc) - delta if delta else None

    def filter_watch(q):
        q = q.filter(WatchHistory.user_id == user_id)
        if cutoff is not None:
            q = q.filter(WatchHistory.date_watched >= cutoff)
        return q

    titles_q = filter_watch(db.query(func.count(func.distinct(WatchHistory.movie_id))))
    if media_type is not None:
        titles_q = titles_q.join(Movie, Movie.movie_id == WatchHistory.movie_id).filter(
            Movie.media_type == media_type
        )
    titles_watched = titles_q.scalar() or 0

    reviews_q = db.query(func.count(Review.review_id)).filter(Review.user_id == user_id)
    if cutoff is not None:
        reviews_q = reviews_q.filter(Review.created_at >= cutoff)
    if media_type is not None:
        reviews_q = reviews_q.join(Movie, Movie.movie_id == Review.movie_id).filter(
            Movie.media_type == media_type
        )
    reviews_written = reviews_q.scalar() or 0

    ratings_q = db.query(
        func.count(Rating.rating_id),
        func.avg(Rating.rating),
    ).filter(Rating.user_id == user_id)
    if cutoff is not None:
        ratings_q = ratings_q.filter(Rating.created_at >= cutoff)
    if media_type is not None:
        ratings_q = ratings_q.join(Movie, Movie.movie_id == Rating.movie_id).filter(
            Movie.media_type == media_type
        )
    rating_count, avg_rating = ratings_q.one()
    rating_count = rating_count or 0
    avg_rating = round(float(avg_rating), 2) if avg_rating is not None else None

    genre_q = (
        filter_watch(
            db.query(
                Genre.name, func.count(func.distinct(WatchHistory.movie_id)).label("c")
            )
        )
        .join(Movie, Movie.movie_id == WatchHistory.movie_id)
        .join(Movie.genres)
    )
    if media_type is not None:
        genre_q = genre_q.filter(Movie.media_type == media_type)
    genre_rows = (
        genre_q.group_by(Genre.name)
        .order_by(func.count(func.distinct(WatchHistory.movie_id)).desc())
        .limit(top_n)
        .all()
    )
    total_for_share = titles_watched or 1
    top_genres = [
        {"genre": g, "count": int(c), "share": round(int(c) / total_for_share, 2)}
        for g, c in genre_rows
    ]

    actor_q = (
        filter_watch(
            db.query(
                Actor.name, func.count(func.distinct(WatchHistory.movie_id)).label("c")
            )
        )
        .join(Movie, Movie.movie_id == WatchHistory.movie_id)
        .join(Movie.actors)
    )
    if media_type is not None:
        actor_q = actor_q.filter(Movie.media_type == media_type)
    actor_rows = (
        actor_q.group_by(Actor.name)
        .order_by(func.count(func.distinct(WatchHistory.movie_id)).desc())
        .limit(top_n)
        .all()
    )
    top_actors = [{"actor": a, "count": int(c)} for a, c in actor_rows]

    latest_watch_subq = (
        db.query(
            WatchHistory.movie_id.label("movie_id"),
            func.max(WatchHistory.date_watched).label("latest_date"),
        )
        .filter(WatchHistory.user_id == user_id)
        .group_by(WatchHistory.movie_id)
        .subquery()
    )
    recent_q = (
        db.query(Movie, latest_watch_subq.c.latest_date, Rating.rating)
        .join(latest_watch_subq, latest_watch_subq.c.movie_id == Movie.movie_id)
        .outerjoin(
            Rating, (Rating.movie_id == Movie.movie_id) & (Rating.user_id == user_id)
        )
    )
    if media_type is not None:
        recent_q = recent_q.filter(Movie.media_type == media_type)
    recent_rows = (
        recent_q.order_by(latest_watch_subq.c.latest_date.desc()).limit(recent_n).all()
    )
    recent_activity = [
        {
            "movie_id": m.movie_id,
            "title": m.title,
            "date_watched": d.date().isoformat() if d else None,
            "your_rating": rating,
        }
        for m, d, rating in recent_rows
    ]

    now_utc = datetime.now(timezone.utc)
    week_ago = now_utc - timedelta(days=7)
    current_week_count = (
        db.query(func.count(WatchHistory.watch_history_id))
        .filter(WatchHistory.user_id == user_id, WatchHistory.date_watched >= week_ago)
        .scalar()
        or 0
    )

    watch_dates = (
        db.query(WatchHistory.date_watched)
        .filter(WatchHistory.user_id == user_id)
        .all()
    )
    week_counts: dict = {}
    for (d,) in watch_dates:
        if d is None:
            continue
        iso_year, iso_week, _ = d.isocalendar()
        key = (iso_year, iso_week)
        week_counts[key] = week_counts.get(key, 0) + 1
    longest_week_count = max(week_counts.values()) if week_counts else 0

    return {
        "user_id": user_id,
        "username": user.username,
        "period": period,
        "cutoff": cutoff.isoformat() if cutoff else None,
        "totals": {
            "titles_watched": int(titles_watched),
            "reviews_written": int(reviews_written),
            "ratings_given": int(rating_count),
            "avg_rating_given": avg_rating,
        },
        "top_genres": top_genres,
        "top_actors": top_actors,
        "recent_activity": recent_activity,
        "streaks": {
            "current_week_watch_count": int(current_week_count),
            "longest_week_watch_count": int(longest_week_count),
        },
    }
