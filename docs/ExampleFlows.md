## Example Flow: Registered User Writes a Review for a Movie

This flow connects to the user story:  
**As a registered user, I want to write a review for a movie or TV show, so that I can share my thoughts with other users.**

Misha is a registered user who wants to write a review for the movie *Inception* after watching it. First, Misha searches for the movie by calling `GET /movies/search?title=Inception&user_id=101`. The system returns the movie details, including that the movie has `movie_id = 1`.

Misha then writes and submits her review. To do this she:

- calls `POST /movies/1/reviews`
- includes her `user_id`
- includes her `review_text`
- includes whether the review `contains_spoilers`

The system saves her review and returns a message saying the review was added successfully.

This flow shows how a registered user can search for a movie and submit a review for it.

## Example Flow: Registered User Leaves a Rating on a Movie

This flow connects to the user story:  
**As a registered user, I want to rate a movie or TV show, so that I can contribute to its overall ranking and track my opinions.**

Alice is a registered user who wants to leave a rating on "Hail Mary" after watching it in theaters. First, Alice searches for the movie by calling `GET /movies/search?title=HailMary&user_id=115`. The system returns the movie details, including that the movie has `movie_id = 135`.

Alice decides on a number to rate the movie out of five, then adds her rating. To do this she:

- calls `POST /movies/135/ratings`
- includes her `user_id`
- includes her `rating` (an integer between 1 and 5, inclusive)

The system saves her rating and returns a message saying the rating was added successfully.

This flow shows how a registered user can search for a movie and rate it.

## Example Flow: Registered User Adds a Movie to Watch History and Views Watched Movies
This flow connects to the user story:
As a registered user, I want to mark movies or TV shows as watched, so that I can keep track of what I have already seen and get better recommendations.

Addie is a registered user who just finished watching Top Gun and wants to add it to her watch history. First, Addie searches for the movie by calling GET /movies/search?title=Top%20Gun&user_id=101. The system returns the movie details, including that the movie has movie_id = 1.

Addie then adds the movie to her watch history. To do this she:

calls POST /users/101/watch-history
includes the movie_id
includes the date_watched

The system saves the movie to her watch history and returns a message saying the movie was added successfully.

Later, Addie wants to see all the movies she has watched. She calls GET /users/101/watch-history?media_type=movie&sort=recent. The system returns her watched movie list, including Top Gun.

This flow shows how a registered user can track movies they have watched and retrieve their watch history.
