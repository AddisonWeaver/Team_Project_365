# Concurrency Control

This document describes three cases where our service would encounter concurrency phenomena if it had no concurrency control protection in place. 
---

## Case 1: Lost Update — Concurrent Rating Updates

### The Phenomenon

A **lost update** occurs when two transactions both read the same row, compute a new value based on that read, and then both write back which causes one transaction's write to silently overwrite the other's.

### How It Occurs in Our Service

Our `POST /movies/{movie_id}/ratings` endpoint allows a user to submit or update a rating for a movie as read then write logic.

1. Read the `ratings` table to check whether a row already exists for `(user_id, movie_id)`.
2. If it exists, update it. If not, insert a new row.

Without proper isolation, two concurrent requests from the same user for the same movie can both pass the "does a row exist?" check before either has committed, leading to a duplicate insert that violates the `uq_ratings_user_movie` unique constraint. Or, if both find an existing row and update it simultaneously, one update overwrites the other with no error raised. The final value in the database reflects whichever transaction committed last, and the earlier write is silently discarded.


### Sequence Diagram

```
User (T1: rating=4)          Database              User (T2: rating=2)
        |                        |                        |
        |-- SELECT rating ------>|                        |
        |   WHERE user=1,        |                        |
        |   movie=10             |                        |
        |<-- (no row found) -----|                        |
        |                        |<-- SELECT rating ------|
        |                        |    WHERE user=1,       |
        |                        |    movie=10            |
        |                        |--> (no row found) ---->|
        |                        |                        |
        |-- INSERT rating=4 ---->|                        |
        |   COMMIT               |                        |
        |<-- OK (rating_id=55) --|                        |
        |                        |<-- INSERT rating=2 ----|
        |                        |    COMMIT              |
        |                        |                        |
        |                   [IntegrityError OR            |
        |                    rating=2 overwrites 4,       |
        |                    T1's write is LOST]          |
```

### What We Do To Ensure Isolation

We can address this with two solutions:

**1. Database-level unique constraint (pessimistic currency control):**
The `ratings` table has a `UniqueConstraint("user_id", "movie_id", name="uq_ratings_user_movie")` defined in `models.py`. This means even if two concurrent transactions both pass the application-level check and attempt to INSERT, the database will reject the second one with an integrity error. Our `try/except SQLAlchemyError` block in `add_rating` catches this and returns a 400, preventing a silent lost update.

**2. Explicit row locking with `SELECT FOR UPDATE`:**
The more robust fix is to add a `FOR UPDATE` lock to the existence check so that the first transaction to read the row holds a lock until it commits, forcing the second transaction to wait:

```python
existing = (
    db.query(Rating)
    .filter(Rating.movie_id == movie_id, Rating.user_id == body.user_id)
    .with_for_update()
    .first()
)
```

This is the best choice because the lost update arises from a **read-then-write** pattern on a specific row. A `FOR UPDATE` lock targets exactly that row and holds it for the duration of the transaction, so no other transaction can read-and-modify the same row at the same time.

---

## Case 2: Phantom Read — Trending Score Calculation

### The Phenomenon

A **phantom read** occurs when the same query is executed twice within a transaction and the second execution returns a different set of rows because another transaction inserted or deleted rows that match the query's filter condition between the two reads. 

### How It Occurs in Our Service

Our `GET /movies/trending` endpoint builds a trending score for each movie by counting recent activity across three separate subqueries with one each against the `ratings`, `reviews`, and `watch_history` tables, all filtered by a time-window cutoff of the last 7 days. From the `READ COMMITTED` isolation level, each statement in the transaction sees a fresh snapshot of committed data at the moment that statement executes. This means the three subqueries can see different states of the database if concurrent writes commit between them.

### Sequence Diagram

```
Client (GET /trending)       Database                 User B (POST review + rating)
        |                        |                               |
        |-- Subquery 1 --------->|                               |
        |   COUNT ratings        |                               |
        |   movie=5 → 10 rows    |                               |
        |<-- recent_ratings=10 --|                               |
        |                        |<-- INSERT rating (movie=5) ---|
        |                        |    COMMIT                     |
        |                        |<-- INSERT review (movie=5) ---|
        |                        |    COMMIT                     |
        |                        |<-- INSERT watch_history ------|
        |                        |    COMMIT                     |
        |-- Subquery 2 --------->|                               |
        |   COUNT reviews        |                               |
        |   movie=5 → NOW 6 rows |                               |
        |   (phantom rows!)      |                               |
        |<-- recent_reviews=6 ---|                               |
        |-- Subquery 3 --------->|                               |
        |   COUNT watches        |                               |
        |   movie=5 → NOW 4 rows |                               |
        |   (phantom rows!)      |                               |
        |<-- recent_watches=4 ---|                               |
        |                        |                               |
        |  trending_score built from inconsistent snapshots:     |
        |  ratings=10 (old), reviews=6 (new), watches=4 (new)   |
        |  → incorrect ranking returned to client                |
```

### What We Do To Ensure Isolation

The best fix is to run the `trending_movies` transaction at **`REPEATABLE READ`** isolation level:

```python
with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
    with conn.begin():
        # all three subqueries execute against the same snapshot
        ...
```

At `REPEATABLE READ`, PostgreSQL takes a consistent snapshot of the database at the start of the transaction and all subsequent reads within that transaction see only that snapshot with new rows committed by other transactions after the snapshot was taken are invisible. This directly prevents phantom reads because the set of rows matching the time-window filter is frozen for the entire duration of the trending calculation, so all three subqueries agree on which activity rows exist.

---

## Case 3: 


---
