# Team_Project_365

For our group project for CSC 365, we decided we wanted to create a new backend API around movie & tv entertainment. The goal is to build a system that allows users to catalog movies and shows, along with reviews, comments, ratings, and other key details. We also plan to include a user component that stores information such as contact details, watch history, favorite genres, and any reviews or comments they’ve made. Other possible relations could be specific contributor roles to film (actor, actress, director, etc) that could store their own information. While many databases like this exist, we also want to include tv, maybe even leaderboards, and some type of visuals if possible.  Overall, this project could be really interesting with a lot of creative ways to make the project unique.


Contributors to this project: aweave10@calpoly.edu , bccorbet@calpoly.edu , mibandi@calpoly.edu , hcampb07@calpoly.edu

## Local setup

Avery #9.16: instructions for running the API locally.

1. Clone the repo and `cd Team_Project_365`.
2. Create a virtualenv and install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in `DATABASE_URL`. For local Postgres:
   ```
   DATABASE_URL=postgresql+psycopg2://<user>:<pass>@localhost:5432/team_project_365
   ```
4. Apply migrations:
   ```
   alembic upgrade head
   ```
5. Start the API:
   ```
   uvicorn src.main:app --reload
   ```
6. Open the interactive docs at http://localhost:8000/docs.

Deployment is on Render at https://team-project-365.onrender.com/.

