# Performance Writeup – Team Project 365 (V5)

---

## 1. Fake Data Modeling

**Python script:** [`generate_fake_data.py`](./generate_fake_data.py)

### Row counts

| Table | Rows | Notes |
|-------|-----:|-------|
| `users` | 10,000 | |
| `movies` | 50,000 | 40k movies, 10k TV |
| `genres` | 25 | fixed lookup |
| `actors` | 20,000 | |
| `movie_genres` | 100,000 | ~2 per title |
| `movie_actors` | 200,000 | ~4 per title |
| `ratings` | 400,000 | |
| `reviews` | 130,000 | |
| `watch_history` | 125,000 | |
| **TOTAL** | **1,035,025** | |

### Why we distributed it this way

We went with 10,000 users because that felt like a realistic early user base for a review service without every possible (user, movie) combo being filled in.

50,000 movies/TV titles to have a large catalog size. Too few and genre/actor filtering is boring to test. We split it 40k movies and 10k TV series since movies just outnumber TV shows on most platforms so it made sense to weight it that way.

Ratings are the biggest table at 400,000 rows because that's the main action users take. We made the distribution intentionally uneven since the top 10% of movies get about 60% of all ratings. Ratings skew toward 3-5 stars because people mostly rate stuff they actually watched and liked.

Reviews are about 1 in 3 ratings, which tracks with how Letterboxd actually works. Watch history is slightly under ratings since some people log things they watched without rating them.

---

## 2. Endpoint Performance

Tested on a local Postgres instance with the full 1M row dataset. Times measured from the browser network tab of `localhost:8000`.

| Endpoint | ms |
|----------|----|
| `GET /movies/recommendations/year?year=2006` | **2090** ← slowest |
| `GET /movies/recommendations/popular` | 1500 |
| `GET /movies` | 376 |
| `GET /movies/filter?genre=Action` | 376 |
| `GET /users/{user_id}/stats/dashboard` | 372 |
| `GET /users/{user_id}/reviews` | 352 |
| `GET /users/{user_id}/watch-history` | 339 |
| `GET /ratings/{movie_id}/ratings` | 338 |
| `GET /movies/{movie_id}/reviews` | 336 |
| `POST /movies/{movie_id}/ratings` | 325 |
| `GET /users/search?username=austin` | 325 |
| `GET /movies/trending?period=7d` | 237 |
| `GET /movies/search?title=fire` | 70 |
| `GET /movies/filter` | 39 |
| `POST /movies/{movie_id}/reviews` | 37 |
| `POST /users` | 22 |
| `GET /users/{user_id}/ratings` | 12 |
| `GET /movies/{movie_id}/ratings` | 8 |

Slowest endpoint: `GET /movies/recommendations/year` at 2090ms.

---

## 3. Performance Tuning

We tuned two endpoints — `recommendations/year` (the slowest) and `trending` (where indexes actually made a big difference for the database)

---

### `GET /movies/recommendations/year`

#### Before any indexes

```sql
EXPLAIN ANALYZE
SELECT * FROM movies WHERE release_year = 2010;
```

```
Seq Scan on movies  (cost=0.00..1113.00 rows=1543 width=43) (actual time=0.039..5.623 rows=1475 loops=1)
  Filter: (release_year = 2010)
  Rows Removed by Filter: 48525
  Buffers: shared hit=488
Planning Time: 3.408 ms
Execution Time: 5.784 ms
```

This is doing a full scan where Postgres reads all 50,000 movies and throws away 48,525 of them. There's no index on `release_year` so it has no other option. The fix was to add one index:

```sql
CREATE INDEX idx_movies_release_year ON movies (release_year);
```

#### After the index

```sql
EXPLAIN ANALYZE
SELECT * FROM movies WHERE release_year = 2010;
```

```
Bitmap Heap Scan on movies  (cost=20.25..527.54 rows=1543 width=43) (actual time=0.273..0.751 rows=1475 loops=1)
  Recheck Cond: (release_year = 2010)
  Heap Blocks: exact=466
  Buffers: shared hit=466 read=3
  ->  Bitmap Index Scan on idx_movies_release_year  (cost=0.00..19.86 rows=1543 width=0) (actual time=0.188..0.188 rows=1475 loops=1)
        Index Cond: (release_year = 2010)
        Index Searches: 1
Planning Time: 1.707 ms
Execution Time: 0.838 ms
```

The query went from 5.7ms to 0.8ms, about 7x faster. Now it's using a Bitmap Index Scan and going straight to the matching rows.

#### Why the endpoint is still slow

The index helped the query but the endpoint itself stayed around 2.5 seconds. We looked into why and ran this:

```sql
SELECT release_year, COUNT(*) FROM movies
GROUP BY release_year ORDER BY COUNT(*) DESC LIMIT 5;
```
```
 release_year | count
--------------+-------
         2025 |  2630
         2024 |  2588
         2023 |  2484
         2022 |  2317
         2021 |  2293
```

Recent years have 2,000-2,600 movies each. The endpoint pulls all of them into Python memory at once, then runs extra queries against ratings and reviews for the whole batch, then sorts everything in Python, and only then cuts it down to 10 results. The LIMIT should be happening in SQL, not at the end in Python after doing all that work.

We tried a few more indexes on watch_history and users to see if any of the inner queries were the bottleneck:

```sql
CREATE INDEX idx_watch_history_movie_id ON watch_history (movie_id);
CREATE INDEX idx_watch_history_user_id ON watch_history (user_id);
CREATE INDEX idx_users_username ON users (username);
```

That didn't fix it either. The problem isn't any single query, it's loading thousands of rows into Python and processing them all before applying a limit. Fixing that would require rewriting the endpoint to do the sorting and limiting in SQL.

