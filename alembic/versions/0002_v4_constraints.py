"""v4 schema hardening: dedupe legacy data, add constraints, ON DELETE CASCADE, release_year

Addresses peer-review feedback:
  Jared #2.1, #2.2, #2.3 — unique (user_id, movie_id) on ratings/reviews/watch_history
  Jared #2.4 — CHECK media_type IN ('movie', 'tv')
  Jared #2.5 — UNIQUE on actors.name
  Jared #2.6 — ON DELETE CASCADE on dependent FKs
  Jared #2.7 — CHECK review_text length
  Jared #2.8 — release_year column on movies
  Avery #10.8 — indexes on FK columns used in filters

Revision ID: 0002_v4_constraints
Revises: 0001_initial_schema
Create Date: 2026-05-24 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "0002_v4_constraints"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DELETE FROM ratings
        WHERE rating_id NOT IN (
            SELECT DISTINCT ON (user_id, movie_id) rating_id
            FROM ratings
            ORDER BY user_id, movie_id, created_at DESC, rating_id DESC
        );
    """)

    op.execute("""
        DELETE FROM reviews
        WHERE review_id NOT IN (
            SELECT DISTINCT ON (user_id, movie_id) review_id
            FROM reviews
            ORDER BY user_id, movie_id, created_at DESC, review_id DESC
        );
    """)

    op.execute("""
        DELETE FROM watch_history
        WHERE watch_history_id NOT IN (
            SELECT DISTINCT ON (user_id, movie_id) watch_history_id
            FROM watch_history
            ORDER BY user_id, movie_id, date_watched DESC, watch_history_id DESC
        );
    """)

    op.execute("""
        WITH ranked AS (
            SELECT actor_id, name,
                   MIN(actor_id) OVER (PARTITION BY name) AS keep_id
            FROM actors
        )
        INSERT INTO movie_actors (movie_id, actor_id)
        SELECT DISTINCT ma.movie_id, r.keep_id
        FROM movie_actors ma
        JOIN ranked r ON ma.actor_id = r.actor_id
        WHERE r.actor_id <> r.keep_id
        ON CONFLICT DO NOTHING;
    """)
    op.execute("""
        DELETE FROM movie_actors
        WHERE actor_id IN (
            SELECT actor_id FROM (
                SELECT actor_id, MIN(actor_id) OVER (PARTITION BY name) AS keep_id
                FROM actors
            ) d
            WHERE actor_id <> keep_id
        );
    """)
    op.execute("""
        DELETE FROM actors
        WHERE actor_id IN (
            SELECT actor_id FROM (
                SELECT actor_id, MIN(actor_id) OVER (PARTITION BY name) AS keep_id
                FROM actors
            ) d
            WHERE actor_id <> keep_id
        );
    """)

    # Empty / reviews that are TOO LONG (Jared #2.7)
    op.execute("DELETE FROM reviews WHERE length(review_text) < 1;")
    op.execute(
        "UPDATE reviews SET review_text = substring(review_text from 1 for 2000) WHERE length(review_text) > 2000;"
    )

    # Invalid media_type (Jared #2.4) change them to 'movie'
    op.execute(
        "UPDATE movies SET media_type = 'movie' WHERE media_type NOT IN ('movie', 'tv');"
    )

    # Jared #2.8: add release_year column with sanity CHECK
    op.add_column("movies", sa.Column("release_year", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "release_year_range",
        "movies",
        "release_year IS NULL OR (release_year >= 1888 AND release_year <= 2031)",
    )

    # Jared #2.4: CHECK media_type
    op.create_check_constraint(
        "media_type_valid", "movies", "media_type IN ('movie', 'tv')"
    )

    # Jared #2.5: UNIQUE actors.name
    op.create_unique_constraint("uq_actors_name", "actors", ["name"])

    # Jared #2.1: UNIQUE (user_id, movie_id) on ratings
    op.create_unique_constraint(
        "uq_ratings_user_movie", "ratings", ["user_id", "movie_id"]
    )

    # Jared #2.3: UNIQUE (user_id, movie_id) on reviews
    op.create_unique_constraint(
        "uq_reviews_user_movie", "reviews", ["user_id", "movie_id"]
    )

    # Jared #2.2: UNIQUE (user_id, movie_id) on watch_history
    op.create_unique_constraint(
        "uq_watch_user_movie", "watch_history", ["user_id", "movie_id"]
    )

    # Jared #2.7: CHECK review_text length
    op.create_check_constraint(
        "review_text_length", "reviews", "length(review_text) BETWEEN 1 AND 2000"
    )

    # Avery #10.8 / Jared #2.6: indexes on FK columns used heavily in WHERE/JOIN
    op.create_index("ix_ratings_movie_id", "ratings", ["movie_id"])
    op.create_index("ix_ratings_user_id", "ratings", ["user_id"])
    op.create_index("ix_reviews_movie_id", "reviews", ["movie_id"])
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"])
    op.create_index("ix_watch_user_id", "watch_history", ["user_id"])
    op.create_index("ix_watch_movie_id", "watch_history", ["movie_id"])

    # Jared #2.6: Create FKs with ON DELETE CASCADE for ratings/reviews/watch_history/joins
    for table, cols in [
        (
            "ratings",
            [("movie_id", "movies", "movie_id"), ("user_id", "users", "user_id")],
        ),
        (
            "reviews",
            [("movie_id", "movies", "movie_id"), ("user_id", "users", "user_id")],
        ),
        (
            "watch_history",
            [("movie_id", "movies", "movie_id"), ("user_id", "users", "user_id")],
        ),
        (
            "movie_genres",
            [("movie_id", "movies", "movie_id"), ("genre_id", "genres", "genre_id")],
        ),
        (
            "movie_actors",
            [("movie_id", "movies", "movie_id"), ("actor_id", "actors", "actor_id")],
        ),
    ]:
        for col, ref_table, ref_col in cols:
            op.execute(f"""
                DO $$
                DECLARE fk_name text;
                BEGIN
                    SELECT conname INTO fk_name
                    FROM pg_constraint
                    WHERE conrelid = '{table}'::regclass
                      AND contype = 'f'
                      AND conkey = ARRAY[(
                          SELECT attnum FROM pg_attribute
                          WHERE attrelid = '{table}'::regclass AND attname = '{col}'
                      )]::int2[];
                    IF fk_name IS NOT NULL THEN
                        EXECUTE 'ALTER TABLE {table} DROP CONSTRAINT ' || quote_ident(fk_name);
                    END IF;
                END$$;
            """)
            op.create_foreign_key(
                f"fk_{table}_{col}",
                table,
                ref_table,
                [col],
                [ref_col],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    for table, cols in [
        (
            "ratings",
            [("movie_id", "movies", "movie_id"), ("user_id", "users", "user_id")],
        ),
        (
            "reviews",
            [("movie_id", "movies", "movie_id"), ("user_id", "users", "user_id")],
        ),
        (
            "watch_history",
            [("movie_id", "movies", "movie_id"), ("user_id", "users", "user_id")],
        ),
        (
            "movie_genres",
            [("movie_id", "movies", "movie_id"), ("genre_id", "genres", "genre_id")],
        ),
        (
            "movie_actors",
            [("movie_id", "movies", "movie_id"), ("actor_id", "actors", "actor_id")],
        ),
    ]:
        for col, ref_table, ref_col in cols:
            op.drop_constraint(f"fk_{table}_{col}", table, type_="foreignkey")
            op.create_foreign_key(None, table, ref_table, [col], [ref_col])

    op.drop_index("ix_watch_movie_id", table_name="watch_history")
    op.drop_index("ix_watch_user_id", table_name="watch_history")
    op.drop_index("ix_reviews_user_id", table_name="reviews")
    op.drop_index("ix_reviews_movie_id", table_name="reviews")
    op.drop_index("ix_ratings_user_id", table_name="ratings")
    op.drop_index("ix_ratings_movie_id", table_name="ratings")

    op.drop_constraint("review_text_length", "reviews", type_="check")
    op.drop_constraint("uq_watch_user_movie", "watch_history", type_="unique")
    op.drop_constraint("uq_reviews_user_movie", "reviews", type_="unique")
    op.drop_constraint("uq_ratings_user_movie", "ratings", type_="unique")
    op.drop_constraint("uq_actors_name", "actors", type_="unique")
    op.drop_constraint("media_type_valid", "movies", type_="check")
    op.drop_constraint("release_year_range", "movies", type_="check")
    op.drop_column("movies", "release_year")
