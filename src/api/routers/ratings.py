from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

import sqlalchemy
from src import database as db
from src.database import get_db
from src.models import Movie, Rating

router = APIRouter(prefix="/ratings", tags=["ratings"])


class RatingCreate(BaseModel):
    user_id: int
    rating: int


class FormattedRating(BaseModel):
    username: str
    review_text: str


@router.post("/{movie_id}/ratings")
def add_rating(movie_id: int, body: RatingCreate, db: Session = Depends(get_db)):
    if not 1 <= body.rating <= 5:
        raise HTTPException(
            status_code=400, detail="Rating must be between 1 and 5")
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    rating = Rating(
        movie_id=movie_id,
        user_id=body.user_id,
        rating=body.rating,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return {"rating_id": rating.rating_id, "message": "Rating added successfully"}


@router.get("/{movie_id}/ratings", response_model=List[FormattedRating])
def get_reviews(movie_id: int) -> List[FormattedRating]:

    # return the movie, username, and rating of all ratings for the specified movie
    with db.get_engine().begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                """
                SELECT username, rating
                FROM ratings
                JOIN movies ON movies.movie_id = ratings.movie_id
                JOIN users ON users.user_id = ratings.user_id
                WHERE ratings.movie_id = :id
                ORDER BY ratings.created_at ASC
                """
            ), [{"id": movie_id}]
        ).all()

        ratings = []
        for row in result:
            ratings.append(
                FormattedRating(
                    username=row.username,
                    review_text=row.rating,
                )
            )
    return ratings
