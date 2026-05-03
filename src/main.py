from fastapi import FastAPI
from src.api.routers import movies, users

app = FastAPI(
    title="Entertainment Tracker API",
    description="A backend API for cataloging movies and TV shows, with reviews, ratings, and watch history.",
    version="1.0.0",
)

app.include_router(movies.router)
app.include_router(users.router)


@app.get("/")
def root():
    return {"message": "Welcome to the Entertainment Tracker API. Visit /docs for interactive documentation."}
