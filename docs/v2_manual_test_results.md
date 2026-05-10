# Example Workflow #1

## Registered User Writes a Review for a Movie

This flow connects to the user story:
> As a registered user, I want to write a review for a movie or TV show, so that I can share my thoughts with other users.

Addie is a registered user who wants to write a review for the movie *Top Gun* after watching it. First, Addie searches for the movie by calling GET /movies/search?title=Top%20Gun&user_id=1. The system returns the movie details, including that the movie has movie_id = 1.

Addie then writes and submits her review. To do this she:

- calls `POST /movies/1/reviews`
- includes her `user_id`
- includes her `review_text`
- includes whether the review `contains_spoilers`

The system saves her review and returns a message saying the review was added successfully.

This flow shows how a registered user can search for a movie and submit a review for it.

# Testing Results

## Step 1 — Search for the movie "Top Gun"

curl -X 'GET' \
  'https://team-project-365.onrender.com/movies/search?title=Top%20Gun&user_id=1' \
  -H 'accept: application/json'

Response:
{"movie_id":1,"title":"Top Gun","media_type":"movie","genre":["Action","Drama"],"average_rating":null,"number_of_reviews":0,"actors":["Tom Cruise","Val Kilmer"],"watched":false}

## Step 2 — Add review to Top Gun (POST — modifies database)

curl -X 'POST' \
  'https://team-project-365-ha53.onrender.com/movies/1/reviews' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 1,
  "review_text": "Loved the movie! Would def recommend.",
  "contains_spoilers": false
}'

Response:
{"review_id": 1,"message": "Review added successfully"}

## Step 3 — View updated review count (repeat Search)

curl -X 'GET' \
  'https://team-project-365.onrender.com/movies/search?title=Top%20Gun&user_id=1' \
  -H 'accept: application/json'

Response:
{"movie_id":1,"title":"Top Gun","media_type":"movie","genre":["Action","Drama"],"average_rating":null,"number_of_reviews":1,"actors":["Tom Cruise","Val Kilmer"],"watched":false}

The value of the number_of_reviews attribute has gone up by 1.

# Example Workflow #2

## Registered User Leaves a Rating on a Movie

This flow connects to the user story:
> As a registered user, I want to rate a movie or TV show, so that I can contribute to its overall ranking and track my opinions.

Addie is a registered user who wants to leave a rating on "Top Gun" after watching it in theaters. First, Addie searches for the movie by calling GET /movies/search?title=Top%20Gun&user_id=1. The system returns the movie details, including that the movie has movie_id = 1.

Addie decides on a number to rate the movie out of five, then adds her rating. To do this she:

- calls `POST /movies/1/ratings`
- includes her `user_id`
- includes her `rating` (an integer between 1 and 5, inclusive)

The system saves her rating and returns a message saying the rating was added successfully.

This flow shows how a registered user can search for a movie and rate it.

# Testing Results

## Step 1 — Search for the movie "Top Gun"

curl -X 'GET' \
  'https://team-project-365.onrender.com/movies/search?title=Top%20Gun&user_id=1' \
  -H 'accept: application/json'

Response:
{"movie_id":1,"title":"Top Gun","media_type":"movie","genre":["Action","Drama"],"average_rating":null,"number_of_reviews":1,"actors":["Tom Cruise","Val Kilmer"],"watched":false}

## Step 2 — Add rating on Top Gun (POST — modifies database)

curl -X 'POST' \
  'https://team-project-365-ha53.onrender.com/movies/1/ratings' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 1,
  "rating": 4
}'

Response:
{"rating_id": 1,"message": "Rating added successfully"}

## Step 3 — View update to average rating (repeat Search)

curl -X 'GET' \
  'https://team-project-365.onrender.com/users/1/watch-history?media_type=movie&sort=recent' \
  -H 'accept: application/json'

Response:
{"movie_id":1,"title":"Top Gun","media_type":"movie","genre":["Action","Drama"],"average_rating":4,"number_of_reviews":1,"actors":["Tom Cruise","Val Kilmer"],"watched":false}

The value of average_rating has increased to 4.