# Example Workflow

## Registered User Adds a Movie to Watch History and Views Watched Movies

This flow connects to the user story:
> As a registered user, I want to mark movies or TV shows as watched, so that I can keep track of what I have already seen and get better recommendations.

Addie is a registered user who just finished watching Top Gun and wants to add it to her watch history. First, Addie searches for the movie by calling GET /movies/search?title=Top%20Gun&user_id=1. The system returns the movie details, including that the movie has movie_id = 1.

Addie then adds the movie to her watch history. To do this she:
- calls POST /users/1/watch-history
- includes the movie_id
- includes the date_watched

The system saves the movie to her watch history and returns a message saying the movie was added successfully.

Later, Addie wants to see all the movies she has watched. She calls GET /users/1/watch-history?media_type=movie&sort=recent. The system returns her watched movie list, including Top Gun.

# Testing Results

## Step 1 — Search for the movie "Top Gun"

curl -X 'GET' \
  'https://team-project-365.onrender.com/movies/search?title=Top%20Gun&user_id=1' \
  -H 'accept: application/json'

Response:
{"movie_id":1,"title":"Top Gun","media_type":"movie","genre":["Action","Drama"],"average_rating":null,"number_of_reviews":0,"actors":["Tom Cruise","Val Kilmer"],"watched":false}

## Step 2 — Add Top Gun to watch history (POST — modifies database)

curl -X 'POST' \
  'https://team-project-365.onrender.com/users/1/watch-history' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"movie_id": 1, "date_watched": "2026-04-18"}'

Response:
{"watch_history_id":1,"message":"Movie added to watch history successfully"}

## Step 3 — View watch history

curl -X 'GET' \
  'https://team-project-365.onrender.com/users/1/watch-history?media_type=movie&sort=recent' \
  -H 'accept: application/json'

Response:
[{"movie_id":1,"title":"Top Gun","media_type":"movie","genre":["Action","Drama"],"average_rating":null,"number_of_reviews":0,"actors":["Tom Cruise","Val Kilmer"],"date_watched":"2026-04-18"}]