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


## 4. Filter Movies by Genre - /movies/filter/genre (GET)
This endpoint lets users filter movies by genre attribute.

Query Parameters:

- `genre` (required): The name of the movie
- `user_id` (optional): Used to check if the user has already watched any of the movies
- `limit` (optional): Used to limit the number of movies that show up after the filter has been applied

Example Request:
GET /movies/filter?genre=Action&user_id=101&limit=2

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
{
  "movie_id": 17,
  "title": "Naked Gun",
  "media_type": "movie",
  "genre": ["Action", "Comedy"],
  "average_rating": 3.2,
  "number_of_reviews": 56,
  "actors": ["Pamela Anderson", "Liam Neeson"],
  "watched": false
}

## 5. Get Movies Watched by User — /users/{user_id}/watch-history (GET)

This endpoint returns the list of movies a specific user has already watched. It can be used to show watch history, avoid recommending already watched titles, or filter recommendation results.

Path Parameters:

user_id (required): The ID of the user

Query Parameters:

media_type (optional): Filter by movie or tv
limit (optional): Maximum number of watched titles to return
sort (optional): Sort order such as recent, rating, or title

Example Request:
GET /users/101/watch-history?media_type=movie&limit=10&sort=recent

[
  {
    "movie_id": 1,
    "title": "Inception",
    "media_type": "movie",
    "genre": ["Action", "Sci-Fi"],
    "average_rating": 4.7,
    "number_of_reviews": 200,
    "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
    "date_watched": "2026-04-18"
  },
  {
    "movie_id": 12,
    "title": "Interstellar",
    "media_type": "movie",
    "genre": ["Adventure", "Drama", "Sci-Fi"],
    "average_rating": 4.8,
    "number_of_reviews": 340,
    "actors": ["Matthew McConaughey", "Anne Hathaway"],
    "date_watched": "2026-04-10"
  }
]

## 6. Add Movie to Watch History — /users/{user_id}/watch-history (POST)

This endpoint lets a user mark a movie as watched by adding it to their watch history.

Path Parameters:

user_id (required): The ID of the user
Request: {
  "movie_id": 1,
  "date_watched": "2026-04-18"
}

Response: {
  "watch_history_id": 55,
  "message": "Movie added to watch history successfully"
}
