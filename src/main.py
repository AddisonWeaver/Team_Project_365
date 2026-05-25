from fastapi import FastAPI
from src.api.routers import movies, ratings, reviews, users

app = FastAPI(
    title="Entertainment Tracker API",
    description="A backend API for cataloging movies and TV shows, with reviews, ratings, and watch history.",
    version="1.0.0",
)

app.include_router(movies.router)
app.include_router(users.router)
app.include_router(ratings.router)
app.include_router(reviews.router)
# Avery #9.1 / #10.1 / Anthony #8.7: canonical /movies/{movie_id}/(reviews|ratings) paths
app.include_router(reviews.movies_alias_router)
app.include_router(ratings.movies_alias_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to the Entertainment Tracker API. Visit /docs for interactive documentation."
    }
