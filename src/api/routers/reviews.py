import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
from typing import List, Optional

import sqlalchemy
from src.database import get_db
from src.models import Movie, Review, User, WatchHistory

router = APIRouter(prefix="/reviews", tags=["reviews"])
# Avery #9.1 / #10.1 / Anthony #8.7: spec promised /movies/{movie_id}/reviews;
movies_alias_router = APIRouter(prefix="/movies", tags=["reviews"])

# Jared #1.12 / Anthony #8.3 / Avery #9.6: enforce review text length bounds (rejects empty + very long reviews)
REVIEW_MIN_LEN = 1
REVIEW_MAX_LEN = 2000


class ReviewCreate(BaseModel):
    user_id: int
    review_text: str = Field(..., min_length=REVIEW_MIN_LEN,
                             max_length=REVIEW_MAX_LEN)
    contains_spoilers: bool = False


class FormattedReview(BaseModel):
    # Anthony #5.7 / #5.9: include date and the user's rating with the review
    username: str
    review_text: str
    contains_spoilers: bool
    created_at: datetime.datetime
    rating: Optional[int] = None


@router.post("/{movie_id}/reviews")
def add_review(movie_id: int, body: ReviewCreate, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    # Jared #1.11 / Anthony #5.3 / Avery #9.5: validate user exists before creating review
    user = db.query(User).filter(User.user_id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Jared #2.3 / Avery #9.7: one review per user per movie update existing instead
    existing = (
        db.query(Review)
        .filter(Review.movie_id == movie_id, Review.user_id == body.user_id)
        .first()
    )
    try:
        if existing:
            existing.review_text = body.review_text
            existing.contains_spoilers = body.contains_spoilers
            db.commit()
            db.refresh(existing)
            review_id = existing.review_id
            message = "Review updated successfully"
        else:
            review = Review(
                movie_id=movie_id,
                user_id=body.user_id,
                review_text=body.review_text,
                contains_spoilers=body.contains_spoilers,
            )
            db.add(review)
            db.commit()  # Jared #1.15 / Avery #9.13: wrap commit in try/except for clearer errors
            db.refresh(review)
            review_id = review.review_id
            message = "Review added successfully"

        # Anthony #5.8: automatically add to watch_history if the user hasn't marked it watched yet
        already_watched = (
            db.query(WatchHistory)
            .filter(
                WatchHistory.user_id == body.user_id, WatchHistory.movie_id == movie_id
            )
            .first()
        )
        if not already_watched:
            db.add(
                WatchHistory(
                    user_id=body.user_id,
                    movie_id=movie_id,
                    date_watched=datetime.datetime.now(datetime.timezone.utc),
                )
            )
            db.commit()

        return {"review_id": review_id, "message": message}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not save review")


@router.get("/{movie_id}/reviews", response_model=List[FormattedReview])
def get_reviews(
    movie_id: int,
    # Jared #1.13 / Avery #10.20: default False, optional
    include_spoilers: bool = Query(False),
    db: Session = Depends(get_db),
) -> List[FormattedReview]:
    # Jared #1.14: check movie exists before returning results
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Anthony #5.5 / Avery #9.10: include_spoilers=true returns ALL reviews;
    # Anthony #5.7 / #5.9: include review date and the user's rating with each review.
    result = db.execute(
        sqlalchemy.text(
            """
            SELECT u.username AS username,
                   r.review_text AS review_text,
                   r.contains_spoilers AS contains_spoilers,
                   r.created_at AS created_at,
                   rt.rating AS rating
            FROM reviews r
            JOIN movies m ON m.movie_id = r.movie_id
            JOIN users u ON u.user_id = r.user_id
            LEFT JOIN ratings rt ON rt.user_id = r.user_id AND rt.movie_id = r.movie_id
            WHERE r.movie_id = :id AND (:include_spoilers OR r.contains_spoilers = false)
            ORDER BY r.created_at ASC
            """
        ),
        {"id": movie_id, "include_spoilers": include_spoilers},
    ).all()

    reviews = []
    for row in result:
        reviews.append(
            FormattedReview(
                username=row.username,
                review_text=row.review_text,
                contains_spoilers=bool(row.contains_spoilers),
                created_at=row.created_at,
                rating=row.rating,
            )
        )
    return reviews


# Avery #9.1 / #10.1 / Anthony #8.7: register the same handlers under the canonical
# /movies/{movie_id}/reviews paths the API spec describes.
movies_alias_router.add_api_route(
    "/{movie_id}/reviews", add_review, methods=["POST"])
movies_alias_router.add_api_route(
    "/{movie_id}/reviews",
    get_reviews,
    methods=["GET"],
    response_model=List[FormattedReview],
)