---

### `GET /movies/trending?period=7d`

This endpoint runs three separate subqueries against ratings, reviews, and watch_history filtered by a time window, then joins everything back to movies. We started with ratings since that's the biggest table.

#### Before any indexes

```sql
EXPLAIN ANALYZE
SELECT movie_id, COUNT(rating_id), AVG(rating)
FROM ratings
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY movie_id;
```

```
GroupAggregate  (cost=7708.86..7896.83 rows=1365 width=44) (actual time=71.969..76.985 rows=1416 loops=1)
  Group Key: movie_id
  Buffers: shared hit=2588
  ->  Gather Merge  (cost=7708.86..7869.22 rows=1407 width=12) (actual time=71.937..75.151 rows=1512 loops=1)
        Workers Planned: 1
        Workers Launched: 1
        ->  Sort  (cost=6708.85..6710.92 rows=828 width=12) (actual time=53.750..53.815 rows=756 loops=2)
              Sort Key: movie_id
              ->  Parallel Seq Scan on ratings  (cost=0.00..6668.72 rows=828 width=12) (actual time=0.013..53.442 rows=756 loops=2)
                    Filter: (created_at >= (now() - '7 days'::interval))
                    Rows Removed by Filter: 199248
Execution Time: 77.179 ms
```

Instead of reading all 400,000 ratings to find the recent ones, an index on created_at lets Postgres jump straight to rows from the last 7 days without checking every single row first.

```sql
CREATE INDEX idx_ratings_created_at ON ratings (created_at);
```

#### After the index on ratings.created_at

```sql
EXPLAIN ANALYZE
SELECT movie_id, COUNT(rating_id), AVG(rating)
FROM ratings
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY movie_id;
```

```
HashAggregate  (cost=2310.61..2327.89 rows=1382 width=44) (actual time=1.848..2.273 rows=1415 loops=1)
  Group Key: movie_id
  Batches: 1  Memory Usage: 305kB
  Buffers: shared hit=1121 read=4
  ->  Bitmap Heap Scan on ratings  (cost=27.47..2299.93 rows=1425 width=12) (actual time=0.451..1.399 rows=1510 loops=1)
        Recheck Cond: (created_at >= (now() - '7 days'::interval))
        Heap Blocks: exact=1118
        ->  Bitmap Index Scan on idx_ratings_created_at  (cost=0.00..27.11 rows=1425 width=0) (actual time=0.283..0.283 rows=1510 loops=1)
              Index Cond: (created_at >= (now() - '7 days'::interval))
Execution Time: 2.415 ms
```

77ms down to 2.4ms which is much faster. Applied the same fix to reviews and watch_history:

```sql
CREATE INDEX idx_reviews_created_at ON reviews (created_at);
CREATE INDEX idx_watch_history_date_watched ON watch_history (date_watched);
```

#### After index on reviews.created_at

```sql
EXPLAIN ANALYZE
SELECT movie_id, COUNT(review_id)
FROM reviews
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY movie_id;
```

```
HashAggregate  (cost=1322.38..1327.16 rows=478 width=12) (actual time=0.791..0.859 rows=487 loops=1)
  ->  Bitmap Heap Scan on reviews  (cost=12.17..1319.97 rows=483 width=8) (actual time=0.165..0.668 rows=499 loops=1)
        Recheck Cond: (created_at >= (now() - '7 days'::interval))
        ->  Bitmap Index Scan on idx_reviews_created_at  (cost=0.00..12.05 rows=483 width=0) (actual time=0.084..0.085 rows=499 loops=1)
              Index Cond: (created_at >= (now() - '7 days'::interval))
Execution Time: 0.922 ms
```

#### After index on watch_history.date_watched

```sql
EXPLAIN ANALYZE
SELECT movie_id, COUNT(watch_history_id)
FROM watch_history
WHERE date_watched >= NOW() - INTERVAL '7 days'
GROUP BY movie_id;
```

```
HashAggregate  (cost=808.70..813.42 rows=472 width=12) (actual time=0.595..0.660 rows=444 loops=1)
  ->  Bitmap Heap Scan on watch_history  (cost=12.10..806.32 rows=475 width=8) (actual time=0.123..0.484 rows=445 loops=1)
        Recheck Cond: (date_watched >= (now() - '7 days'::interval))
        ->  Bitmap Index Scan on idx_watch_history_date_watched  (cost=0.00..11.99 rows=475 width=0) (actual time=0.064..0.064 rows=445 loops=1)
              Index Cond: (date_watched >= (now() - '7 days'::interval))
Execution Time: 0.718 ms
```

All three queries are now under 3ms. The endpoint itself is still around 362ms because after the database part finishes, Python makes extra calls to look up the genres and actors for each movie separately. That's what's eating up the remaining time.

#### Summary

| Query | Before | After |
|-------|--------|-------|
| ratings (created_at filter) | 77.2ms | 2.4ms |
| reviews (created_at filter) | seq scan | 0.9ms |
| watch_history (date_watched filter) | seq scan | 0.7ms |

---

### All indexes added

| Index | Table | Column |
|-------|-------|--------|
| `idx_movies_release_year` | `movies` | `release_year` |
| `idx_ratings_created_at` | `ratings` | `created_at` |
| `idx_reviews_created_at` | `reviews` | `created_at` |
| `idx_watch_history_date_watched` | `watch_history` | `date_watched` |
| `idx_watch_history_movie_id` | `watch_history` | `movie_id` |
| `idx_watch_history_user_id` | `watch_history` | `user_id` |
| `idx_users_username` | `users` | `username` |