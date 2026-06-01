import math
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, select, case
from typing import Optional, List
from src.database import get_db
from src.models import Movie, Genre, Actor, Review, Rating, WatchHistory, User

router = APIRouter(prefix="/movies", tags=["movies"])


def _movies_to_dicts(movies, db: Session, user_id: Optional[int] = None) -> List[dict]:
    # Jared #1.4,5 / Anthony #5.2 / Avery #9.2: batch aggregate queries
    if not movies:
        return []
    movie_ids = [m.movie_id for m in movies]

    rating_rows = (
        db.query(
            Rating.movie_id,
            func.avg(Rating.rating).label("avg_r"),
            func.count(Rating.rating_id).label("rating_count"),
        )
        .filter(Rating.movie_id.in_(movie_ids))
        .group_by(Rating.movie_id)
        .all()
    )
    rating_map = {
        r.movie_id: (float(r.avg_r), int(r.rating_count)) for r in rating_rows
    }

    review_rows = (
        db.query(Review.movie_id, func.count(Review.review_id).label("review_count"))
        .filter(Review.movie_id.in_(movie_ids))
        .group_by(Review.movie_id)
        .all()
    )
    review_map = {r.movie_id: int(r.review_count) for r in review_rows}

    watched_ids: set = set()
    if user_id is not None:
        watched_rows = (
            db.query(WatchHistory.movie_id)
            .filter(
                WatchHistory.user_id == user_id, WatchHistory.movie_id.in_(movie_ids)
            )
            .distinct()
            .all()
        )
        watched_ids = {w.movie_id for w in watched_rows}

    out = []
    for m in movies:
        avg, _ = rating_map.get(m.movie_id, (None, 0))
        out.append(
            {
                "movie_id": m.movie_id,
                "title": m.title,
                "media_type": m.media_type,
                "genre": [g.name for g in m.genres],
                "average_rating": round(avg, 2) if avg is not None else None,
                "number_of_reviews": review_map.get(m.movie_id, 0),
                "actors": [a.name for a in m.actors],
                "watched": m.movie_id in watched_ids,
            }
        )
    return out


