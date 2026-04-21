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
