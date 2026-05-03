"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-05-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    op.create_table(
        'movies',
        sa.Column('movie_id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('media_type', sa.String(10),
                  nullable=False, server_default='movie'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index('ix_movies_title', 'movies', ['title'])

    op.create_table(
        'genres',
        sa.Column('genre_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
    )

    op.create_table(
        'actors',
        sa.Column('actor_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
    )

    op.create_table(
        'movie_genres',
        sa.Column('movie_id', sa.Integer(), sa.ForeignKey(
            'movies.movie_id'), primary_key=True),
        sa.Column('genre_id', sa.Integer(), sa.ForeignKey(
            'genres.genre_id'), primary_key=True),
    )

    op.create_table(
        'movie_actors',
        sa.Column('movie_id', sa.Integer(), sa.ForeignKey(
            'movies.movie_id'), primary_key=True),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey(
            'actors.actor_id'), primary_key=True),
    )

    op.create_table(
        'reviews',
        sa.Column('review_id', sa.Integer(), primary_key=True),
        sa.Column('movie_id', sa.Integer(), sa.ForeignKey(
            'movies.movie_id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey(
            'users.user_id'), nullable=False),
        sa.Column('review_text', sa.Text(), nullable=False),
        sa.Column('contains_spoilers', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    op.create_table(
        'ratings',
        sa.Column('rating_id', sa.Integer(), primary_key=True),
        sa.Column('movie_id', sa.Integer(), sa.ForeignKey(
            'movies.movie_id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey(
            'users.user_id'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='rating_range'),
    )

    op.create_table(
        'watch_history',
        sa.Column('watch_history_id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey(
            'users.user_id'), nullable=False),
        sa.Column('movie_id', sa.Integer(), sa.ForeignKey(
            'movies.movie_id'), nullable=False),
        sa.Column('date_watched', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('watch_history')
    op.drop_table('ratings')
    op.drop_table('reviews')
    op.drop_table('movie_actors')
    op.drop_table('movie_genres')
    op.drop_table('actors')
    op.drop_table('genres')
    op.drop_index('ix_movies_title', table_name='movies')
    op.drop_table('movies')
    op.drop_table('users')
