from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
from typing import List, Optional

import sqlalchemy
from src.database import get_db
from src.models import Movie, Rating, User

router = APIRouter(prefix="/ratings", tags=["ratings"])
# Avery #9.1 / #10.1 / Anthony #8.7: canonical /movies/{movie_id}/ratings paths from API spec
movies_alias_router = APIRouter(prefix="/movies", tags=["ratings"])


class RatingCreate(BaseModel):
    user_id: int
    rating: int


class FormattedRating(BaseModel):
    username: str
    rating: int


# Anthony #5.10: response now exposes the aggregate alongside the individual ratings
class RatingsResponse(BaseModel):
    average_rating: Optional[float] = None
    rating_count: int
    ratings: List[FormattedRating]


def add_rating(movie_id: int, body: RatingCreate, db: Session = Depends(get_db)):
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    # Jared #1.7 / Anthony #5.3 / Avery #9.5: validate user exists before creating rating
    user = db.query(User).filter(User.user_id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Jared #1.8 / Anthony #5.4 / Avery #9.7: prevent duplicate (user, movie) ratings; update existing instead
    existing = (
        db.query(Rating)
        .filter(Rating.movie_id == movie_id, Rating.user_id == body.user_id)
        .first()
    )
    try:
        if existing:
            existing.rating = body.rating
            db.commit()
            db.refresh(existing)
            return {
                "rating_id": existing.rating_id,
                "message": "Rating updated successfully",
            }
        rating = Rating(
            movie_id=movie_id,
            user_id=body.user_id,
            rating=body.rating,
        )
        db.add(rating)
        db.commit()  # Jared #1.10 / Avery #9.13: wrap commit in try/except for clearer errors
        db.refresh(rating)
        return {"rating_id": rating.rating_id, "message": "Rating added successfully"}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not save rating")


def get_ratings(  # Avery #9.9: renamed from get_reviews to get_ratings
    movie_id: int,
    db: Session = Depends(get_db),
) -> RatingsResponse:
    # Jared #1.9: check movie exists before returning results
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    result = db.execute(
        sqlalchemy.text(
            """
            SELECT username, rating
            FROM ratings
            JOIN movies ON movies.movie_id = ratings.movie_id
            JOIN users ON users.user_id = ratings.user_id
            WHERE ratings.movie_id = :id
            ORDER BY ratings.created_at ASC
            """
        ),
        {"id": movie_id},
    ).all()

    items = [FormattedRating(username=r.username, rating=r.rating) for r in result]
    # Anthony #5.10: include average_rating and rating_count in the response
    if items:
        avg = round(sum(i.rating for i in items) / len(items), 2)
    else:
        avg = None
    return RatingsResponse(
        average_rating=avg,
        rating_count=len(items),
        ratings=items,
    )


# Avery #9.1 / #10.1 / Anthony #8.7: canonical /movies/{movie_id}/ratings paths from API spec
movies_alias_router.add_api_route("/{movie_id}/ratings", add_rating, methods=["POST"])
movies_alias_router.add_api_route(
    "/{movie_id}/ratings",
    get_ratings,
    methods=["GET"],
    response_model=RatingsResponse,
)
