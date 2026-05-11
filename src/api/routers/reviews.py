from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

import sqlalchemy
from src import database as db
from src.database import get_db
from src.models import Movie, Review

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewCreate(BaseModel):
    user_id: int
    review_text: str
    contains_spoilers: bool = False


class FormattedReview(BaseModel):
    username: str
    review_text: str


@router.post("/{movie_id}/reviews")
def add_review(movie_id: int, body: ReviewCreate, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    review = Review(
        movie_id=movie_id,
        user_id=body.user_id,
        review_text=body.review_text,
        contains_spoilers=body.contains_spoilers,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return {"review_id": review.review_id, "message": "Review added successfully"}


@router.get("/{movie_id}/reviews", response_model=List[FormattedReview])
def get_reviews(movie_id: int, include_spoilers: bool) -> List[FormattedReview]:

    include_spoilers = False if include_spoilers is None else include_spoilers
    # return the movie, username, and review text of all reviews for the specified movie (w or wo spoilers depending on the val of include_spoilers)
    with db.get_engine().begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                """
                SELECT username, review_text
                FROM reviews
                JOIN movies ON movies.movie_id = reviews.movie_id
                JOIN users ON users.user_id = reviews.user_id
                WHERE reviews.movie_id = :id AND contains_spoilers = :spoilers
                ORDER BY reviews.created_at ASC
                """
            ), [{"id": movie_id, "spoilers": include_spoilers}]
        ).all()

        reviews = []
        for row in result:
            reviews.append(
                FormattedReview(
                    username=row.username,
                    review_text=row.review_text,
                )
            )
    return reviews