def _require_user(db: Session, user_id: Optional[int]) -> None:
    # Jared #1.3 / Anthony #5.3 / Avery #9.5: validate user_id exists when provided
    if user_id is None:
        return
    if not db.query(User).filter(User.user_id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/search")
def search_movie(
    title: str = Query(..., description="Title of the movie to search for"),
    user_id: Optional[int] = Query(None),
    # Jared #1.6 / Anthony #8.12: cap limit
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _require_user(db, user_id)
    # Jared #1.1 / Anthony #5.1 / Avery #10.4: return list of matches instead of .first()
    movies = db.query(Movie).filter(Movie.title.ilike(f"%{title}%")).limit(limit).all()
    if not movies:
        raise HTTPException(status_code=404, detail="Movie not found")
    return _movies_to_dicts(movies, db, user_id=user_id)


@router.get("")
def list_movies(
    # Anthony #5.6: page through all movies; bounded limit (Jared #1.6 / Anthony #8.12)
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    _require_user(db, user_id)
    movies = (
        db.query(Movie).order_by(Movie.movie_id.asc()).offset(offset).limit(limit).all()
    )
    return _movies_to_dicts(movies, db, user_id=user_id)


# Avery #10.2: spec said GET /movies/filter?genre=...; expose both paths so spec-following clients work
@router.get("/filter")
@router.get("/filter/genre")
def filter_by_genre(
    genre: str = Query(...),
    user_id: Optional[int] = Query(None),
    # Jared #1.6 / Anthony #8.12: cap limit
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _require_user(db, user_id)
    movies = (
        db.query(Movie)
        .join(Movie.genres)
        .filter(Genre.name.ilike(f"%{genre}%"))
        .limit(limit)
        .all()
    )
    # Anthony #8.9: return 404 when no matches instead of an empty list
    if not movies:
        raise HTTPException(
            status_code=404, detail=f"No movies found for genre '{genre}'"
        )
    return _movies_to_dicts(movies, db, user_id=user_id)


def _popularity_map(movie_ids: list, db: Session) -> dict:
    if not movie_ids:
        return {}
    rows = (
        db.query(
            Rating.movie_id,
            func.avg(Rating.rating).label("avg_r"),
            func.count(Rating.rating_id).label("rating_count"),
        )
        .filter(Rating.movie_id.in_(movie_ids))
        .group_by(Rating.movie_id)
        .all()
    )
    return {r.movie_id: (float(r.avg_r), int(r.rating_count)) for r in rows}


# Avery #9.3: popularity score expression that SQL can ORDER BY directly.
def _popularity_score_expr():
    return (
        func.coalesce(func.avg(Rating.rating), 0)
        * func.log(func.count(Rating.rating_id) + 1)
        * 10
    )


@router.get("/recommendations/popular")
def popular_recommendations(
    # Jared #1.6 / Anthony #8.12: cap limit
    limit: int = Query(10, ge=1, le=100),
    genre: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    exclude_watched: bool = Query(False),
    db: Session = Depends(get_db),
):
    _require_user(db, user_id)
    # Avery #9.3: compute popularity score and apply LIMIT in SQL so we don't load every movie
    # Jared #1.2: popularity score uses rating count (not review count)
    score = _popularity_score_expr().label("popularity_score")
    q = db.query(Movie, score).outerjoin(Rating, Rating.movie_id == Movie.movie_id)
    if genre:
        q = q.join(Movie.genres).filter(Genre.name.ilike(f"%{genre}%"))
    if exclude_watched and user_id is not None:
        from sqlalchemy import select

        watched_select = select(WatchHistory.movie_id).where(
            WatchHistory.user_id == user_id
        )
        q = q.filter(~Movie.movie_id.in_(watched_select))
    rows = q.group_by(Movie.movie_id).order_by(score.desc()).limit(limit).all()
    movies = [m for m, _ in rows]
    scores = {m.movie_id: float(s) for m, s in rows}
    base = _movies_to_dicts(movies, db, user_id=user_id)
    for d in base:
        d["popularity_score"] = round(scores.get(d["movie_id"], 0.0), 1)
    return base


# ENDPOINT #1: /movies/trending
# Jared #4 product idea #2)
# It joins activity from THREE tables (ratings, reviews, watch_history) inside a configurable time window,
# it then computes a weighted trending score per movie in SQL, before letting the caller filter
# by genre / media_type / period, and returns the contributing counts.
TRENDING_PERIODS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "all": None,
}


@router.get("/trending")
def trending_movies(
    period: str = Query("7d", description="Time window: 24h, 7d, 30d, or all"),
    genre: Optional[str] = Query(None, description="Restrict to a single genre"),
    media_type: Optional[str] = Query(None, description="movie or tv"),
    limit: int = Query(10, ge=1, le=50),
    user_id: Optional[int] = Query(
        None, description="If set, include 'watched' flag for this user"
    ),
    db: Session = Depends(get_db),
):
    if period not in TRENDING_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Allowed: {sorted(TRENDING_PERIODS.keys())}",
        )
    if media_type is not None and media_type not in ("movie", "tv"):
        raise HTTPException(
            status_code=400, detail="media_type must be 'movie' or 'tv'"
        )
    _require_user(db, user_id)

    delta = TRENDING_PERIODS[period]
    cutoff = datetime.now(timezone.utc) - delta if delta else None

    rating_q = db.query(
        Rating.movie_id.label("movie_id"),
        func.count(Rating.rating_id).label("recent_ratings"),
        func.avg(Rating.rating).label("recent_avg_rating"),
    )
    if cutoff is not None:
        rating_q = rating_q.filter(Rating.created_at >= cutoff)
    rating_subq = rating_q.group_by(Rating.movie_id).subquery()

    review_q = db.query(
        Review.movie_id.label("movie_id"),
        func.count(Review.review_id).label("recent_reviews"),
    )
    if cutoff is not None:
        review_q = review_q.filter(Review.created_at >= cutoff)
    review_subq = review_q.group_by(Review.movie_id).subquery()

    watch_q = db.query(
        WatchHistory.movie_id.label("movie_id"),
        func.count(WatchHistory.watch_history_id).label("recent_watches"),
    )
    if cutoff is not None:
        watch_q = watch_q.filter(WatchHistory.date_watched >= cutoff)
    watch_subq = watch_q.group_by(WatchHistory.movie_id).subquery()

    # Trending score = ratings*2 + reviews*3 + watches*1, multiplied by avg rating
    # Baseline is 1
    score_expr = (
        (func.coalesce(rating_subq.c.recent_ratings, 0) * 2)
        + (func.coalesce(review_subq.c.recent_reviews, 0) * 3)
        + (func.coalesce(watch_subq.c.recent_watches, 0) * 1)
    ) * case(
        (rating_subq.c.recent_avg_rating != None, rating_subq.c.recent_avg_rating),  # noqa: E711
        else_=1.0,
    )

    q = (
        db.query(
            Movie,
            func.coalesce(rating_subq.c.recent_ratings, 0).label("recent_ratings"),
            func.coalesce(rating_subq.c.recent_avg_rating, 0).label(
                "recent_avg_rating"
            ),
            func.coalesce(review_subq.c.recent_reviews, 0).label("recent_reviews"),
            func.coalesce(watch_subq.c.recent_watches, 0).label("recent_watches"),
            score_expr.label("trending_score"),
        )
        .outerjoin(rating_subq, rating_subq.c.movie_id == Movie.movie_id)
        .outerjoin(review_subq, review_subq.c.movie_id == Movie.movie_id)
        .outerjoin(watch_subq, watch_subq.c.movie_id == Movie.movie_id)
    )
    if media_type is not None:
        q = q.filter(Movie.media_type == media_type)
    if genre is not None:
        q = q.join(Movie.genres).filter(Genre.name.ilike(f"%{genre}%"))

    rows = q.order_by(score_expr.desc()).limit(limit).all()

    watched_ids = set()
    if user_id is not None and rows:
        movie_ids = [m.movie_id for m, *_ in rows]
        watched_rows = (
            db.query(WatchHistory.movie_id)
            .filter(
                WatchHistory.user_id == user_id, WatchHistory.movie_id.in_(movie_ids)
            )
            .distinct()
            .all()
        )
        watched_ids = {w.movie_id for w in watched_rows}

    results = []
    for m, n_ratings, avg_r, n_reviews, n_watches, score in rows:
        results.append(
            {
                "movie_id": m.movie_id,
                "title": m.title,
                "media_type": m.media_type,
                "release_year": m.release_year,
                "genre": [g.name for g in m.genres],
                "actors": [a.name for a in m.actors],
                "watched": m.movie_id in watched_ids,
                "trending_score": round(float(score), 2),
                "recent_activity": {
                    "ratings": int(n_ratings),
                    "avg_rating": round(float(avg_r), 2) if avg_r else None,
                    "reviews": int(n_reviews),
                    "watches": int(n_watches),
                },
            }
        )
    return {
        "period": period,
        "cutoff": cutoff.isoformat() if cutoff else None,
        "count": len(results),
        "results": results,
    }


# Anthony #7.2: recommendations filtered by release year (Jared #2.8 added the column)
@router.get("/recommendations/year")
def recommendations_by_year(
    year: int = Query(
        ..., ge=1888, le=2031, description="Release year; must not be in the future"
    ),
    limit: int = Query(10, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    exclude_watched: bool = Query(False),
    db: Session = Depends(get_db),
):
    # Anthony #7.2: extra safety reject years that have not happened yet
    from datetime import date

    if year > date.today().year:
        raise HTTPException(status_code=400, detail="year cannot be in the future")
    _require_user(db, user_id)
    movies = db.query(Movie).filter(Movie.release_year == year).all()
    if exclude_watched and user_id is not None:
        rows = (
            db.query(WatchHistory.movie_id)
            .filter(WatchHistory.user_id == user_id)
            .distinct()
            .all()
        )
        watched_ids = {r.movie_id for r in rows}
        movies = [m for m in movies if m.movie_id not in watched_ids]
    base = _movies_to_dicts(movies, db, user_id=user_id)
    rmap = _popularity_map([m.movie_id for m in movies], db)
    for d in base:
        avg, count = rmap.get(d["movie_id"], (None, 0))
        d["popularity_score"] = (
            round(avg * math.log1p(count) * 10, 1) if avg and count else 0.0
        )
    base.sort(key=lambda x: x["popularity_score"], reverse=True)
    return base[:limit]


@router.get("/recommendations/by-actor")
def recommendations_by_actor(
    actor: str = Query(...),
    # Jared #1.6 / Anthony #8.12: cap limit
    limit: int = Query(10, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    exclude_watched: bool = Query(False),
    db: Session = Depends(get_db),
):
    _require_user(db, user_id)
    # Avery #9.3: SQL side score + LIMIT
    # Jared #1.2: popularity score uses rating count
    score = _popularity_score_expr().label("popularity_score")
    q = (
        db.query(Movie, score)
        .join(Movie.actors)
        .filter(Actor.name.ilike(f"%{actor}%"))
        .outerjoin(Rating, Rating.movie_id == Movie.movie_id)
    )
    if exclude_watched and user_id is not None:
        from sqlalchemy import select

        watched_select = select(WatchHistory.movie_id).where(
            WatchHistory.user_id == user_id
        )
        q = q.filter(~Movie.movie_id.in_(watched_select))
    rows = q.group_by(Movie.movie_id).order_by(score.desc()).limit(limit).all()
    movies = [m for m, _ in rows]
    scores = {m.movie_id: float(s) for m, s in rows}
    base = _movies_to_dicts(movies, db, user_id=user_id)
    for d in base:
        d["popularity_score"] = round(scores.get(d["movie_id"], 0.0), 1)
    return base
