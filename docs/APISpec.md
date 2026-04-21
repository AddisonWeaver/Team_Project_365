## 1. Get Movie Details by Title - /movies/search (GET)
This endpoint lets users search for a movie by its title and get details like genre, rating, actors, and number of reviews.

Query Parameters:

- `title` (required): The name of the movie
- `user_id` (optional): Used to check if the user has already watched the movie

Example Request:
GET /movies/search?title=Inception&user_id=101

Response:
{
  "movie_id": 1,
  "title": "Inception",
  "media_type": "movie",
  "genre": ["Action", "Sci-Fi"],
  "average_rating": 4.7,
  "number_of_reviews": 200,
  "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
  "watched": false
}


## 2. Add Review of Movie - /movies/{movie_id}/reviews (POST)
This endpoint lets a user write a review for a specific movie. The review is saved and can be seen by other users.

Request:
{
  "user_id": 101,
  "review_text": "Really cool concept and amazing visuals.",
  "contains_spoilers": false
}

Response:
{
  "review_id": 1,
  "message": "Review added successfully"
}


## 3. Add Rating to Movie - /movies/{movie_id}/ratings (POST)
This endpoint lets a user add a rating (integer value between 1 and 5, inclusive) for a specific movie. The rating is saved and can be seen by other users.

Request:
{
  "user_id": 101,
  "rating": 3
}

Response:
{
  "rating_id": 3,
  "message": "Rating added successfully"
}
